import argparse
from datetime import date

import pandas as pd

from kiblib.utils.db import DbConn
from kiblib.utils.frequentation import calculer_occupation

# Reconstitue le jeu "affluence horaire" publié sur data.lillemetropole.fr
# (ville_roubaix:affluence_et_activites_de_la_grand_plage_h_par_h_depuis_2014),
# arrêté au 2020-12-31, enrichi de colonnes absentes du jeu d'origine
# (connexions_wifi, impressions, frequentation_etude, entrees, occupation).
# Prêts/retours viennent de statdb.stat_issues (branche MED = Grand Plage),
# connexions postes de statdb.stat_webkiosk (à la demande - ni cette table ni
# stat_sessions_webkiosk ne sont alimentées en continu actuellement, voir
# README, section "Jeu open data affluence horaire"), wifi de
# statdb.stat_wifi, impressions (nombre de pages) de statdb.stat_impressions,
# fréquentation salle d'étude de statdb.stat_freq_etude, entrées/occupation
# de statdb.stat_entrees/stat_entrees_det. Voir README pour le détail de
# chaque colonne, les règles métier appliquées (lundi, amplitude
# d'ouverture) et les anomalies identifiées et corrigées.


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
    parser.add_argument(
        "--granularite", type=int, default=60, metavar="MINUTES",
        help="Pas de temps des créneaux, en minutes (défaut : 60). Doit "
             "diviser 60 exactement (30, 20, 15, 12, 10, 6, 5...).")
    args = parser.parse_args()
    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    if not (1 <= args.granularite <= 60) or 60 % args.granularite != 0:
        parser.error(
            f"--granularite {args.granularite} invalide : doit être un "
            "diviseur de 60 entre 1 et 60 (30, 20, 15, 12, 10, 6, 5...), "
            "pour que les créneaux restent alignés sur l'heure."
        )
    if args.granularite != 60 and start_date < date(2021, 1, 1):
        parser.error(
            f"--granularite {args.granularite} n'est fiable qu'à partir de "
            "2021-01-01 : le jeu publié à l'origine (2014-2020) n'a que des "
            "heures pleines, et statdb.stat_issues n'a pas d'historique "
            "fiable avant ~2019 - voir README."
        )
    return start_date, end_date, args.granularite


DATE_DEBUT, DATE_FIN, PAS = parse_args()
DIVISIONS_PAR_HEURE = 60 // PAS
NOM_FICHIER = (
    "affluence_grand_plage_h_par_h.csv" if PAS == 60
    else f"affluence_grand_plage_{PAS}_min.csv")


def expr_heure(colonne):
    """Expression SQL du créneau (index entier, 0 à 24*DIVISIONS_PAR_HEURE-1) -
    HOUR() seul quand PAS == 60, sinon HOUR()*DIVISIONS_PAR_HEURE + la
    subdivision de l'heure correspondant au pas choisi."""
    if PAS == 60:
        return f"HOUR({colonne})"
    return f"(HOUR({colonne}) * {DIVISIONS_PAR_HEURE} + FLOOR(MINUTE({colonne}) / {PAS}))"


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
    f"""
    SELECT DATE(issuedate) AS date, {expr_heure('issuedate')} AS heure, COUNT(*) AS prets
    FROM statdb.stat_issues
    WHERE branch = 'MED' AND issuedate >= %(debut)s AND issuedate < %(fin)s
      AND HOUR(issuedate) BETWEEN 9 AND 19
      AND DAYOFWEEK(issuedate) != 2
    GROUP BY DATE(issuedate), {expr_heure('issuedate')}
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

# Exclusion ponctuelle du 2026-03-30 18h-19h : 1740 puis 1992 retours, un
# lundi soir (fermé au public), sans aucune activité corrélée sur les 6
# autres métriques ce créneau-là - 3,6x le record de tout autre lundi
# jamais enregistré. Cas isolé (le seul sur 127 valeurs extrêmes de retours
# à n'avoir aucune activité corrélée) - traité au cas par cas plutôt que par
# une règle générale comme pour les prêts groupés (voir plus haut), faute de
# récurrence constatée à ce jour.
retours = pd.read_sql(
    f"""
    SELECT DATE(returndate) AS date, {expr_heure('returndate')} AS heure, COUNT(*) AS retours
    FROM statdb.stat_issues
    WHERE branch = 'MED' AND returndate >= %(debut)s AND returndate < %(fin)s
      AND NOT (DATE(returndate) = '2026-03-30' AND HOUR(returndate) IN (18, 19))
    GROUP BY DATE(returndate), {expr_heure('returndate')}
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

