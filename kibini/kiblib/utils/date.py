import pandas as pd
import datetime

def dfcol_split_datetime(df, dt_col):
    tm = ['annee', 'mois', 'jour', 'jour_semaine', 'heure']
    strft = ['%Y', '%m', '%d', '%w', '%W', '%H']
    sdt = pd.to_datetime(df[dt_col], format='%Y%m%d %H%M%S', errors='coerce')
    for t, s in zip(tm, strft):
        col = f"{dt_col}_{t}"
        df[col] = sdt.dt.strftime(s)
    col_jour_semaine = f"{dt_col}_jour_semaine"
    if col_jour_semaine in df:
        wd = {
            '0': '7_Dimanche',
            '1': '1_Lundi',
            '2': '2_Mardi',
            '3': '3_Mercredi',
            '4': '4_Jeudi',
            '5': '5_Vendredi',
            '6': '6_Samedi'
        }
        df[col_jour_semaine] = df[col_jour_semaine].map(wd)
    return df

def get_date_and_time(param):
    dt = datetime.datetime.today()
    if param == 'now':                             # YYYY-MM-DD HH:MM:SS
        result = dt.strftime('%Y-%m-%d %H:%M:%S')
    elif param == 'today':                         # YYYY-MM-DD
        result = dt.strftime('%Y-%m-%d')
    elif param == 'today YYYYMMDD':                # YYYYMMDD
        result = dt.strftime('%Y%m%d')
    elif param == 'yesterday':                     # YYYY-MM-DD
        dt = dt - datetime.timedelta(days=1)
        result = dt.strftime('%Y-%m-%d')
    elif param == 'yesterday YYYYMMDD':            # YYYYMMDD
        dt = dt - datetime.timedelta(days=1)
        result = dt.strftime('%Y%m%d')
    return result

if __name__ == "__main__":
    r = get_date_and_time('yesterday YYYYMMDD')
    print(r)
