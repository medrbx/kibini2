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
    geo_ville as adh_geo_ville,
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
date = "2023-12-27"
df = pd.read_sql(query, params={date}, con=db_conn)
adh = Adherent(df=df, con=db_conn, c2l=c2l.dict_codes_lib)
adh.get_adherent_statdb_data()
adh.get_adherent_es_data()
adh.df.to_csv("data/openData/data/adherents_2023_brut.csv", index=False)