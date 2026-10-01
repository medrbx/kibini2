import argparse
from datetime import date

import pandas as pd

from kiblib.utils.db import DbConn
from kiblib.utils.frequentation import calculer_occupation

# Jeu open data "affluence horaire" publié sur data.lillemetropole.fr
# (ville_roubaix:affluence_et_activites_de_la_grand_plage_h_par_h_depuis_2014),
# arrêté au 2020-12-31 à l'origine, enrichi de colonnes absentes du jeu
# d'origine (connexions_wifi, impressions, frequentation_etude, entrees,
# occupation). Remplace stat_affluence2oa.py + stat_affluence_concat.py.
# À lancer depuis la racine du dépôt (chemins relatifs "data/...").
#
#   python kibini/stat_opendata_affluence.py
#   python kibini/stat_opendata_affluence.py --start-date 2021-01-01 --end-date 2026-01-01
#   python kibini/stat_opendata_affluence.py --granularite 30
#
# Deux étapes enchaînées :
#   1. extraction fraîche depuis statdb (2021-01-01 -> --end-date exclue) ->
#      data/openData/affluence_grand_plage_h_par_h.csv
#      (ou affluence_grand_plage_<pas>_min.csv si --granularite != 60)
#   2. concaténation avec le jeu déjà publié 2014-2020, corrigé et complété ->
#      data/openData/affluence_grand_plage_h_par_h_complet.csv
#      (seulement si --granularite 60 et --start-date 2021-01-01)
#
# Prêts/retours viennent de statdb.stat_issues (branche MED = Grand Plage),
# connexions postes de statdb.stat_webkiosk (à la demande - ni cette table ni
# stat_sessions_webkiosk ne sont alimentées en continu actuellement, voir
# README, section "Jeu open data affluence horaire"), wifi de
# statdb.stat_wifi, impressions (nombre de pages) de statdb.stat_impressions,
# fréquentation salle d'étude de statdb.stat_freq_etude, entrées/occupation
# de statdb.stat_entrees/stat_entrees_det. Voir README pour le détail de
# chaque colonne, les règles métier appliquées (lundi, amplitude
# d'ouverture) et les anomalies identifiées et corrigées.

DEBUT_EXTRACTION = date(2021, 1, 1)
DIR_OPENDATA = "data/openData"
FICHIER_DATA_MEL = "data/openData/data/affluence_data_mel_2014-2020_brut.csv"
FICHIER_COMPLET = f"{DIR_OPENDATA}/affluence_grand_plage_h_par_h_complet.csv"

COLONNES = [
    "date", "annee", "jour", "mois", "heure",
    "retours", "prets", "connexions_postes", "connexions_wifi", "impressions",
    "frequentation_etude", "entrees", "occupation"]

METRIQUES = [
    "prets", "retours", "connexions_postes", "connexions_wifi", "impressions",
    "frequentation_etude", "entrees"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Produit le jeu 'affluence horaire' (extraction 2021+ puis concaténation avec 2014-2020)."
    )
    parser.add_argument(
        "--start-date", default=DEBUT_EXTRACTION.isoformat(),
        help="Début de la plage à extraire (YYYY-MM-DD), inclus (défaut : 2021-01-01). "
             "La concaténation avec 2014-2020 n'a lieu que pour 2021-01-01.")
    parser.add_argument(
        "--end-date", default=date.today().isoformat(),
        help="Fin de la plage à extraire (YYYY-MM-DD), exclue (défaut : aujourd'hui, "
             "donc jusqu'à hier inclus).")
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
    if args.granularite != 60 and start_date < DEBUT_EXTRACTION:
        parser.error(
            f"--granularite {args.granularite} n'est fiable qu'à partir de "
            "2021-01-01 : le jeu publié à l'origine (2014-2020) n'a que des "
            "heures pleines, et statdb.stat_issues n'a pas d'historique "
            "fiable avant ~2019 - voir README."
        )
    return start_date, end_date, args.granularite


