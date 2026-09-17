"""
Alimente statdb.stat_web2 à partir de l'API Matomo (visites brutes
Live.getLastVisitsDetails, ré-agrégées jour par jour), en remplacement de
l'export CSV manuel utilisé par data_web_interne.py / data_web_externe.py.

Les visites brutes (plutôt que les endpoints agrégés VisitsSummary/Actions
/Goals) sont nécessaires pour exclure via
kiblib.utils.matomo.is_server_tracked_visit() les visites trackées côté
serveur (authentification/réservation) qui dupliquent une visite déjà
trackée normalement par le navigateur de l'usager (cf. analyse bokeh du
2026-09-17, ~4,5% des visites concernées). Cf.
kiblib/utils/matomo.py -> MatomoClient.get_daily_stats_deduped().

Un seul site Matomo (section 'matomo': site_id dans kibini_conf.yml) reçoit
le trafic interne et externe : les deux origines sont distinguées par un
segment sur l'IP du visiteur (matomo.ip_interne) plutôt que par id_site
-> visitIp==ip_interne pour 'interne', visitIp!=ip_interne pour 'externe'.
L'URL de base et le token_auth de l'API sont aussi lus dans cette section
(cf. kiblib/utils/conf.py -> Config.get_config_matomo() et
kiblib/utils/matomo.py -> MatomoClient).

Le champ 'periode' (scolaire/vacances) est ajouté par jointure avec le
calendrier des vacances scolaires (kiblib/vacances_scolaires_fr.csv), comme
dans les scripts existants.

Usage :
    python data_matomo.py --last 7
    python data_matomo.py --start 2026-08-01 --end 2026-08-10
    python data_matomo.py --last 7 --origine externe   # une seule origine
    python data_matomo.py --last 7 --dry-run           # affiche sans écrire dans statdb

Idempotence : stat_web2 n'a pas de contrainte d'unicité connue -> la
période est purgée (DELETE), par origine traitée, avant réinsertion.
"""
import argparse
import os
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import text

from kiblib.utils.conf import Config
from kiblib.utils.db import DbConn
from kiblib.utils.log import Log
from kiblib.utils.matomo import MatomoClient

# Chemin de prod ; repli sur le fichier du dépôt si absent (poste de dev).
VACANCES_CSV_PATH = "/home/kibini/kibini2/kibini/kiblib/vacances_scolaires_fr.csv"
if not os.path.exists(VACANCES_CSV_PATH):
    VACANCES_CSV_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "kiblib", "vacances_scolaires_fr.csv"
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Alimente statdb.stat_web2 à partir de l'API Matomo."
    )
    parser.add_argument("--start", help="date de début AAAA-MM-JJ")
    parser.add_argument("--end", help="date de fin AAAA-MM-JJ (défaut : hier)")
    parser.add_argument("--last", type=int, metavar="N", help="raccourci : les N derniers jours")
    parser.add_argument(
        "--origine", choices=("interne", "externe"),
        help="ne peupler qu'une seule origine (défaut : les deux)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="récupère les données Matomo et les affiche sans rien écrire dans statdb",
    )
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
    return start, end, args.origine, args.dry_run


def build_dataframe(daily_stats, origine):
    rows = [
        {"date": day, "origine": origine, **values}
        for day, values in sorted(daily_stats.items())
    ]
    return pd.DataFrame(
        rows,
        columns=["date", "visites", "pages_vues", "utilisateurs", "taux_conversion", "origine"],
    )


start, end, only_origine, dry_run = parse_args()
want_interne = only_origine in (None, "interne")
want_externe = only_origine in (None, "externe")

log = Log()
log.add_info(f'Lancement {log.script_name}')
log.add_info(f"période={start}..{end} origine={only_origine or 'les deux'} dry_run={dry_run}")

conf_matomo = Config().get_config_matomo()
client = MatomoClient()

# Calendrier des vacances scolaires, pour ajouter la colonne 'periode'
verif_vacances = pd.read_csv(VACANCES_CSV_PATH)
verif_vacances.loc[verif_vacances['vacances_zone_b'] == False, 'periode'] = 'scolaire'
verif_vacances.loc[verif_vacances['vacances_zone_b'] == True, 'periode'] = 'vacances'
verif_vacances = verif_vacances[['date', 'periode']]

site_id = conf_matomo['site_id']
ip_interne = conf_matomo['ip_interne']

dataframes = []
if want_interne:
    stats = client.get_daily_stats_deduped(site_id, start, end, segment=f"visitIp=={ip_interne}")
    log.add_info(f"{len(stats)} jours récupérés depuis l'API Matomo (interne)")
    dataframes.append(build_dataframe(stats, 'interne'))
if want_externe:
    stats = client.get_daily_stats_deduped(site_id, start, end, segment=f"visitIp!={ip_interne}")
    log.add_info(f"{len(stats)} jours récupérés depuis l'API Matomo (externe)")
    dataframes.append(build_dataframe(stats, 'externe'))

web_to_import = pd.concat(dataframes, ignore_index=True)
web_to_import = web_to_import.merge(verif_vacances, left_on='date', right_on='date', how='left')

if dry_run:
    log.add_info(f"[dry-run] {len(web_to_import)} lignes qui auraient été insérées dans stat_web2 (aucune écriture)")
    print(web_to_import.to_string(index=False))
else:
    engine = DbConn().create_engine()
    with engine.begin() as conn:
        # Pas de contrainte d'unicité connue sur stat_web2 : on purge la
        # période (par origine traitée) avant réinsertion, pour rester
        # idempotent si le script est relancé.
        for origine in web_to_import['origine'].unique():
            conn.execute(
                text(
                    "DELETE FROM statdb.stat_web2 "
                    "WHERE date >= :start AND date <= :end AND origine = :origine"
                ),
                {"start": start, "end": end, "origine": origine},
            )
        web_to_import.to_sql('stat_web2', con=conn, if_exists='append', index=False)
    log.add_info(f"{len(web_to_import)} lignes insérées dans stat_web2")

log.add_info(f"Fin traitement {log.script_name}\n\n")
