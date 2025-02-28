import pandas as pd

from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.utils.date import get_date_and_time
from kiblib.utils.log import Log
from kiblib.pret import Pret

log = Log()
log.add_info('Lancement')

date = get_date_and_time('yesterday')
print(date)

db_conn = DbConn().create_db_con()
print(db_conn)

#c2l = Code2Libelle(db_conn)
#c2l.get_val()

chunksize = 10000
