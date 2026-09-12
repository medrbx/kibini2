import argparse
from datetime import date

import pandas as pd

from kiblib.utils.db import DbConn

# Reconstitue le jeu "affluence horaire" publié sur data.lillemetropole.fr
# (ville_roubaix:affluence_et_activites_de_la_grand_plage_h_par_h_depuis_2014),
# arrêté au 2020-12-31, enrichi de colonnes absentes du jeu d'origine
# (connexions_wifi, impressions). Prêts/retours viennent de
# statdb.stat_issues (branche MED = Grand Plage), connexions postes de
# statdb.stat_webkiosk (à la demande - ni cette table ni
# stat_sessions_webkiosk ne sont alimentées en continu actuellement, voir
# README, section "Jeu open data affluence horaire"), wifi de
# statdb.stat_wifi, impressions (nombre de pages) de statdb.stat_impressions.


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reconstitue le jeu 'affluence horaire' entre deux dates."
    )
    parser.add_argument(
        "--start-date", required=True,
        help="Début de la plage à traiter (YYYY-MM-DD), inclus.")
    parser.add_argument(
        "--end-date", required=True,
        help="Fin de la plage à traiter (YYYY-MM-DD), exclue.")
    args = parser.parse_args()
    return date.fromisoformat(args.start_date), date.fromisoformat(args.end_date)


DATE_DEBUT, DATE_FIN = parse_args()

engine = DbConn().create_engine()

# HOUR(issuedate) BETWEEN 9 AND 19 (amplitude d'ouverture) exclut des lots de
# prêts groupés en rafale hors ouverture (plusieurs adhérents, chacun
# plusieurs exemplaires, en quelques secondes - ex. 70 prêts en 17s à 3h01 le
# 2021-02-04) : de vrais prêts mais qui ne représentent pas de la
# fréquentation réelle sur ce créneau (traitement automatisé, cause exacte
# non identifiée - voir README).
# DAYOFWEEK != 2 (lundi) : la médiathèque est fermée au public le lundi, seuls
# les retours (boîte de retour) sont possibles ce jour-là - tout prêt ou toute
# connexion poste enregistrés un lundi sont un test, pas de la fréquentation.
prets = pd.read_sql(
    """
    SELECT DATE(issuedate) AS date, HOUR(issuedate) AS heure, COUNT(*) AS prets
    FROM statdb.stat_issues
    WHERE branch = 'MED' AND issuedate >= %(debut)s AND issuedate < %(fin)s
      AND HOUR(issuedate) BETWEEN 9 AND 19
      AND DAYOFWEEK(issuedate) != 2
    GROUP BY DATE(issuedate), HOUR(issuedate)
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

retours = pd.read_sql(
    """
    SELECT DATE(returndate) AS date, HOUR(returndate) AS heure, COUNT(*) AS retours
    FROM statdb.stat_issues
    WHERE branch = 'MED' AND returndate >= %(debut)s AND returndate < %(fin)s
    GROUP BY DATE(returndate), HOUR(returndate)
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

connexions = pd.read_sql(
    """
    SELECT DATE(heure_deb) AS date, HOUR(heure_deb) AS heure, COUNT(*) AS connexions_postes
    FROM statdb.stat_webkiosk
    WHERE heure_deb >= %(debut)s AND heure_deb < %(fin)s
      AND DAYOFWEEK(heure_deb) != 2
    GROUP BY DATE(heure_deb), HOUR(heure_deb)
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

# Même filtre du lundi que pour connexions_postes : la médiathèque étant
# fermée au public, une connexion wifi ce jour-là est un test.
connexions_wifi = pd.read_sql(
    """
    SELECT DATE(start_wifi) AS date, HOUR(start_wifi) AS heure, COUNT(*) AS connexions_wifi
    FROM statdb.stat_wifi
    WHERE start_wifi >= %(debut)s AND start_wifi < %(fin)s
      AND DAYOFWEEK(start_wifi) != 2
    GROUP BY DATE(start_wifi), HOUR(start_wifi)
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

# impressions = nombre de pages imprimées (volume, pas un comptage de
# travaux d'impression) - même filtre du lundi que les autres colonnes.
impressions = pd.read_sql(
    """
    SELECT DATE(date_impression) AS date, HOUR(date_impression) AS heure,
        SUM(nb_pages_imprimees) AS impressions
    FROM statdb.stat_impressions
    WHERE date_impression >= %(debut)s AND date_impression < %(fin)s
      AND DAYOFWEEK(date_impression) != 2
    GROUP BY DATE(date_impression), HOUR(date_impression)
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

# entrees = comptage de passages physiques (capteur Opteio), déjà agrégé à
# l'heure dans stat_entrees. Même filtre du lundi que les autres colonnes.
entrees = pd.read_sql(
    """
    SELECT DATE(datetime) AS date, HOUR(datetime) AS heure, SUM(entrees) AS entrees
    FROM statdb.stat_entrees
    WHERE datetime >= %(debut)s AND datetime < %(fin)s
      AND DAYOFWEEK(datetime) != 2
    GROUP BY DATE(datetime), HOUR(datetime)
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

df = prets.merge(retours, on=["date", "heure"], how="outer")
df = df.merge(connexions, on=["date", "heure"], how="outer")
df = df.merge(connexions_wifi, on=["date", "heure"], how="outer")
df = df.merge(impressions, on=["date", "heure"], how="outer")
df = df.merge(entrees, on=["date", "heure"], how="outer")

# Contrairement au jeu publié jusqu'ici (cf. README), les créneaux sans
# activité sont mis à 0 explicitement plutôt que laissés vides - ambiguïté
# NaN documentée comme point à corriger.
for c in ["prets", "retours", "connexions_postes", "connexions_wifi", "impressions", "entrees"]:
    df[c] = df[c].fillna(0).astype(int)

df["date"] = pd.to_datetime(df["date"])
df["annee"] = df["date"].dt.year
df["jour"] = df["date"].dt.day
df["mois"] = df["date"].dt.month
df["heure"] = df["heure"].apply(lambda h: f"{h:02d}:00:00")
df["date"] = df["date"].dt.strftime("%Y-%m-%d")

df = df[[
    "date", "annee", "jour", "mois", "heure",
    "retours", "prets", "connexions_postes", "connexions_wifi", "impressions", "entrees"]]
df = df.sort_values(["date", "heure"])

df.to_csv("data/openData/affluence_grand_plage_h_par_h.csv", index=False)
