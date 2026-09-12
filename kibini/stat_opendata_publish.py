import pandas as pd

# Renommage des colonnes brutes de data/adherents_2015-2025.csv.gz vers des
# intitulés compréhensibles pour un public non technique, en vue de remplacer
# le jeu de données publié sur data.lillemetropole.fr (dernière mise à jour :
# 2020). Les codes techniques (categorycode Koha, codes d'attributs...) sont
# conservés à la demande, seulement renommés avec un préfixe "code_".
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

# À éditer avant chaque lancement, en cohérence avec FICHIER_SORTIE de
# stat_opendata_fusion.py.
FICHIER_HISTORIQUE = "data/adherents_2015-2025.csv.gz"
FICHIER_SORTIE = "data/openData/adherents_2015-2025_opendata.csv.gz"

df = pd.read_csv(FICHIER_HISTORIQUE)
df = df.drop(columns=COLONNES_A_SUPPRIMER)
df = df.rename(columns=RENAME_MAP)
df = df[list(RENAME_MAP.values())]
df.to_csv(FICHIER_SORTIE, index=False, compression="gzip")
