"""
Extrait les logs de visite bruts (une ligne par visite) du site Matomo
bokeh (portail Médiathèque de Roubaix) via Live.getLastVisitsDetails,
dans un fichier CSV. Pendant du data_matomo_logs_bnr.py pour l'instance
matomo.biblibre.com plutôt que stats.bn-r.fr.

Contrairement à data_matomo.py, qui alimente statdb.stat_web2 avec des
agrégats journaliers (VisitsSummary/Actions/Goals), ce script récupère le
détail brut par visite : referrer, device/navigateur/OS, pays, durée,
nombre d'actions, ainsi que le détail de chaque page vue au sein de la
visite (URL, titre, temps passé) via actionDetails - bien peuplé sur
cette instance comme sur BN-R. Il n'écrit rien dans statdb : sortie CSV
uniquement.

Origine (interne/externe) : ce site n'a pas de variable personnalisée
dédiée (contrairement à BN-R) ; comme pour data_matomo.py, elle est
déduite en comparant visitIp à matomo.ip_interne (kibini_conf.yml).

Étendue disponible côté API (constatée le 2026-09-10 sur idSite=233) :
- Agrégats (VisitsSummary...)            : depuis longtemps (cf. data_matomo.py).
- Logs bruts (Live.getLastVisitsDetails) : purgés au-delà d'environ 9-10
  mois ; premier jour avec des logs constaté : 2025-11-28. Au-delà (avant),
  l'API renvoie simplement 0 visite par jour, ce n'est pas une erreur.

DEFAULT_START est néanmoins fixé au 2026-03-31, pas à cette date de purge :
avant le 31/03/2026, idSite=233 était le site de test/développement (pas
le portail de production), comme pour data_matomo.py. Les logs du
28/11/2025 au 30/03/2026 existent donc côté API mais ne représentent pas
du vrai trafic ; à ne pas extraire sauf besoin explicite (--start).

Volume : environ 800-900 visites/jour sur ce site (bien plus que BN-R) ->
l'extraction complète depuis DEFAULT_START représente plusieurs centaines
de milliers de lignes et plusieurs milliers d'appels API.

Pagination : le serveur plafonne chaque appel à 100 visites, quel que soit
filter_limit demandé au-delà -> on boucle avec filter_offset jusqu'à une
page vide, jour par jour.

Reprise : si le fichier de sortie existe déjà, le script reprend au
lendemain de la dernière date qui s'y trouve (relancer après une
interruption ne duplique donc rien, sans avoir à tout refaire).

Identifiants lus dans kibini_conf.yml (section 'matomo' : base, token_auth,
site_id, ip_interne), via kiblib.utils.conf.Config.get_config_matomo().

Usage :
    python data_matomo_logs_bokeh.py                              # 2026-03-31 -> hier, ou reprise auto
    python data_matomo_logs_bokeh.py --start 2026-03-31 --end 2026-04-30
    python data_matomo_logs_bokeh.py --out /chemin/vers/bokeh_logs.csv
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

DEFAULT_START = date(2026, 3, 31)  # avant : site de test, pas le portail de prod
# dossier data/ à la racine du dépôt (exclu par .gitignore)
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bokeh_visites_detail.csv")
PAGE_SIZE = 100
PAUSE_BETWEEN_APPELS = 0.2  # secondes, pour ne pas marteler l'API

# Champs bruts renvoyés par Live.getLastVisitsDetails (constatés sur bokeh).
FIELDNAMES = [
    "serverDate", "idVisit", "visitorId", "fingerprint", "visitCount",
    "visitorType", "firstActionTimestamp", "lastActionTimestamp",
    "serverTimePrettyFirstAction", "serverTimePretty", "visitDuration",
    "visitDurationPretty", "actions", "interactions", "searches", "events",
    "goalConversions", "visitConverted", "visitEcommerceStatus",
    "referrerType", "referrerTypeName", "referrerName", "referrerUrl",
    "referrerKeyword", "referrerKeywordPosition", "referrerSearchEngineUrl",
    "referrerSocialNetworkUrl", "referrerAIAssistantUrl", "provider",
    "providerName", "providerUrl", "deviceType", "deviceBrand",
    "deviceModel", "operatingSystem", "operatingSystemVersion", "browser",
    "browserName", "browserVersion", "languageCode", "language",
    "continent", "country", "region", "city", "latitude", "longitude",
    "resolution", "plugins", "visitIp", "visitLocalTime", "visitServerHour",
    "daysSinceFirstVisit", "daysSinceLastVisit", "secondsSinceFirstVisit",
    "secondsSinceLastVisit", "userId", "siteName", "siteCurrency",
    "origine", "customVariables", "pluginsIcons", "actionDetails",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extrait les logs de visite bruts Matomo (bokeh) dans un CSV."
    )
    parser.add_argument("--start", help="date de début AAAA-MM-JJ (défaut : reprise auto, sinon 2025-11-28)")
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


def flatten_visit(visit, ip_interne):
    """Aplati une visite Live.getLastVisitsDetails en une ligne de CSV.
    Les structures imbriquées (customVariables, pluginsIcons,
    actionDetails - dont le détail des pages vues, ici bien peuplé) sont
    conservées telles quelles, sérialisées en JSON."""
    row = {key: visit.get(key, "") for key in FIELDNAMES}
    row["origine"] = "interne" if visit.get("visitIp") == ip_interne else "externe"
    row["customVariables"] = json.dumps(visit.get("customVariables") or [], ensure_ascii=False)
    row["pluginsIcons"] = json.dumps(visit.get("pluginsIcons") or [], ensure_ascii=False)
    row["actionDetails"] = json.dumps(visit.get("actionDetails") or [], ensure_ascii=False)
    return row


start, end, out_path = parse_args()

conf = Config().get_config_matomo()
client = MatomoClient(base=conf["base"], token_auth=conf["token_auth"])
site_id = conf["site_id"]
ip_interne = conf["ip_interne"]

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
                writer.writerow(flatten_visit(visit, ip_interne))
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
