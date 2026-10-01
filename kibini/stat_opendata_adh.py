import argparse
import re
from glob import glob
from os.path import basename

import pandas as pd

# Jeu open data "caractéristiques des adhérents" (data.lillemetropole.fr).
# Remplace stat_adh2oa.py + stat_opendata_fusion.py + stat_opendata_publish.py.
# À lancer depuis la racine du dépôt (chemins relatifs "data/...").
#
#   python kibini/stat_opendata_adh.py --date 2026-12-27
#
# Trois étapes enchaînées :
#   1. extraction : statdb.stat_adherents pour la date_extraction donnée ->
#      data/openData/data/adherents_<annee>.csv (colonnes internes adh_*)
#   2. fusion : ajoute cette année à l'historique multi-années le plus récent
#      -> data/adherents_2015-<annee>.csv.gz
#   3. publication : renomme vers le schéma grand public
#      -> data/openData/adherents_2015-<annee>_opendata.csv.gz
#
# Les colonnes d'attributs (action culturelle, arrêt Zèbre, structure
# collective) sont vides à partir de 2023 : stat_adherents.inscription_attribut
# ne contient plus le JSON qui permettait de les reconstituer (voir README,
# section "inscription_attribut a changé de format dans le temps").

DIR_DATA = "data"
DIR_OPENDATA = "data/openData"
DIR_ANNEES = "data/openData/data"
DEBUT = 2015

QUERY = """
SELECT
    date_extraction,
    age as adh_age,
    geo_ville as city,
    geo_roubaix_iris as adh_geo_rbx_iris_code,
    sexe as adh_sexe_code,
    inscription_code_carte as adh_inscription_carte_code,
    inscription_code_site as adh_inscription_site_code,
    inscription_attribut,
    inscription_fidelite as adh_inscription_nb_annees_adhesion,
    nb_venues_prets_mediatheque,
    nb_venues_prets_bus,
    nb_venues_postes_informatiques,
    nb_venues_wifi,
    nb_venues_salle_etude,
    nb_venues
FROM statdb.stat_adherents WHERE date_extraction = %s
"""

# Renommage des colonnes brutes vers des intitulés compréhensibles pour un
# public non technique, en vue de remplacer le jeu de données publié sur
# data.lillemetropole.fr (dernière mise à jour : 2020). Les codes techniques
# (categorycode Koha, codes d'attributs...) sont conservés à la demande,
# seulement renommés avec un préfixe "code_".
RENAME_MAP = {
    "date_extraction": "date_extraction",
    "adh_sexe_code": "code_sexe",
    "adh_sexe": "sexe",
    "age": "age_annees",
    "adh_age_code": "code_tranche_age",
    "adh_age_lib1": "tranche_age_detaillee",
    "adh_age_lib2": "tranche_age_large",
    "adh_age_lib3": "tranche_age_intermediaire",
    "city": "commune_de_residence_brute",
    "adh_geo_gentilite": "est_roubaisien",
    "adh_geo_ville": "commune_de_residence",
    "adh_geo_ville_bm": "fait_partie_bibliotheques_metropole",
    "adh_geo_ville_limitrophe": "commune_limitrophe_roubaix",
    "adh_geo_rbx_iris_code": "code_iris_roubaix",
    "adh_geo_rbx_iris": "nom_iris_roubaix",
    "adh_geo_rbx_quartier": "quartier_roubaix",
    "geo_rbx_secteur": "secteur_roubaix",
    "adh_inscription_site_code": "code_site_inscription",
    "adh_inscription_site": "site_inscription",
    "inscription_carte": "categorie_carte",
    "adh_inscription_carte_code": "code_categorie_carte",
    "adh_inscription_carte_type": "type_tarification_carte",
    "adh_inscription_carte_gratuite": "carte_gratuite_ou_payante",
    "adh_inscription_carte_prix": "prix_carte_euros",
    "adh_inscription_carte_personnalite_code": "code_type_adherent",
    "adh_inscription_carte_personnalite": "type_adherent",
    "adh_inscription_nb_annees_adhesion": "anciennete_adhesion_annees",
    "adh_inscription_nb_annees_adhesion_tra": "tranche_anciennete_adhesion",
    "inscription_attribut": "attributs_inscription_bruts",
    "adh_inscription_attribut_action_code": "code_action_culturelle",
    "adh_inscription_attribut_action": "action_culturelle_associee",
    "adh_inscription_attribut_bus_code": "code_arret_bus_zebre",
    "adh_inscription_attribut_bus": "arret_bus_zebre",
    "adh_inscription_attribut_collect_code": "code_type_structure_collective",
    "adh_inscription_attribut_collect": "type_structure_collective",
    "nb_venues_prets": "nombre_visites_emprunt",
    "nb_venues_prets_mediatheque": "nombre_visites_emprunt_mediatheque",
    "nb_venues_prets_bus": "nombre_visites_emprunt_zebre",
    "nb_venues_postes_informatiques": "nombre_visites_postes_informatiques",
    "nb_venues_wifi": "nombre_visites_wifi",
    "nb_venues_salle_etude": "nombre_visites_salle_etude",
    "nb_venues": "nombre_visites_total",
    "activite_emprunteur": "est_emprunteur",
    "activite_emprunteur_bus": "est_emprunteur_zebre",
    "activite_emprunteur_med": "est_emprunteur_mediatheque",
    "activite_salle_etude": "est_utilisateur_salle_etude",
    "activite_utilisateur_postes_informatiques": "est_utilisateur_postes_informatiques",
    "activite_utilisateur_wifi": "est_utilisateur_wifi",
    "activite": "profil_usage",
}

