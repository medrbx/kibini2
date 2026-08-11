"""
Charge la fréquentation (comptage de passages) depuis l'API Opteio dans deux
tables statdb, à partir d'un seul appel API par lancement :

- stat_entrees      : totaux horaires (datetime, entrees), tous capteurs du
                       site confondus, sorties ignorées. Remplace l'ancien
                       flux Perl statdb_entrees.pl, qui lisait un système de
                       comptage disparu.
- stat_entrees_det  : détail brut par capteur et par minute (site_id,
                       capteur, datetime, jour, heure, minute, entree,
                       sortie) - le détail que statdb_entrees.pl ne
                       conservait pas.

Source des comptages : dataset 'inout' de l'API Opteio, via
kiblib.utils.opteio.OpteioClient (intégré depuis dev/opteio-export).

Schéma de stat_entrees_det : voir schema_stat_entrees_det.sql (table à créer
manuellement avant le premier lancement - pas de migration automatique).

Prérequis : une section `opteio: {login, password}` dans kibini_conf.yml
(cf. kiblib/utils/conf.py -> Config.get_config_opteio()).

Usage :
    python statdb_entrees_opteio.py --last 7
    python statdb_entrees_opteio.py --start 2026-08-01 --end 2026-08-10
    python statdb_entrees_opteio.py --site-id 21 --last 30   # site par défaut

Idempotence : les deux tables peuvent être rechargées sur une période déjà
traitée sans créer de doublons, mais pas de la même façon :
- stat_entrees n'a aucune contrainte d'unicité -> la période est purgée
  (DELETE) avant réinsertion.
- stat_entrees_det a une contrainte UNIQUE (site_id, capteur, datetime) ->
  upsert (INSERT ... ON DUPLICATE KEY UPDATE).

Piège observé sur les données réelles : l'API renvoie parfois deux lignes
distinctes pour le même capteur/minute - une pour les entrées, une pour les
sorties (ex. {entree:1,sortie:0} et {entree:0,sortie:2}). build_detail_rows
les fusionne (somme) avant upsert ; sans ça, la seconde ligne écraserait
silencieusement la première via ON DUPLICATE KEY UPDATE. aggregate_by_hour
n'est pas concerné : il additionne déjà toutes les lignes brutes.
"""
import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import text

from kiblib.utils.db import DbConn
from kiblib.utils.log import Log
from kiblib.utils.opteio import OpteioClient

DEFAULT_SITE_ID = 21  # Médiathèque de Roubaix


def parse_args():
    parser = argparse.ArgumentParser(
        description="Alimente statdb.stat_entrees à partir des comptages Opteio (dataset 'inout')."
    )
    parser.add_argument(
        "--site-id", type=int, default=DEFAULT_SITE_ID,
        help=f"id du site Opteio (défaut : {DEFAULT_SITE_ID}, Médiathèque de Roubaix)",
    )
    parser.add_argument("--start", help="date de début AAAA-MM-JJ")
    parser.add_argument("--end", help="date de fin AAAA-MM-JJ (défaut : hier)")
    parser.add_argument("--last", type=int, metavar="N", help="raccourci : les N derniers jours")
    args = parser.parse_args()

    end = date.fromisoformat(args.end) if args.end else date.today() - timedelta(days=1)
    if args.last:
        start = end - timedelta(days=args.last - 1)
    elif args.start:
        start = date.fromisoformat(args.start)
    else:
        parser.error("précise --start AAAA-MM-JJ (ou --last N)")
    if start > end:
        parser.error("la date de début est postérieure à la date de fin")
    return args.site_id, start, end


def aggregate_by_hour(rows):
    """Somme les entrées par heure, tous capteurs confondus - même logique
    que l'ancien statdb_entrees.pl (pas de distinction par capteur, sorties
    ignorées)."""
    totals = defaultdict(int)
    for row in rows:
        try:
            dt = datetime.strptime(f"{row['jour']} {int(row['heure']):02d}:00:00", "%Y-%m-%d %H:%M:%S")
            entree = int(row["entree"])
        except (KeyError, TypeError, ValueError):
            continue
        totals[dt] += entree
    return totals


def build_detail_rows(site_id, rows):
    """
    Une ligne par capteur/minute, champs bruts tels que renvoyés par l'API.

    L'API renvoie parfois deux lignes distinctes pour le même capteur/minute
    (une pour les entrées, une pour les sorties, ex. {entree:1,sortie:0} et
    {entree:0,sortie:2}) : on les somme ici avant upsert, pour ne pas en
    perdre une au profit de l'autre.
    """
    totals = {}
    for row in rows:
        try:
            heure = int(row["heure"])
            minute = int(row["minute"])
            dt = datetime.strptime(f"{row['jour']} {heure:02d}:{minute:02d}:00", "%Y-%m-%d %H:%M:%S")
            key = (int(row["capteur"]), dt)
            entree = int(row["entree"])
            sortie = int(row["sortie"])
        except (KeyError, TypeError, ValueError):
            continue

        if key in totals:
            totals[key]["entree"] += entree
            totals[key]["sortie"] += sortie
        else:
            totals[key] = {
                "site_id": site_id,
                "capteur": key[0],
                "datetime": dt,
                "jour": row["jour"],
                "heure": heure,
                "minute": minute,
                "entree": entree,
                "sortie": sortie,
            }
    return list(totals.values())


site_id, start, end = parse_args()

log = Log()
log.add_info('Lancement')
log.add_info(f"site_id={site_id} période={start}..{end}")

client = OpteioClient()
data = client.fetch_period(site_id, start, end, datasets=["inout"])
rows = data.get("inout", [])
log.add_info(f"{len(rows)} lignes 'inout' récupérées depuis l'API Opteio")

totals = aggregate_by_hour(rows)
log.add_info(f"{len(totals)} heures agrégées")

detail_rows = build_detail_rows(site_id, rows)
log.add_info(f"{len(detail_rows)} lignes de détail (capteur/minute)")

engine = DbConn().create_engine()
range_start = datetime.combine(start, datetime.min.time())
range_end = datetime.combine(end + timedelta(days=1), datetime.min.time())

with engine.begin() as conn:
    # stat_entrees n'a aucune contrainte d'unicité : on purge la période avant
    # de réinsérer, pour rester idempotent si le script est relancé.
    deleted = conn.execute(
        text("DELETE FROM statdb.stat_entrees WHERE datetime >= :start AND datetime < :end"),
        {"start": range_start, "end": range_end},
    )
    log.add_info(f"{deleted.rowcount} anciennes lignes supprimées sur la période (stat_entrees)")

    if totals:
        conn.execute(
            text("INSERT INTO statdb.stat_entrees (datetime, entrees) VALUES (:datetime, :entrees)"),
            [{"datetime": dt, "entrees": n} for dt, n in totals.items()],
        )

    # stat_entrees_det a une contrainte d'unicité (site_id, capteur, datetime) :
    # upsert plutôt que purge/réinsertion, plus adapté à son volume.
    if detail_rows:
        conn.execute(
            text(
                """
                INSERT INTO statdb.stat_entrees_det
                    (site_id, capteur, datetime, jour, heure, minute, entree, sortie)
                VALUES
                    (:site_id, :capteur, :datetime, :jour, :heure, :minute, :entree, :sortie)
                ON DUPLICATE KEY UPDATE entree = VALUES(entree), sortie = VALUES(sortie)
                """
            ),
            detail_rows,
        )

log.add_info(f"{len(totals)} lignes insérées (stat_entrees), {len(detail_rows)} lignes upsertées (stat_entrees_det)")
log.add_info("Fin traitement\n\n")
