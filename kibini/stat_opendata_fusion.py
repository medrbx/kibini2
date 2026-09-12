import pandas as pd

# Ajoute une nouvelle année (export brut produit par stat_adh2oa.py) à
# l'historique multi-années. À éditer avant chaque lancement : le fichier
# historique existant, le nouvel export annuel, et le nom du fichier de
# sortie (qui devient le nouvel historique de référence).
FICHIER_HISTORIQUE = "data/adherents_2015-2025.csv.gz"
NOUVELLE_ANNEE = "data/openData/data/adherents_2026.csv"
FICHIER_SORTIE = "data/adherents_2015-2026.csv.gz"

historique = pd.read_csv(FICHIER_HISTORIQUE)
nouvelle_annee = pd.read_csv(NOUVELLE_ANNEE)

# La nouvelle année n'aura pas les colonnes d'attributs (action culturelle,
# arrêt Zèbre, structure collective) correctement renseignées : depuis 2023,
# stat_adherents.inscription_attribut ne contient plus le JSON qui permettait
# de les reconstituer (voir README, section "inscription_attribut a changé de
# format dans le temps") - colonnes absentes ou vides, pas une erreur de ce
# script.
fusion = pd.concat([historique, nouvelle_annee], ignore_index=True)
fusion.to_csv(FICHIER_SORTIE, index=False, compression="gzip")
