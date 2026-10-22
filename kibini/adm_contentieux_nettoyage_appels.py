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

Les fiches à traiter viennent d'un rapport SQL sauvegardé dans Koha, appelé via
svc/report comme les listes de la webapp (rapport RAPPORT_NETTOYAGE_APPELS, sur
l'hôte "base" de la section "webservice") : les données sont donc
celles de la production, au moment de l'appel. Le rapport est limité à 500
fiches (LIMIT 500) : relancer le script traite les suivantes, puisque les fiches
nettoyées sortent du rapport. Critère du rapport : informations d'appel
renseignées, et aucun prêt en cours dont l'échéance + 28 jours est atteinte.

Par défaut, le script ne modifie rien : il écrit seulement la liste des fiches
concernées. Ajouter --appliquer pour modifier Koha.

Avec --appliquer, chaque fiche est relue dans Koha juste avant d'être modifiée
(filet de sécurité, le rapport pouvant être mis en cache par Koha) :
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
si elles figurent dans la réponse du rapport.
"""
import argparse
from datetime import date, datetime
from os.path import exists, join

import pandas as pd
import requests

from kiblib.utils.conf import Config
from kiblib.utils.log import Log

SEUIL_RETARD = 28

# rapport SQL Koha sauvegardé (même convention que les rapports de webapp/services.py)
RAPPORT_NETTOYAGE_APPELS = "343"
# colonnes renvoyées par le rapport Koha, dans l'ordre de son SELECT
COLONNES_RAPPORT = ["borrowernumber", "cardnumber", "categorycode", "B_address", "B_address2"]

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
                        help="ne traiter que ces adhérents (s'ils figurent dans le rapport)")
    return parser.parse_args()


# arrêt du traitement après ce nombre d'échecs consécutifs (API injoignable, droits insuffisants...)
MAX_ECHECS_CONSECUTIFS = 5


def lire_rapport(conf):
    # rapport SQL sauvegardé dans Koha, appelé via svc/report comme dans la webapp (webapp/services.py)
    reponse = requests.get(f"{conf['base']}/cgi-bin/koha/svc/report", params={"id": RAPPORT_NETTOYAGE_APPELS})
    reponse.raise_for_status()
    lignes = reponse.json()
    if not isinstance(lignes, list):
        raise RuntimeError(f"réponse inattendue du rapport Koha : {str(lignes)[:200]}")
    adherents = pd.DataFrame(lignes, columns=COLONNES_RAPPORT)
    adherents["borrowernumber"] = adherents["borrowernumber"].astype(int)
    return adherents


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

conf = Config().get_config_webservice()
adherents = lire_rapport(conf)
print(f"{len(adherents)} fiches renvoyées par le rapport Koha {RAPPORT_NETTOYAGE_APPELS} (500 au plus)")
log.add_info(f"{len(adherents)} fiches renvoyées par le rapport Koha {RAPPORT_NETTOYAGE_APPELS}")
if args.borrowernumber:
    absents = sorted(set(args.borrowernumber) - set(adherents["borrowernumber"]))
    if absents:
        print(f"Non traités, absents du rapport (pas d'information d'appel, retard d'au moins {SEUIL_RETARD} jours, "
              f"au-delà des 500 premières fiches, ou adhérent inexistant) : {absents}")
        log.add_info(f"borrowernumber absents du rapport, non traités : {absents}")
    adherents = adherents[adherents["borrowernumber"].isin(args.borrowernumber)]

# sauvegarde : un fichier par lancement, pour ne jamais écraser une sauvegarde
dir_data = Config().get_config_data()
file_out = join(dir_data, f"contentieux_nettoyage_appels_{datetime.now():%Y%m%d_%H%M%S}.csv")
n = 2
while exists(file_out):   # deux lancements dans la même seconde
    file_out = join(dir_data, f"contentieux_nettoyage_appels_{datetime.now():%Y%m%d_%H%M%S}_{n}.csv")
    n += 1

if not args.appliquer:
    liste = adherents.head(args.limite) if args.limite else adherents
    liste.to_csv(file_out, index=False)
    for row in liste.itertuples(index=False):
        print(f"{row.cardnumber} : à nettoyer")
    print(f"Simulation : aucune modification. {len(liste)} fiches listées dans {file_out}")
    print("Relancer avec --appliquer pour modifier Koha.")
else:
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
