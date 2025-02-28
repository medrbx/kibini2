import pandas as pd

from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.utils.date import get_date_and_time
from kiblib.utils.log import Log
from kiblib.webkiosk import Webkiosk

db_conn = DbConn().create_db_con()

c2l = Code2Libelle(db_conn)
c2l.get_val()

df = pd.read_csv("data/wk_users_logs_consommations.csv",
                    names = ['session_date_heure_deb',
                             'session_date_heure_fin',
                             'session_groupe',
                             'session_poste',
                             'adh_cardnumber'])
webkiosk = Webkiosk(session_mode='poste', df=df, con=db_conn, c2l=c2l.dict_codes_lib)
webkiosk.get_webkiosk_statdb_data()
#webkiosk.add_statdb_webkiosk_data()
webkiosk.get_webkiosk_es_data()
#webkiosk.add_es_webkiosk_data()
print(webkiosk.webkiosk_es_data)
