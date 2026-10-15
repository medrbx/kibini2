"""
Nettoyage des informations d'appel téléphonique (contentieux) dans Koha.

Vide B_address (date de l'appel) et B_address2 (résultat de l'appel) pour les
adhérents qui n'ont plus aucun prêt en retard de plus de 28 jours. Les champs
du titre de recette (B_city, B_state, B_zipcode, B_country, contactnote) ne
sont pas touchés.

Les modifications passent par l'API REST officielle de Koha
(PUT /api/v1/patrons/{patron_id}), comme les suggestions dans la webapp
(webapp/services.py, mod_suggestion2). L'hôte Koha (clé "koha_staff") et les
identifiants viennent de la section "webservice" de conf/kibini_conf.yml.
Dans l'API, B_address et
B_address2 s'appellent altaddress_address et altaddress_address2.

Par défaut, le script ne modifie rien : il écrit seulement la liste des fiches
concernées. Ajouter --appliquer pour modifier Koha. Dans les deux cas, les
valeurs effacées sont sauvegardées dans un CSV, car elles n'existent nulle part
ailleurs.

    python adm_contentieux_nettoyage_appels.py                  # simulation
    python adm_contentieux_nettoyage_appels.py --appliquer      # modification
    python adm_contentieux_nettoyage_appels.py --appliquer --borrowernumber 12345   # une fiche de test

Avec --borrowernumber, seules les fiches indiquées sont traitées, et seulement
si elles remplissent le critère (aucun retard de plus de 28 jours).
"""
import argparse
from datetime import datetime
from os.path import join

import pandas as pd
import requests

from kiblib.utils.conf import Config
from kiblib.utils.db import DbConn
from kiblib.utils.log import Log

SEUIL_RETARD = 28

# adhérents avec des informations d'appel, sans prêt en retard de plus de 28 jours
QUERY = f"""
SELECT b.borrowernumber, b.cardnumber, b.categorycode, b.B_address, b.B_address2
FROM koha_prod.borrowers b
WHERE ((b.B_address IS NOT NULL AND TRIM(b.B_address) != '')
    OR (b.B_address2 IS NOT NULL AND TRIM(b.B_address2) != ''))
  AND NOT EXISTS (
    SELECT 1 FROM koha_prod.issues i
    WHERE i.borrowernumber = b.borrowernumber
      AND DATE(i.date_due) + INTERVAL {SEUIL_RETARD} DAY <= CURDATE()
  )
ORDER BY b.borrowernumber
"""

# champs obligatoires du corps d'un PUT /api/v1/patrons : repris tels quels
CHAMPS_OBLIGATOIRES = ["surname", "library_id", "category_id"]


def parse_args():
    parser = argparse.ArgumentParser(description="Vide les informations d'appel (B_address, B_address2) "
                                                 "des adhérents qui ne sont plus en retard.")
    parser.add_argument("--appliquer", action="store_true",
                        help="modifie réellement Koha (sinon : simulation)")
    parser.add_argument("--limite", type=int,
                        help="nombre maximum de fiches à traiter")
    parser.add_argument("--borrowernumber", type=int, nargs="+",
                        help="ne traiter que ces adhérents (s'ils remplissent le critère)")
    return parser.parse_args()


def vider_appel(koha_staff, borrowernumber, auth):
    url = f"{koha_staff}/api/v1/patrons/{borrowernumber}"
    patron = requests.get(url, auth=auth)
    patron.raise_for_status()
    body = {champ: patron.json()[champ] for champ in CHAMPS_OBLIGATOIRES}
    body.update({"altaddress_address": None, "altaddress_address2": None})
    requests.put(url, json=body, auth=auth).raise_for_status()


args = parse_args()
log = Log()
log.add_info(f"Lancement {log.script_name} ({'modification' if args.appliquer else 'simulation'})")

db_conn = DbConn().create_engine()
adherents = pd.read_sql(QUERY, db_conn)
if args.borrowernumber:
    demandes = ",".join(str(n) for n in args.borrowernumber)
    existants = set(pd.read_sql(f"SELECT borrowernumber FROM koha_prod.borrowers WHERE borrowernumber IN ({demandes})",
                                db_conn)["borrowernumber"])
    inexistants = sorted(set(args.borrowernumber) - existants)
    hors_critere = sorted(existants - set(adherents["borrowernumber"]))
    if inexistants:
        print(f"Non traités, adhérent inexistant : {inexistants}")
        log.add_info(f"borrowernumber inexistants, non traités : {inexistants}")
    if hors_critere:
        print(f"Non traités, pas d'information d'appel ou retard de plus de {SEUIL_RETARD} jours : {hors_critere}")
        log.add_info(f"borrowernumber hors critère, non traités : {hors_critere}")
    adherents = adherents[adherents["borrowernumber"].isin(args.borrowernumber)]
if args.limite:
    adherents = adherents.head(args.limite)

# sauvegarde des valeurs avant effacement (un fichier par lancement, pour ne jamais écraser une sauvegarde)
dir_data = Config().get_config_data()
file_out = join(dir_data, f"contentieux_nettoyage_appels_{datetime.now():%Y%m%d_%H%M%S}.csv")
adherents.to_csv(file_out, index=False)
print(f"{len(adherents)} fiches concernées, sauvegardées dans {file_out}")
log.add_info(f"{len(adherents)} fiches concernées, sauvegarde : {file_out}")

if not args.appliquer:
    print("Simulation : aucune modification. Relancer avec --appliquer pour modifier Koha.")
else:
    conf = Config().get_config_webservice()
    koha_staff = conf["koha_staff"]
    auth = (conf["user"], conf["pwd"])
    ok, echecs = 0, []
    for borrowernumber in adherents["borrowernumber"]:
        try:
            vider_appel(koha_staff, borrowernumber, auth)
            ok += 1
        except requests.RequestException as exc:
            echecs.append(borrowernumber)
            log.add_info(f"échec {borrowernumber} : {exc}")
    print(f"{ok} fiches nettoyées, {len(echecs)} échecs")
    log.add_info(f"{ok} fiches nettoyées, {len(echecs)} échecs : {echecs}")

log.add_info(f"Fin traitement {log.script_name}\n\n")
