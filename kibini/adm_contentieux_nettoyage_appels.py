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
concernées. Ajouter --appliquer pour modifier Koha.

Avec --appliquer, chaque fiche est relue dans Koha juste avant d'être modifiée
(la base lue par DbConn est une copie rechargée chaque nuit, qui ne voit ni les
nettoyages du jour ni les nouveaux retards) :
- une fiche dont les champs d'appel sont déjà vides est ignorée ;
- une fiche qui a, dans Koha, un prêt en cours en retard d'au moins 28 jours
  est ignorée (GET /api/v1/checkouts ; le compte webservice doit avoir le droit
  de circulation circulate_remaining_permissions).
--limite porte sur le nombre de fiches réellement modifiées : relancer le
script avec la même limite traite donc les fiches suivantes. Les valeurs lues
dans Koha sont ajoutées au CSV de sauvegarde avant chaque effacement, car elles
n'existent nulle part ailleurs.

    python adm_contentieux_nettoyage_appels.py                  # simulation
    python adm_contentieux_nettoyage_appels.py --appliquer      # modification
    python adm_contentieux_nettoyage_appels.py --appliquer --borrowernumber 12345   # une fiche de test

Avec --borrowernumber, seules les fiches indiquées sont traitées, et seulement
si elles remplissent le critère (aucun retard de plus de 28 jours).
"""
import argparse
from datetime import date, datetime
from os.path import exists, join

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
                        help="nombre maximum de fiches à modifier (en simulation : à lister)")
    parser.add_argument("--borrowernumber", type=int, nargs="+",
                        help="ne traiter que ces adhérents (s'ils remplissent le critère)")
    return parser.parse_args()


# arrêt du traitement après ce nombre d'échecs consécutifs (API injoignable, droits insuffisants...)
MAX_ECHECS_CONSECUTIFS = 5


def lire_fiche(koha_staff, borrowernumber, auth):
    patron = requests.get(f"{koha_staff}/api/v1/patrons/{borrowernumber}", auth=auth)
    patron.raise_for_status()
    return patron.json()


def retard_max_koha(koha_staff, borrowernumber, auth):
    # prêts en cours de l'adhérent dans Koha (_per_page=-1 : tous les résultats)
    checkouts = requests.get(f"{koha_staff}/api/v1/checkouts",
                             params={"patron_id": borrowernumber, "_per_page": -1}, auth=auth)
    checkouts.raise_for_status()
    retards = [(date.today() - pd.Timestamp(c["due_date"]).date()).days for c in checkouts.json()]
    return max(retards, default=None)


def vider_appel(koha_staff, patron, auth):
    body = {champ: patron[champ] for champ in CHAMPS_OBLIGATOIRES}
    body.update({"altaddress_address": None, "altaddress_address2": None})
    requests.put(f"{koha_staff}/api/v1/patrons/{patron['patron_id']}", json=body, auth=auth).raise_for_status()


def est_vide(valeur):
    return valeur is None or str(valeur).strip() == ""


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
print(f"{len(adherents)} fiches remplissent le critère dans la base lue")
log.add_info(f"{len(adherents)} fiches remplissent le critère dans la base lue")

# sauvegarde : un fichier par lancement, pour ne jamais écraser une sauvegarde
dir_data = Config().get_config_data()
file_out = join(dir_data, f"contentieux_nettoyage_appels_{datetime.now():%Y%m%d_%H%M%S}.csv")

if not args.appliquer:
    liste = adherents.head(args.limite) if args.limite else adherents
    liste.to_csv(file_out, index=False)
    for row in liste.itertuples(index=False):
        print(f"{row.cardnumber} : à nettoyer")
    print(f"Simulation : aucune modification. {len(liste)} fiches listées dans {file_out}")
    print("Relancer avec --appliquer pour modifier Koha.")
else:
    conf = Config().get_config_webservice()
    koha_staff = conf["koha_staff"]
    auth = (conf["user"], conf["pwd"])
    modifiees, deja_vides, en_retard, echecs, echecs_consecutifs = 0, 0, [], [], 0
    for row in adherents.itertuples(index=False):
        if args.limite and modifiees >= args.limite:
            break
        try:
            patron = lire_fiche(koha_staff, row.borrowernumber, auth)
            if est_vide(patron.get("altaddress_address")) and est_vide(patron.get("altaddress_address2")):
                deja_vides += 1
                print(f"{row.cardnumber} : déjà vide dans Koha, ignorée")
                continue
            retard = retard_max_koha(koha_staff, row.borrowernumber, auth)
            # même règle que la requête SQL : échéance + 28 jours <= aujourd'hui
            if retard is not None and retard >= SEUIL_RETARD:
                en_retard.append(row.borrowernumber)
                echecs_consecutifs = 0
                print(f"{row.cardnumber} : retard de {retard} jours dans Koha, ignorée")
                continue
            # sauvegarde des valeurs lues dans Koha, écrite avant l'effacement
            pd.DataFrame([{"borrowernumber": row.borrowernumber, "cardnumber": row.cardnumber,
                           "categorycode": row.categorycode,
                           "B_address": patron.get("altaddress_address"),
                           "B_address2": patron.get("altaddress_address2")}]).to_csv(
                file_out, mode="a", header=not exists(file_out), index=False)
            vider_appel(koha_staff, patron, auth)
            modifiees += 1
            print(f"{row.cardnumber} : nettoyée")
            echecs_consecutifs = 0
        except requests.RequestException as exc:
            echecs.append(row.borrowernumber)
            echecs_consecutifs += 1
            log.add_info(f"échec {row.borrowernumber} : {exc}")
            print(f"{row.cardnumber} : échec ({exc})")
            if echecs_consecutifs >= MAX_ECHECS_CONSECUTIFS:
                print(f"Arrêt après {MAX_ECHECS_CONSECUTIFS} échecs consécutifs : vérifier l'accès à l'API (voir le journal).")
                log.add_info(f"arrêt après {MAX_ECHECS_CONSECUTIFS} échecs consécutifs")
                break
    print(f"{modifiees} fiches nettoyées, {deja_vides} déjà vides dans Koha (ignorées), "
          f"{len(en_retard)} en retard d'au moins {SEUIL_RETARD} jours dans Koha (ignorées), {len(echecs)} échecs")
    if exists(file_out):
        print(f"Sauvegarde des valeurs effacées : {file_out}")
    log.add_info(f"{modifiees} fiches nettoyées, {deja_vides} déjà vides, en retard dans Koha : {en_retard}, "
                 f"{len(echecs)} échecs : {echecs} ; sauvegarde : {file_out}")

log.add_info(f"Fin traitement {log.script_name}\n\n")
