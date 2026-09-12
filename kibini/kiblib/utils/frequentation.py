"""
Occupation d'un établissement (nb de personnes présentes) à partir d'un
détail entrées/sorties par capteur (ex. statdb.stat_entrees_det, alimentée
par data_entrees_opteio.py).

En théorie, le cumul entrées - sorties d'une journée revient à 0 à la
fermeture (personne ne reste dans un bâtiment fermé). En pratique, de légers
biais de comptage du capteur (deux personnes détectées comme une seule,
rebond compté deux fois, sens mal détecté...) s'accumulent au fil de la
journée et empêchent ce retour exact à 0. calculer_occupation() corrige cet
écart en le répartissant linéairement dans le temps sur la journée, puis
plafonne le résultat à 0 (l'occupation ne peut pas être négative).

Utilisé par stat_affluence2oa.py et stat_affluence_concat.py ; réutilisable
tel quel dans un notebook ou tout autre script partant d'un DataFrame au même
format (colonnes date/heure/entree/sortie, une ligne par jour et créneau
horaire, déjà sommées si plusieurs capteurs).
"""


def corriger_occupation_jour(groupe):
    """Corrige l'occupation d'une seule journée (groupe trié par heure)."""
    groupe = groupe.sort_values("heure").copy()
    brut = groupe["entree"].cumsum() - groupe["sortie"].cumsum()
    h_min, h_max = groupe["heure"].min(), groupe["heure"].max()
    residu = brut.iloc[-1]
    if h_max > h_min:
        correction = residu * (groupe["heure"] - h_min) / (h_max - h_min)
    else:
        correction = 0
    groupe["occupation"] = (brut - correction).round().clip(lower=0).astype(int)
    return groupe[["date", "heure", "occupation"]]


def calculer_occupation(entrees_det):
    """
    entrees_det : DataFrame avec les colonnes 'date', 'heure', 'entree',
    'sortie' - une ligne par jour et par créneau horaire (déjà sommées tous
    capteurs confondus si plusieurs capteurs).

    Renvoie un DataFrame 'date', 'heure', 'occupation'.
    """
    if entrees_det.empty:
        return entrees_det.assign(occupation=[])[["date", "heure", "occupation"]]
    return entrees_det.groupby("date", group_keys=False).apply(corriger_occupation_jour)