connexions = pd.read_sql(
    f"""
    SELECT DATE(heure_deb) AS date, {expr_heure('heure_deb')} AS heure, COUNT(*) AS connexions_postes
    FROM statdb.stat_webkiosk
    WHERE heure_deb >= %(debut)s AND heure_deb < %(fin)s
      AND DAYOFWEEK(heure_deb) != 2
    GROUP BY DATE(heure_deb), {expr_heure('heure_deb')}
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

# Même filtre du lundi que pour connexions_postes : la médiathèque étant
# fermée au public, une connexion wifi ce jour-là est un test.
connexions_wifi = pd.read_sql(
    f"""
    SELECT DATE(start_wifi) AS date, {expr_heure('start_wifi')} AS heure, COUNT(*) AS connexions_wifi
    FROM statdb.stat_wifi
    WHERE start_wifi >= %(debut)s AND start_wifi < %(fin)s
      AND DAYOFWEEK(start_wifi) != 2
    GROUP BY DATE(start_wifi), {expr_heure('start_wifi')}
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

# impressions = nombre de pages imprimées (volume, pas un comptage de
# travaux d'impression) - même filtre du lundi que les autres colonnes.
# HAVING > 0 : contrairement à COUNT(*) (toujours >= 1 par construction du
# GROUP BY), SUM() peut ressortir à 0 (travail d'impression à 0 page) et
# introduire une ligne fantôme dans la jointure externe si rien d'autre n'a
# d'activité ce créneau-là.
impressions = pd.read_sql(
    f"""
    SELECT DATE(date_impression) AS date, {expr_heure('date_impression')} AS heure,
        SUM(nb_pages_imprimees) AS impressions
    FROM statdb.stat_impressions
    WHERE date_impression >= %(debut)s AND date_impression < %(fin)s
      AND DAYOFWEEK(date_impression) != 2
    GROUP BY DATE(date_impression), {expr_heure('date_impression')}
    HAVING SUM(nb_pages_imprimees) > 0
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

# frequentation_etude = nombre d'entrées en salle d'étude (badgeage direct,
# webapp/services.py::is_entrance() - pas un import CSV différé comme
# webkiosk/wifi/impressions). Même filtre du lundi que les autres colonnes.
frequentation_etude = pd.read_sql(
    f"""
    SELECT DATE(datetime_entree) AS date, {expr_heure('datetime_entree')} AS heure,
        COUNT(*) AS frequentation_etude
    FROM statdb.stat_freq_etude
    WHERE datetime_entree >= %(debut)s AND datetime_entree < %(fin)s
      AND DAYOFWEEK(datetime_entree) != 2
    GROUP BY DATE(datetime_entree), {expr_heure('datetime_entree')}
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})

# statdb.stat_entrees_det a ses propres colonnes entières heure/minute
# (posées à l'insertion par data_entrees_opteio.py), pas un datetime à passer
# à HOUR()/MINUTE() - expression du créneau dédiée.
def expr_heure_det():
    if PAS == 60:
        return "heure"
    return f"(heure * {DIVISIONS_PAR_HEURE} + FLOOR(minute / {PAS}))"


# occupation = nb de personnes présentes dans l'établissement, dérivé du
# détail brut par capteur/minute (statdb.stat_entrees_det). Calcul et
# correction (l'occupation brute ne revient pas exactement à 0 en fin de
# journée à cause de biais de comptage du capteur) dans
# kiblib.utils.frequentation, réutilisable ailleurs (notebook, autre
# script). Même filtre du lundi que les autres colonnes.
entrees_det = pd.read_sql(
    f"""
    SELECT jour AS date, {expr_heure_det()} AS heure,
        SUM(entree) AS entree, SUM(sortie) AS sortie
    FROM statdb.stat_entrees_det
    WHERE datetime >= %(debut)s AND datetime < %(fin)s
      AND DAYOFWEEK(datetime) != 2
    GROUP BY jour, {expr_heure_det()}
    """,
    con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})
