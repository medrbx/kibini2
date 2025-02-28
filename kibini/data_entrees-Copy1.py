import sys
import pandas as pd
import datetime
from os.path import join

from kiblib.utils.db import DbConn
from kiblib.utils.conf import Config
from kiblib.utils.date import get_date_and_time

db_conn = DbConn().create_engine()

entrees = pd.read_sql("SELECT * FROM stat_entrees", con=db_conn)
dir_data = Config().get_config_data()
today = get_date_and_time('today YYYYMMDD')
file_out = join(dir_data, f"entrees_{today}.csv.gz")
entrees.to_csv(file_out, index=False)

#entrees['datetime'] = pd.to_datetime(entrees['datetime'])

dataframes = []
for filename in sys.argv[1:]:
    f = pd.ExcelFile(filename)
    for sheet_name in f.sheet_names:
        year = int(sheet_name[0:4])
        month = int(sheet_name[5:7].lstrip("0"))
        day = int(sheet_name[8:10].lstrip("0"))
        df = f.parse(sheet_name = sheet_name, names = ['datetime', 'entrees'])
        df = df[~df['datetime'].isna()]
        df = df[df['entrees'] != 0]
        df = df[df['datetime'].str.match('^\d')]
        df['datetime'] = df['datetime'].str.lstrip("0")
        df['datetime'] = df['datetime'].str.rstrip("H")
        df['datetime'] = df['datetime'].apply(lambda x : datetime.datetime(year, month, day, int(x)))
        dataframes.append(df)

df = pd.concat(dataframes)
df = df.sort_values(by='datetime')
df = df.drop_duplicates()

df.to_sql('stat_entrees', con=db_conn, if_exists='append', index=False)

print(df)
