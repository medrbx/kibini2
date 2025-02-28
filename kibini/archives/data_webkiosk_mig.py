import pandas as pd

from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.utils.date import get_date_and_time
from kiblib.webkiosk import Webkiosk

db_conn = DbConn().create_db_con()

c2l = Code2Libelle(db_conn)
c2l.get_val()

query = """
    SELECT
        heure_deb as session_date_heure_deb,
        heure_fin as session_date_heure_fin,
        espace as session_groupe,
        poste as session_poste,
        borrowernumber as borrowernumber,
        age as age,
        sexe as adh_sexe_code,
        ville as city,
        iris as altcontactcountry,
        branchcode,
        categorycode,
        fidelite as adh_inscription_nb_annees_adhesion
    FROM statdb.stat_webkiosk
"""
ch = 0
#for df in pd.read_sql(query, con=db_conn, chunksize=10000):
#    ch = ch + 1
#    webkiosk = Webkiosk(df=df, con=db_conn, c2l=c2l.dict_codes_lib)
#    webkiosk.get_webkiosk_statdb_data()
#    webkiosk.add_statdb_webkiosk_data()
#    #print(webkiosk.webkiosk_statdb_data)
#    print(ch)

webkiosk = Webkiosk()
webkiosk.ano_webkiosk_statdb_data()
