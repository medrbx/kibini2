import pandas as pd

from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.utils.date import get_date_and_time
from kiblib.utils.log import Log
from kiblib.webkiosk import Webkiosk

db_conn = DbConn().create_db_con()

c2l = Code2Libelle(db_conn)
c2l.get_val()

#for df in pd.read_csv("data/wk_web_wifi_logs.csv",
#                    names = ['wifi_session_id',
#                             'session_date_heure_deb',
#                             'session_date_heure_fin',
#                             'adh_cardnumber'],
#                    chunksize=10000):
for df in pd.read_csv("data/stat_wifi_202011221014.csv", chunksize=10000):
    webkiosk = Webkiosk(session_mode='wifi', df=df, con=db_conn, c2l=c2l.dict_codes_lib)
    webkiosk.get_webkiosk_statdb_data()
    webkiosk.add_statdb_webkiosk_data()
    webkiosk.get_webkiosk_es_data()
    #webkiosk.add_es_webkiosk_data()
    #print(webkiosk.df.columns)
