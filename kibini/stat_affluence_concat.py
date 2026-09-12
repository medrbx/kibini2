import pandas as pd

from kiblib.utils.db import DbConn
from kiblib.utils.frequentation import calculer_occupation

# Concatène le jeu open data "affluence horaire" en 2 parties, sans reconstruire
# ce qui est déjà publié sur data.lillemetropole.fr (statdb.stat_issues n'a de
# toute façon pas l'historique avant ~2019 - voir README) :
# - 2014-07-01 -> 2020-12-31 : export tel que publié à l'origine
#   (affluence_data_mel_2014-2020_brut.csv), à un correctif près confirmé par
#   comparaison mois par mois avec une extraction fraîche de statdb : les
#   colonnes prets/connexions_postes sont interverties sur toute l'année 2020
#   dans le fichier publié (concordance quasi parfaite une fois remises dans
#   le bon sens) - corrigé ici, aucune autre valeur modifiée. Colonne
#   connexions_wifi, impressions, frequentation_etude et entrees absentes du
#   jeu publié à l'origine (jamais suivies à l'époque) : reconstruites ici
#   depuis statdb.stat_wifi (profondeur historique dès 2016, 2014-2015
#   sortent à 0), statdb.stat_impressions (profondeur dès 2015, 2014 sort à
#   0) et statdb.stat_freq_etude (profondeur dès 2016, 2014-2015 sortent à
#   0) - le service n'existait probablement pas encore ces années-là, à
#   confirmer si besoin - et statdb.stat_entrees (profondeur dès 2009,
#   aucune lacune sur 2014-2020).
#   occupation reconstruite depuis statdb.stat_entrees_det (aussi profondeur
#   dès 2009, aucune lacune) - calcul et correction dans
#   kiblib.utils.frequentation (cumul entrées-sorties, écart de fermeture
#   réparti linéairement dans le temps).
# - 2021-01-01 -> aujourd'hui : extraction fraîche produite par
#   stat_affluence2oa.py (toutes les colonnes ci-dessus déjà incluses).
FICHIER_DATA_MEL = "data/openData/data/affluence_data_mel_2014-2020_brut.csv"
FICHIER_NOUVEAU = "data/openData/affluence_grand_plage_h_par_h.csv"
FICHIER_SORTIE = "data/openData/affluence_grand_plage_h_par_h_complet.csv"

COLONNES = [
    "date", "annee", "jour", "mois", "heure",
    "retours", "prets", "connexions_postes", "connexions_wifi", "impressions",
    "frequentation_etude", "entrees", "occupation"]

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

data_mel["heure_int"] = data_mel["heure"].str[:2].astype(int)

# Mêmes règles que stat_affluence2oa.py, appliquées ici a posteriori sur le
# fichier publié d'origine pour rester cohérent sur toute la période : lundi
# (médiathèque fermée au public, seuls les retours sont possibles) et
# amplitude d'ouverture 9h-19h pour les prêts (lots groupés hors ouverture,
# voir README) - on annule les valeurs concernées plutôt que de reconstruire.
lundi = data_mel["date"].dt.dayofweek == 0
data_mel.loc[lundi, ["prets", "connexions_postes"]] = 0
hors_ouverture = ~data_mel["heure_int"].between(9, 19)
data_mel.loc[hors_ouverture, "prets"] = 0

# Même filtre du lundi que dans stat_affluence2oa.py (médiathèque fermée au
# public, toute connexion ce jour-là est un test).
engine = DbConn().create_engine()
DEBUT = data_mel["date"].min()
FIN = data_mel["date"].max() + pd.Timedelta(days=1)

connexions_wifi = pd.read_sql(
    """
    SELECT DATE(start_wifi) AS date, HOUR(start_wifi) AS heure, COUNT(*) AS connexions_wifi
    FROM statdb.stat_wifi
    WHERE start_wifi >= %(debut)s AND start_wifi < %(fin)s
      AND DAYOFWEEK(start_wifi) != 2
    GROUP BY DATE(start_wifi), HOUR(start_wifi)
    """,
    con=engine, params={"debut": DEBUT, "fin": FIN})
connexions_wifi["date"] = pd.to_datetime(connexions_wifi["date"])

# HAVING > 0 sur les 2 requêtes SUM() ci-dessous : contrairement à COUNT(*),
# une somme peut ressortir à 0 (travail d'impression à 0 page, événement
# "sortie seule" Opteio - voir stat_affluence2oa.py) - déjà sans conséquence
# ici grâce au filtre "tout zéro" plus bas, mais gardé par cohérence.
impressions = pd.read_sql(
    """
    SELECT DATE(date_impression) AS date, HOUR(date_impression) AS heure,
        SUM(nb_pages_imprimees) AS impressions
    FROM statdb.stat_impressions
    WHERE date_impression >= %(debut)s AND date_impression < %(fin)s
      AND DAYOFWEEK(date_impression) != 2
    GROUP BY DATE(date_impression), HOUR(date_impression)
    HAVING SUM(nb_pages_imprimees) > 0
    """,
    con=engine, params={"debut": DEBUT, "fin": FIN})
impressions["date"] = pd.to_datetime(impressions["date"])

