"""
Extrait les logs de visite bruts (une ligne par visite) du site BN-R sur
stats.bn-r.fr (module Live.getLastVisitsDetails), dans un fichier CSV.

Contrairement à data_matomo.py, qui alimente statdb.stat_web2 avec des
agrégats journaliers (VisitsSummary/Actions/Goals), ce script récupère le
détail brut par visite : referrer, device/navigateur/OS, pays, durée,
nombre d'actions, variable personnalisée 'Provenance IP' (interne/externe),
etc. Il n'écrit rien dans statdb : sortie CSV uniquement.

Étendue disponible côté API (constatée le 2026-09-10 sur idSite=1) :
- Agrégats (VisitsSummary...)          : depuis le 2017-12-08.
- Logs bruts (Live.getLastVisitsDetails) : purgés au-delà d'environ 2 ans ;
  premier jour avec des logs constaté : 2024-06-13. Au-delà (avant), l'API
  renvoie simplement 0 visite par jour, ce n'est pas une erreur.
DEFAULT_START reflète cette date de purge ; à ajuster si la politique de
rétention change côté serveur Matomo.

Pagination : le serveur plafonne chaque appel à 100 visites, quel que soit
filter_limit demandé au-delà -> on boucle avec filter_offset jusqu'à une
page vide, jour par jour.

Reprise : si le fichier de sortie existe déjà, le script reprend au
lendemain de la dernière date qui s'y trouve (relancer après une
interruption ne duplique donc rien, sans avoir à tout refaire).

Identifiants lus dans kibini_conf.yml (section 'matomo_bnr' : base,
token_auth, site_id), via kiblib.utils.conf.Config.get_config_matomo_bnr().

Usage :
    python data_matomo_logs_bnr.py                                # 2024-06-13 -> hier, ou reprise auto
    python data_matomo_logs_bnr.py --start 2024-06-13 --end 2024-06-30
    python data_matomo_logs_bnr.py --out /chemin/vers/bnr_logs.csv
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import date, timedelta

from kiblib.utils.conf import Config
from kiblib.utils.log import Log
from kiblib.utils.matomo import MatomoClient

# actionDetails (JSON de toutes les pages vues d'une visite) peut largement
# depasser la limite par defaut du module csv (131072 caracteres), ce qui
# fait planter resume_start() des la reprise sur un fichier deja volumineux.
csv.field_size_limit(sys.maxsize)

DEFAULT_START = date(2024, 6, 13)
# dossier data/ à la racine du dépôt (exclu par .gitignore)
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bnr_visites_detail.csv")
PAGE_SIZE = 100
PAUSE_BETWEEN_APPELS = 0.2  # secondes, pour ne pas marteler l'API

# Champs bruts renvoyés par Live.getLastVisitsDetails (constatés sur BN-R).
FIELDNAMES = [
    "serverDate", "idVisit", "visitorId", "visitCount", "visitorType",
    "firstActionTimestamp", "lastActionTimestamp", "serverTimePrettyFirstAction",
    "serverTimePretty", "visitDuration", "visitDurationPretty", "actions",
    "searches", "events", "goalConversions", "visitConverted",
    "visitEcommerceStatus", "referrerType", "referrerTypeName", "referrerName",
    "referrerUrl", "referrerKeyword", "referrerKeywordPosition",
    "referrerSearchEngineUrl", "deviceType", "deviceBrand", "deviceModel",
    "operatingSystem", "operatingSystemVersion", "browser", "browserName",
    "browserVersion", "languageCode", "language", "continent", "country",
    "region", "city", "latitude", "longitude", "resolution", "plugins",
    "visitIp", "visitLocalTime", "visitServerHour", "daysSinceFirstVisit",
    "daysSinceLastVisit", "userId", "siteCurrency",
    "provenance_ip", "customVariables", "pluginsIcons", "actionDetails",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extrait les logs de visite bruts Matomo (BN-R) dans un CSV."
    )
    parser.add_argument("--start", help="date de début AAAA-MM-JJ (défaut : reprise auto, sinon 2024-06-13)")
    parser.add_argument("--end", help="date de fin AAAA-MM-JJ (défaut : hier)")
    parser.add_argument("--out", default=DEFAULT_OUT, help=f"fichier CSV de sortie (défaut : {DEFAULT_OUT})")
    args = parser.parse_args()

    end = date.fromisoformat(args.end) if args.end else date.today() - timedelta(days=1)
    start = date.fromisoformat(args.start) if args.start else None
    return start, end, args.out


def resume_start(out_path, fallback_start):
    """Si le fichier de sortie existe déjà, reprend au lendemain de la
    dernière date qui y figure ; sinon renvoie fallback_start."""
    if not os.path.exists(out_path):
        return fallback_start
    last_date = None
    with open(out_path, newline="") as f:
        for row in csv.DictReader(f):
            d = row.get("serverDate")
            if d and (last_date is None or d > last_date):
                last_date = d
    if last_date is None:
        return fallback_start
    return date.fromisoformat(last_date) + timedelta(days=1)


def flatten_visit(visit):
    """Aplati une visite Live.getLastVisitsDetails en une ligne de CSV.
    Les structures imbriquées (customVariables, pluginsIcons,
    actionDetails) sont conservées telles quelles, sérialisées en JSON."""
    custom_vars = visit.get("customVariables") or {}
    provenance_ip = ""
    for cv in custom_vars.values():
        if cv.get("customVariableName1") == "Provenance IP":
            provenance_ip = cv.get("customVariableValue1", "")
            break

    row = {key: visit.get(key, "") for key in FIELDNAMES}
    row["provenance_ip"] = provenance_ip
    row["customVariables"] = json.dumps(custom_vars, ensure_ascii=False)
    row["pluginsIcons"] = json.dumps(visit.get("pluginsIcons") or [], ensure_ascii=False)
    row["actionDetails"] = json.dumps(visit.get("actionDetails") or [], ensure_ascii=False)
    return row


start, end, out_path = parse_args()

conf = Config().get_config_matomo_bnr()
client = MatomoClient(base=conf["base"], token_auth=conf["token_auth"])
site_id = conf["site_id"]

if start is None:
    start = resume_start(out_path, DEFAULT_START)

log = Log()
log.add_info(f"Lancement {log.script_name}")
log.add_info(f"période={start}..{end} out={out_path}")

if start > end:
    log.add_info("Rien à faire : la date de reprise est déjà postérieure à la date de fin.")
    log.add_info(f"Fin traitement {log.script_name}\n\n")
    raise SystemExit(0)

file_exists = os.path.exists(out_path)
os.makedirs(os.path.dirname(out_path), exist_ok=True)

total_visits = 0
with open(out_path, "a", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    if not file_exists:
        writer.writeheader()

    cur = start
    while cur <= end:
        offset = 0
        day_visits = 0
        while True:
            page = client.get_visits_details(site_id, cur, filter_limit=PAGE_SIZE, filter_offset=offset)
            if not page:
                break
            for visit in page:
                writer.writerow(flatten_visit(visit))
            day_visits += len(page)
            offset += len(page)
            if len(page) < PAGE_SIZE:
                break
            time.sleep(PAUSE_BETWEEN_APPELS)
        f.flush()
        total_visits += day_visits
        log.add_info(f"{cur} : {day_visits} visites")
        cur += timedelta(days=1)

log.add_info(f"{total_visits} visites écrites dans {out_path}")
log.add_info(f"Fin traitement {log.script_name}\n\n")
