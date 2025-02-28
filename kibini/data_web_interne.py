#Permet d'ajouter un repertoire dans lequel pyhton recherche le module à importer
#import sys
#sys.path.append('/home/kibini/kibini2/kibini') # FP : placé le notebook dans kibini2/kibini pour éviter cette manip

import pandas as pd
from kiblib.utils.db import DbConn
from datetime import datetime as dt

#Le tableau listant les periodes de vacances scolaires s'arrete en 2026
#Ce script verifie que la date limite de verification de la periode ne soit pas depasse

if dt.today().date() > dt(2026,12,31).date():
    print("ERREUR La date limite du tableau de verification des vacances scolaire est depassee")
    exit()

# Définition d'une variable contenant les paramétrages de connexions à statdb
db_conn = DbConn().create_engine()

# Import du fichier
stat_web_interne = pd.read_csv("/home/kibini/stat_web_interne.csv",encoding="utf-16")

#Liste des colonnes à garder pour import dans statdb
colonnes_to_keep = ['Date',
                    'Visites',
                    'Vues',
                    'Utilisateurs',
                    'Taux de conversion']

web_interne_to_import = stat_web_interne[colonnes_to_keep]
web_interne_to_import.head(10)

#creation d'un dictionnaire de correspondance des données PIWIK et STATDB
dico_stats_web = {'Date':'date',
                  'periode':'periode',
                  'Visites':'visites',
                  'Vues': 'pages_vues',
                  'Utilisateurs':'utilisateurs',
                  'Taux de conversion':'taux_conversion'
                 }

# Rennomage des colonnes
web_interne_to_import = web_interne_to_import.rename(columns=dico_stats_web)

# Import du module re (Regular expression Operation)
import re

# Fonction pour extraire les chiffres d'une chaîne de caractère
def extraire_chiffres(chaine):
    chiffres = re.findall(r'([^%]+)', chaine)
    return float(chiffres[0]) if chiffres else None


# Appliquer la fonction à la colonne 'taux_conversion'
web_interne_to_import['taux_conversion'] = web_interne_to_import['taux_conversion'].apply(extraire_chiffres)


# On arrondi à l'unité la valeur dans TAUX_CONVERSION, puis on transforme en INT
web_interne_to_import['taux_conversion'] = round(web_interne_to_import['taux_conversion'],0).astype(int)


#import d'un fichier vacances scolaires
verif_vacances = pd.read_csv("/home/kibini/kibini2/kibini/kiblib/vacances_scolaires_fr.csv")
verif_vacances

# Ajout d'une colonne periode et des valeurs SCOLAIRE ou VACANCES
verif_vacances.loc[verif_vacances['vacances_zone_b']==False,['periode']] = 'scolaire'
verif_vacances.loc[verif_vacances['vacances_zone_b']==True,['periode']] = 'vacances'

# On ne garde que la date et la periode
verif_vacances = verif_vacances[['date','periode']]

# Ajout d'une colonne origine avec la valeur INTERNE
web_interne_to_import['origine'] = 'interne'

#Jointure gauche des deux tables
web_interne_to_import = web_interne_to_import.merge(verif_vacances,left_on='date',right_on='date',how='left')

# Import des données dans statdb
web_interne_to_import.to_sql('stat_web2',con=db_conn,if_exists='append',index=False)

# Affichage du résultat
print(web_interne_to_import)