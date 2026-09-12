import pandas as pd

from kiblib.utils.db import DbConn

# Concatène le jeu open data "affluence horaire" en 2 parties, sans reconstruire
# ce qui est déjà publié sur data.lillemetropole.fr (statdb.stat_issues n'a de
# toute façon pas l'historique avant ~2019 - voir README) :
# - 2014-07-01 -> 2020-12-31 : export tel que publié à l'origine
#   (affluence_data_mel_2014-2020_brut.csv), à un correctif près confirmé par
#   comparaison mois par mois avec une extraction fraîche de statdb : les
#   colonnes prets/connexions_postes sont interverties sur toute l'année 2020
#   dans le fichier publié (concordance quasi parfaite une fois remises dans
#   le bon sens) - corrigé ici, aucune autre valeur modifiée. Colonne
#   connexions_wifi absente du jeu publié à l'origine (jamais suivie à
#   l'époque) : reconstruite ici depuis statdb.stat_wifi, qui a de la
#   profondeur historique dès 2016 (2014-2015 sortent à 0 - le service wifi
#   public n'existait probablement pas encore, à confirmer si besoin).
# - 2021-01-01 -> aujourd'hui : extraction fraîche produite par
#   stat_affluence2oa.py (colonne connexions_wifi déjà incluse).
FICHIER_DATA_MEL = "data/openData/data/affluence_data_mel_2014-2020_brut.csv"
FICHIER_NOUVEAU = "data/openData/affluence_grand_plage_h_par_h.csv"
FICHIER_SORTIE = "data/openData/affluence_grand_plage_h_par_h_complet.csv"

COLONNES = [
    "date", "annee", "jour", "mois", "heure",
    "retours", "prets", "connexions_postes", "connexions_wifi"]

data_mel = pd.read_csv(FICHIER_DATA_MEL)
if "FID" in data_mel.columns:
    data_mel = data_mel.drop(columns=["FID"])

data_mel["date"] = pd.to_datetime(data_mel["date"])
masque_2020 = data_mel["date"].dt.year == 2020
data_mel.loc[masque_2020, ["prets", "connexions_postes"]] = (
    data_mel.loc[masque_2020, ["connexions_postes", "prets"]].values)

# Ambiguïté NaN du fichier publié (voir README) levée ici : créneaux sans
# activité mis à 0 explicite, comme sur la partie 2021+.
for c in ["retours", "prets", "connexions_postes"]:
    data_mel[c] = data_mel[c].fillna(0).astype(int)

# Même filtre du lundi que dans stat_affluence2oa.py (médiathèque fermée au
# public, toute connexion ce jour-là est un test).
engine = DbConn().create_engine()
connexions_wifi = pd.read_sql(
    """
    SELECT DATE(start_wifi) AS date, HOUR(start_wifi) AS heure, COUNT(*) AS connexions_wifi
    FROM statdb.stat_wifi
    WHERE start_wifi >= %(debut)s AND start_wifi < %(fin)s
      AND DAYOFWEEK(start_wifi) != 2
    GROUP BY DATE(start_wifi), HOUR(start_wifi)
    """,
    con=engine,
    params={"debut": data_mel["date"].min(), "fin": data_mel["date"].max() + pd.Timedelta(days=1)})
connexions_wifi["date"] = pd.to_datetime(connexions_wifi["date"])

# data_mel a 'heure' au format 'HH:00:00' (texte), connexions_wifi au format
# entier (issu de HOUR() en SQL) - clé de jointure normalisée en entier le
# temps de la fusion, puis reformatée à l'identique du fichier d'origine.
# Jointure externe (outer) : un créneau où seul le wifi a été utilisé
# n'existe pas dans le fichier data MEL d'origine (colonne jamais suivie à
# l'époque), il ne faut pas le perdre.
data_mel["heure_int"] = data_mel["heure"].str[:2].astype(int)
data_mel = data_mel.merge(
    connexions_wifi.rename(columns={"heure": "heure_int"}),
    on=["date", "heure_int"], how="outer")

for c in ["retours", "prets", "connexions_postes", "connexions_wifi"]:
    data_mel[c] = data_mel[c].fillna(0).astype(int)

data_mel["annee"] = data_mel["date"].dt.year
data_mel["jour"] = data_mel["date"].dt.day
data_mel["mois"] = data_mel["date"].dt.month
data_mel["heure"] = data_mel["heure_int"].apply(lambda h: f"{h:02d}:00:00")
data_mel = data_mel.drop(columns=["heure_int"])
data_mel["date"] = data_mel["date"].dt.strftime("%Y-%m-%d")

nouveau = pd.read_csv(FICHIER_NOUVEAU)
nouveau = nouveau[nouveau["date"] >= "2021-01-01"]

final = pd.concat([data_mel[COLONNES], nouveau[COLONNES]], ignore_index=True)
final = final.sort_values(["date", "heure"])
final.to_csv(FICHIER_SORTIE, index=False)