def extraire(engine, debut, fin, pas):
    """Extraction fraîche depuis statdb, sur [debut, fin[, au pas donné (minutes)."""
    divisions_par_heure = 60 // pas
    params = {"debut": debut, "fin": fin}

    def expr_heure(colonne):
        """Expression SQL du créneau (index entier, 0 à 24*divisions_par_heure-1) -
        HOUR() seul quand pas == 60, sinon HOUR()*divisions_par_heure + la
        subdivision de l'heure correspondant au pas choisi."""
        if pas == 60:
            return f"HOUR({colonne})"
        return f"(HOUR({colonne}) * {divisions_par_heure} + FLOOR(MINUTE({colonne}) / {pas}))"

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
        con=engine, params=params)

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
        con=engine, params=params)

    connexions = pd.read_sql(
        f"""
        SELECT DATE(heure_deb) AS date, {expr_heure('heure_deb')} AS heure, COUNT(*) AS connexions_postes
        FROM statdb.stat_webkiosk
        WHERE heure_deb >= %(debut)s AND heure_deb < %(fin)s
          AND DAYOFWEEK(heure_deb) != 2
        GROUP BY DATE(heure_deb), {expr_heure('heure_deb')}
        """,
        con=engine, params=params)

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
        con=engine, params=params)

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
        con=engine, params=params)

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
        con=engine, params=params)

    # statdb.stat_entrees_det a ses propres colonnes entières heure/minute
    # (posées à l'insertion par data_entrees_opteio.py), pas un datetime à passer
    # à HOUR()/MINUTE() - expression du créneau dédiée.
    if pas == 60:
        expr_heure_det = "heure"
    else:
        expr_heure_det = f"(heure * {divisions_par_heure} + FLOOR(minute / {pas}))"

    # occupation = nb de personnes présentes dans l'établissement, dérivé du
    # détail brut par capteur/minute (statdb.stat_entrees_det). Calcul et
    # correction (l'occupation brute ne revient pas exactement à 0 en fin de
    # journée à cause de biais de comptage du capteur) dans
    # kiblib.utils.frequentation, réutilisable ailleurs (notebook, autre
    # script). Même filtre du lundi que les autres colonnes.
    entrees_det = pd.read_sql(
        f"""
        SELECT jour AS date, {expr_heure_det} AS heure,
            SUM(entree) AS entree, SUM(sortie) AS sortie
        FROM statdb.stat_entrees_det
        WHERE datetime >= %(debut)s AND datetime < %(fin)s
          AND DAYOFWEEK(datetime) != 2
        GROUP BY jour, {expr_heure_det}
        """,
        con=engine, params=params)
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
    if pas == 60:
        entrees = pd.read_sql(
            """
            SELECT DATE(datetime) AS date, HOUR(datetime) AS heure, SUM(entrees) AS entrees
            FROM statdb.stat_entrees
            WHERE datetime >= %(debut)s AND datetime < %(fin)s
              AND DAYOFWEEK(datetime) != 2
            GROUP BY DATE(datetime), HOUR(datetime)
            HAVING SUM(entrees) > 0
            """,
            con=engine, params=params)
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
    for c in METRIQUES:
        df[c] = df[c].fillna(0).astype(int)

    # Filet de sécurité (en plus des HAVING > 0 ci-dessus) : une ligne
    # entièrement à zéro sur les 7 métriques ne devrait jamais exister.
    masque_tout_zero = (df[METRIQUES] == 0).all(axis=1)
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
        lambda h: f"{h // divisions_par_heure:02d}:{(h % divisions_par_heure) * pas:02d}:00")
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    df = df[COLONNES]
    return df.sort_values(["date", "heure"])