# Catégorie socio-professionnelle jugée non fiable (valeurs incohérentes
# constatées, ex. code PCS02 associé à un libellé "Artisans, commerçants..."
# non représentatif de la réalité observée) - exclue volontairement.
COLONNES_A_SUPPRIMER = [
    "adh_inscription_attribut_pcs_code",
    "adh_inscription_attribut_pcs",
]


def fichier_annee(annee):
    return f"{DIR_ANNEES}/adherents_{annee}.csv"


def fichier_historique(annee_fin):
    return f"{DIR_DATA}/adherents_{DEBUT}-{annee_fin}.csv.gz"


def historique_le_plus_recent():
    """Retourne (chemin, année de fin) de l'historique multi-années le plus récent."""
    candidats = []
    for chemin in glob(f"{DIR_DATA}/adherents_{DEBUT}-*.csv.gz"):
        m = re.fullmatch(rf"adherents_{DEBUT}-(\d{{4}})\.csv\.gz", basename(chemin))
        if m:
            candidats.append((int(m.group(1)), chemin))
    if not candidats:
        raise SystemExit(f"Aucun historique {DIR_DATA}/adherents_{DEBUT}-<annee>.csv.gz trouvé.")
    annee, chemin = max(candidats)
    return chemin, annee


def extraire(date):
    # imports ici : --only-publish doit fonctionner sans accès à la base
    from kiblib.utils.db import DbConn
    from kiblib.utils.code2libelle import Code2Libelle
    from kiblib.adherent import Adherent

    db_conn = DbConn().create_engine()
    c2l = Code2Libelle(db_conn)
    c2l.get_val()

    df = pd.read_sql(QUERY, params=(date,), con=db_conn)
    if df.empty:
        raise SystemExit(f"Aucune ligne dans statdb.stat_adherents pour date_extraction = {date}.")
    adh = Adherent(df=df, con=db_conn, c2l=c2l.dict_codes_lib)
    adh.get_adherent_opendata_data()
    # Export au format brut (colonnes internes adh_*), pas le schéma final grand
    # public : le renommage se fait une seule fois, sur le fichier fusionné.
    sortie = fichier_annee(date[:4])
    adh.df.to_csv(sortie, index=False)
    print(f"[1/3] extraction : {len(adh.df)} lignes -> {sortie}")


def fusionner(annee):
    chemin_histo, annee_histo = historique_le_plus_recent()
    historique = pd.read_csv(chemin_histo)
    nouvelle = pd.read_csv(fichier_annee(annee))

    annees_presentes = set(historique["date_extraction"].astype(str).str[:4])
    if str(annee) in annees_presentes:
        raise SystemExit(f"L'année {annee} est déjà dans {chemin_histo} : fusion annulée.")

    fusion = pd.concat([historique, nouvelle], ignore_index=True)
    sortie = fichier_historique(annee)
    fusion.to_csv(sortie, index=False, compression="gzip")
    print(f"[2/3] fusion : {chemin_histo} + {annee} -> {sortie} ({len(fusion)} lignes)")


def publier():
    chemin_histo, annee_fin = historique_le_plus_recent()
    df = pd.read_csv(chemin_histo)
    df = df.drop(columns=COLONNES_A_SUPPRIMER)
    df = df.rename(columns=RENAME_MAP)
    df = df[list(RENAME_MAP.values())]
    sortie = f"{DIR_OPENDATA}/adherents_{DEBUT}-{annee_fin}_opendata.csv.gz"
    df.to_csv(sortie, index=False, compression="gzip")
    print(f"[3/3] publication : {chemin_histo} -> {sortie} ({len(df)} lignes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__ or "Open data adhérents")
    parser.add_argument("--date", help="date_extraction à exporter (AAAA-MM-JJ), calée sur le cliché de fin d'année de data_adherents.py")
    parser.add_argument("--skip-extract", action="store_true", help="réutilise data/openData/data/adherents_<annee>.csv déjà produit")
    parser.add_argument("--only-publish", action="store_true", help="régénère seulement le fichier grand public depuis l'historique le plus récent")
    args = parser.parse_args()

    if args.only_publish:
        publier()
    else:
        if not args.date or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
            parser.error("--date AAAA-MM-JJ est requis")
        annee = args.date[:4]
        if not args.skip_extract:
            extraire(args.date)
        fusionner(annee)
        publier()
