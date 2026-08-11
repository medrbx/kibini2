import pandas as pd
import datetime as dt

from kiblib.utils.db import DbConn
db_conn = DbConn().create_engine()

#On cree une liste contenant les futurs noms de colonne du dataframe
nom_colonnes=['date_impression',
              'wk_id',
              'utilisateur',
              'espace',
              'poste',
              'imprimante',
              'nb_credits_utilises',
              'nb_pages_imprimees',
              'type_impression']

# Import du fichier de donnees sur les impressions
prints = pd.read_csv("/home/kibini/wk_logs_prints.csv",names=nom_colonnes)

# Conversion de la colonne date_impression au format YYYY-MM-JJ
prints['date_impression'] = pd.to_datetime(prints['date_impression'],yearfirst=True)

prints['date_impression'] = prints['date_impression'].dt.strftime('%Y-%m-%d %H:%M:%S')

prints.loc[prints['type_impression']==0,['type_impression']] = 'N&B'
prints.loc[prints['type_impression']==1,['type_impression']] = 'COULEUR'

prints.to_sql("stat_impressions",con=db_conn,if_exists="append",index=False)

print(prints)