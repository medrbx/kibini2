import pandas as pd

df = pd.read_csv("_tmp_affluence_v2.csv")
df['date'] = pd.to_datetime(df['date'])
df['heure_h'] = pd.to_datetime(df['heure'], format='%H:%M:%S').dt.hour

print("Lignes:", len(df))
print("min/max date:", df['date'].min(), df['date'].max())
print()

print("--- doublons ---")
print(df.duplicated(subset=['date','heure']).sum())
print()

print("--- coherence jour/mois/annee ---")
incoh = df[(df['jour'] != df['date'].dt.day) | (df['mois'] != df['date'].dt.month) | (df['annee'] != df['date'].dt.year)]
print(len(incoh))
print()

print("--- valeurs manquantes / negatives ---")
print(df.isna().sum().sum(), "NaN")
for c in ['retours','prets','connexions_postes']:
    print(c, 'neg:', (df[c]<0).sum())
print()

print("--- plage horaire des prets ---")
print(df[df['prets']>0]['heure_h'].value_counts().sort_index())
print()

print("--- prets hors [9,19] : doit etre 0 ---")
print((df[(df['prets']>0) & ((df['heure_h']<9)|(df['heure_h']>19))]).shape[0])
print()

print("--- comparaison avec avant (lignes en moins) ---")
print("nouveau total:", len(df))
print()

print("--- verif les 7 dates anomalies : prets doit etre absent/0 a ces heures ---")
checks = [
    ('2021-02-04', 3), ('2022-03-10', 21), ('2023-11-23', 21),
    ('2023-11-30', 21), ('2023-12-09', 21), ('2025-05-16', 3), ('2025-12-24', 3),
]
for d, h in checks:
    row = df[(df['date']==d) & (df['heure_h']==h)]
    print(d, h, 'h ->', row[['retours','prets','connexions_postes']].values if len(row) else 'absent')
print()

print("--- stats generales ---")
print(df[['retours','prets','connexions_postes']].describe())
print()

print("--- annee coverage ---")
print(df['annee'].value_counts().sort_index())
