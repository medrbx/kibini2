import pandas as pd

from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.utils.date import get_date_and_time
from kiblib.adherent import Adherent

db_conn = DbConn().create_engine()
c2l = Code2Libelle(db_conn)
c2l.get_val()
chunksize = 1000

query = """
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
# Date de l'extraction annuelle à exporter (calée sur le cliché de fin
# d'année produit par data_adherents.py) - à éditer avant chaque lancement.
date = "2023-12-27"
df = pd.read_sql(query, params={date}, con=db_conn)
adh = Adherent(df=df, con=db_conn, c2l=c2l.dict_codes_lib)
adh.get_adherent_opendata_data()
# Export au format brut (colonnes internes adh_*), pas le schéma final grand
# public : c'est le format attendu par data/openData/data/fusion_fichiers.ipynb
# et par stat_opendata_fusion.py pour l'agrégation multi-années. Le
# renommage/nettoyage vers le schéma public se fait ensuite, une seule fois,
# via stat_opendata_publish.py sur le fichier multi-années fusionné - pas ici.
adh.df.to_csv(f"data/openData/data/adherents_{date[:4]}.csv", index=False)