occupation = calculer_occupation(entrees_det)

# entrees = comptage de passages physiques (capteur Opteio). En granularité
# heure, vient de statdb.stat_entrees (déjà agrégée à l'heure par
# data_entrees_opteio.py) - source validée, laissée telle quelle. En
# granularité plus fine (demi-heure, quart-heure...), stat_entrees n'a pas
# la précision infra-horaire nécessaire (toujours à la minute 00) : dérivée
# de statdb.stat_entrees_det (déjà interrogée ci-dessus pour occupation) à
# la place.
# HAVING/filtre > 0 dans les deux cas : l'API Opteio distingue parfois
# entrées et sorties sur deux lignes séparées (cf. data_entrees_opteio.py) -
# un événement "sortie seule" donne entree=0, qui introduirait sinon une
# ligne fantôme dans la jointure externe (cause confirmée de 38 lignes
# entièrement à zéro sur un premier essai).
if PAS == 60:
    entrees = pd.read_sql(
        """
        SELECT DATE(datetime) AS date, HOUR(datetime) AS heure, SUM(entrees) AS entrees
        FROM statdb.stat_entrees
        WHERE datetime >= %(debut)s AND datetime < %(fin)s
          AND DAYOFWEEK(datetime) != 2
        GROUP BY DATE(datetime), HOUR(datetime)
        HAVING SUM(entrees) > 0
        """,
        con=engine, params={"debut": DATE_DEBUT, "fin": DATE_FIN})
else:
    entrees = (
        entrees_det[entrees_det["entree"] > 0][["date", "heure", "entree"]]
        .rename(columns={"entree": "entrees"})
        .copy())

df = prets.merge(retours, on=["date", "heure"], how="outer")
df = df.merge(connexions, on=["date", "heure"], how="outer")
df = df.merge(connexions_wifi, on=["date", "heure"], how="outer")
df = df.merge(impressions, on=["date", "heure"], how="outer")
df = df.merge(frequentation_etude, on=["date", "heure"], how="outer")
df = df.merge(entrees, on=["date", "heure"], how="outer")

# Contrairement au jeu publié jusqu'ici (cf. README), les créneaux sans
# activité sont mis à 0 explicitement plutôt que laissés vides - ambiguïté
# NaN documentée comme point à corriger.
for c in ["prets", "retours", "connexions_postes", "connexions_wifi", "impressions", "frequentation_etude", "entrees"]:
    df[c] = df[c].fillna(0).astype(int)

# Filet de sécurité (en plus des HAVING > 0 ci-dessus) : une ligne
# entièrement à zéro sur les 7 métriques ne devrait jamais exister.
masque_tout_zero = (df[["prets", "retours", "connexions_postes", "connexions_wifi", "impressions", "frequentation_etude", "entrees"]] == 0).all(axis=1)
df = df[~masque_tout_zero]

# occupation en jointure gauche, après le filtre "tout zéro" ci-dessus :
# contrairement aux autres métriques, 0 y est une valeur légitime (bâtiment
# vide à l'ouverture/fermeture), elle ne doit donc pas participer à ce
# filtre ni créer de nouvelles lignes par elle-même.
df = df.merge(occupation, on=["date", "heure"], how="left")
df["occupation"] = df["occupation"].fillna(0).astype(int)

df["date"] = pd.to_datetime(df["date"])
df["annee"] = df["date"].dt.year
df["jour"] = df["date"].dt.day
df["mois"] = df["date"].dt.month
df["heure"] = df["heure"].apply(
    lambda h: f"{h // DIVISIONS_PAR_HEURE:02d}:{(h % DIVISIONS_PAR_HEURE) * PAS:02d}:00")
fichier_sortie = f"data/openData/{NOM_FICHIER}"
df["date"] = df["date"].dt.strftime("%Y-%m-%d")

df = df[[
    "date", "annee", "jour", "mois", "heure",
    "retours", "prets", "connexions_postes", "connexions_wifi", "impressions",
    "frequentation_etude", "entrees", "occupation"]]
df = df.sort_values(["date", "heure"])

df.to_csv(fichier_sortie, index=False)