def reconstruire_2014_2020(engine):
    """Jeu publié à l'origine (2014-07-01 -> 2020-12-31), corrigé et complété.

    Pas de reconstruction complète : statdb.stat_issues n'a de toute façon pas
    l'historique avant ~2019 (voir README). Export tel que publié à
    l'origine (affluence_data_mel_2014-2020_brut.csv), à un correctif près
    confirmé par comparaison mois par mois avec une extraction fraîche de
    statdb : les colonnes prets/connexions_postes sont interverties sur toute
    l'année 2020 dans le fichier publié (concordance quasi parfaite une fois
    remises dans le bon sens) - corrigé ici, aucune autre valeur modifiée.
    Colonnes connexions_wifi, impressions, frequentation_etude et entrees
    absentes du jeu publié à l'origine (jamais suivies à l'époque) :
    reconstruites ici depuis statdb.stat_wifi (profondeur historique dès 2016,
    2014-2015 sortent à 0), statdb.stat_impressions (profondeur dès 2015, 2014
    sort à 0) et statdb.stat_freq_etude (profondeur dès 2016, 2014-2015
    sortent à 0) - le service n'existait probablement pas encore ces
    années-là, à confirmer si besoin - et statdb.stat_entrees (profondeur dès
    2009, aucune lacune sur 2014-2020). occupation reconstruite depuis
    statdb.stat_entrees_det (aussi profondeur dès 2009, aucune lacune) -
    calcul et correction dans kiblib.utils.frequentation (cumul
    entrées-sorties, écart de fermeture réparti linéairement dans le temps).
    """
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

    # Mêmes règles que extraire(), appliquées ici a posteriori sur le fichier
    # publié d'origine pour rester cohérent sur toute la période : lundi
    # (médiathèque fermée au public, seuls les retours sont possibles) et
    # amplitude d'ouverture 9h-19h pour les prêts (lots groupés hors ouverture,
    # voir README) - on annule les valeurs concernées plutôt que de reconstruire.
    lundi = data_mel["date"].dt.dayofweek == 0
    data_mel.loc[lundi, ["prets", "connexions_postes"]] = 0
    hors_ouverture = ~data_mel["heure_int"].between(9, 19)
    data_mel.loc[hors_ouverture, "prets"] = 0

    # Même filtre du lundi que dans extraire() (médiathèque fermée au public,
    # toute connexion ce jour-là est un test).
    params = {
        "debut": data_mel["date"].min(),
        "fin": data_mel["date"].max() + pd.Timedelta(days=1)}

    connexions_wifi = pd.read_sql(
        """
        SELECT DATE(start_wifi) AS date, HOUR(start_wifi) AS heure, COUNT(*) AS connexions_wifi
        FROM statdb.stat_wifi
        WHERE start_wifi >= %(debut)s AND start_wifi < %(fin)s
          AND DAYOFWEEK(start_wifi) != 2
        GROUP BY DATE(start_wifi), HOUR(start_wifi)
        """,
        con=engine, params=params)
    connexions_wifi["date"] = pd.to_datetime(connexions_wifi["date"])

    # HAVING > 0 sur les 2 requêtes SUM() ci-dessous : contrairement à COUNT(*),
    # une somme peut ressortir à 0 (travail d'impression à 0 page, événement
    # "sortie seule" Opteio - voir extraire()) - déjà sans conséquence ici
    # grâce au filtre "tout zéro" plus bas, mais gardé par cohérence.
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
        con=engine, params=params)
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
        con=engine, params=params)
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
        con=engine, params=params)
    entrees["date"] = pd.to_datetime(entrees["date"])

    entrees_det = pd.read_sql(
        """
        SELECT jour AS date, heure, SUM(entree) AS entree, SUM(sortie) AS sortie
        FROM statdb.stat_entrees_det
        WHERE datetime >= %(debut)s AND datetime < %(fin)s
          AND DAYOFWEEK(datetime) != 2
        GROUP BY jour, heure
        """,
        con=engine, params=params)
    entrees_det["date"] = pd.to_datetime(entrees_det["date"])

    occupation = calculer_occupation(entrees_det)

    # heure_int (calculé plus haut) sert de clé de jointure - data_mel a 'heure'
    # au format 'HH:00:00' (texte), les extractions ci-dessus au format entier
    # (issu de HOUR() en SQL). Jointures externes (outer) : un créneau où seul
    # le wifi, l'impression ou l'entrée a été utilisé n'existe pas dans le
    # fichier data MEL d'origine (colonnes jamais suivies à l'époque), il ne
    # faut pas le perdre.
    for extraction in (connexions_wifi, impressions, frequentation_etude, entrees):
        data_mel = data_mel.merge(
            extraction.rename(columns={"heure": "heure_int"}),
            on=["date", "heure_int"], how="outer")

    for c in METRIQUES:
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
    masque_tout_zero = (data_mel[METRIQUES] == 0).all(axis=1)
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
    return data_mel[COLONNES]


if __name__ == "__main__":
    start_date, end_date, pas = parse_args()
    engine = DbConn().create_engine()

    nouveau = extraire(engine, start_date, end_date, pas)
    nom_fichier = (
        "affluence_grand_plage_h_par_h.csv" if pas == 60
        else f"affluence_grand_plage_{pas}_min.csv")
    fichier_nouveau = f"{DIR_OPENDATA}/{nom_fichier}"
    nouveau.to_csv(fichier_nouveau, index=False)
    print(f"[1/2] extraction : {len(nouveau)} lignes ({start_date} -> {end_date} exclue) -> {fichier_nouveau}")

    if pas != 60 or start_date != DEBUT_EXTRACTION:
        print("[2/2] concaténation ignorée : requiert --granularite 60 et --start-date 2021-01-01.")
    else:
        # 2014-2020 + extraction fraîche (2021-01-01 -> aujourd'hui)
        data_mel = reconstruire_2014_2020(engine)
        final = pd.concat(
            [data_mel, nouveau[nouveau["date"] >= DEBUT_EXTRACTION.isoformat()][COLONNES]],
            ignore_index=True)
        final = final.sort_values(["date", "heure"])
        final.to_csv(FICHIER_COMPLET, index=False)
        print(f"[2/2] concaténation : {len(final)} lignes -> {FICHIER_COMPLET}")