frequentation_etude = pd.read_sql(
    """
    SELECT DATE(datetime_entree) AS date, HOUR(datetime_entree) AS heure,
        COUNT(*) AS frequentation_etude
    FROM statdb.stat_freq_etude
    WHERE datetime_entree >= %(debut)s AND datetime_entree < %(fin)s
      AND DAYOFWEEK(datetime_entree) != 2
    GROUP BY DATE(datetime_entree), HOUR(datetime_entree)
    """,
    con=engine, params={"debut": DEBUT, "fin": FIN})
frequentation_etude["date"] = pd.to_datetime(frequentation_etude["date"])

entrees = pd.read_sql(
    """
    SELECT DATE(datetime) AS date, HOUR(datetime) AS heure, SUM(entrees) AS entrees
    FROM statdb.stat_entrees
    WHERE datetime >= %(debut)s AND datetime < %(fin)s
      AND DAYOFWEEK(datetime) != 2
    GROUP BY DATE(datetime), HOUR(datetime)
    HAVING SUM(entrees) > 0
    """,
    con=engine, params={"debut": DEBUT, "fin": FIN})
entrees["date"] = pd.to_datetime(entrees["date"])

entrees_det = pd.read_sql(
    """
    SELECT jour AS date, heure, SUM(entree) AS entree, SUM(sortie) AS sortie
    FROM statdb.stat_entrees_det
    WHERE datetime >= %(debut)s AND datetime < %(fin)s
      AND DAYOFWEEK(datetime) != 2
    GROUP BY jour, heure
    """,
    con=engine, params={"debut": DEBUT, "fin": FIN})
entrees_det["date"] = pd.to_datetime(entrees_det["date"])

occupation = calculer_occupation(entrees_det)

# heure_int (calculé plus haut) sert de clé de jointure - data_mel a 'heure'
# au format 'HH:00:00' (texte), les extractions ci-dessus au format entier
# (issu de HOUR() en SQL). Jointures externes (outer) : un créneau où seul
# le wifi, l'impression ou l'entrée a été utilisé n'existe pas dans le
# fichier data MEL d'origine (colonnes jamais suivies à l'époque), il ne
# faut pas le perdre.
data_mel = data_mel.merge(
    connexions_wifi.rename(columns={"heure": "heure_int"}),
    on=["date", "heure_int"], how="outer")
data_mel = data_mel.merge(
    impressions.rename(columns={"heure": "heure_int"}),
    on=["date", "heure_int"], how="outer")
data_mel = data_mel.merge(
    frequentation_etude.rename(columns={"heure": "heure_int"}),
    on=["date", "heure_int"], how="outer")
data_mel = data_mel.merge(
    entrees.rename(columns={"heure": "heure_int"}),
    on=["date", "heure_int"], how="outer")

for c in ["retours", "prets", "connexions_postes", "connexions_wifi", "impressions", "frequentation_etude", "entrees"]:
    data_mel[c] = data_mel[c].fillna(0).astype(int)

data_mel["annee"] = data_mel["date"].dt.year
data_mel["jour"] = data_mel["date"].dt.day
data_mel["mois"] = data_mel["date"].dt.month
data_mel["heure"] = data_mel["heure_int"].apply(lambda h: f"{h:02d}:00:00")
data_mel = data_mel.drop(columns=["heure_int"])
data_mel["date"] = data_mel["date"].dt.strftime("%Y-%m-%d")

# Les annulations lundi/hors-ouverture ci-dessus peuvent ramener une ligne à
# zéro sur les 6 métriques - on la retire, comme les créneaux sans activité
# n'apparaissent jamais dans la partie 2021+ (construite par jointure sur des
# comptages GROUP BY, jamais tous nuls par construction).
masque_tout_zero = (
    (data_mel["retours"] == 0) & (data_mel["prets"] == 0)
    & (data_mel["connexions_postes"] == 0) & (data_mel["connexions_wifi"] == 0)
    & (data_mel["impressions"] == 0) & (data_mel["frequentation_etude"] == 0)
    & (data_mel["entrees"] == 0))
data_mel = data_mel[~masque_tout_zero]

# occupation en jointure gauche, après le filtre "tout zéro" ci-dessus :
# contrairement aux autres métriques, 0 y est une valeur légitime (bâtiment
# vide en début/fin de journée), elle ne doit donc pas participer à ce
# filtre ni créer de nouvelles lignes par elle-même. data_mel['date'] est
# déjà une chaîne 'AAAA-MM-JJ' à ce stade (voir plus haut) - occupation
# reformatée à l'identique pour la jointure.
occupation["date"] = occupation["date"].dt.strftime("%Y-%m-%d")
data_mel["heure_int"] = data_mel["heure"].str[:2].astype(int)
data_mel = data_mel.merge(
    occupation.rename(columns={"heure": "heure_int"}),
    on=["date", "heure_int"], how="left")
data_mel["occupation"] = data_mel["occupation"].fillna(0).astype(int)
data_mel = data_mel.drop(columns=["heure_int"])

nouveau = pd.read_csv(FICHIER_NOUVEAU)
nouveau = nouveau[nouveau["date"] >= "2021-01-01"]

final = pd.concat([data_mel[COLONNES], nouveau[COLONNES]], ignore_index=True)
final = final.sort_values(["date", "heure"])
final.to_csv(FICHIER_SORTIE, index=False)
