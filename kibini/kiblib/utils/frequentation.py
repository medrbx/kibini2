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

calculer_occupation_sessions() fait l'équivalent pour des sessions avec un
début et une fin (ex. statdb.stat_webkiosk, ordinateurs publics) : nombre
moyen de sessions simultanées par créneau.

Utilisé par stat_opendata_affluence.py ; réutilisable
tel quel dans un notebook ou tout autre script partant d'un DataFrame au même
format (colonnes date/heure/entree/sortie, une ligne par jour et créneau
horaire, déjà sommées si plusieurs capteurs).
"""

import numpy as np
import pandas as pd


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


def calculer_occupation_sessions(sessions, pas=60, duree_max=None):
    """
    Nombre moyen de sessions simultanées par créneau (ex. ordinateurs occupés),
    à partir de sessions avec un début et une fin.

    sessions : DataFrame avec les colonnes 'debut' et 'fin' (datetime). Les
    sessions sans fin ou finissant avant leur début sont ignorées, une session
    qui se prolonge au-delà de minuit est coupée à minuit (fins aberrantes
    constatées sur 2014-2015 dans statdb.stat_webkiosk).
    pas : durée du créneau en minutes (diviseur de 60).
    duree_max : durée maximale plausible d'une session, en minutes - les
    sessions plus longues sont ignorées (fin manifestement fausse), aucune
    limite si None.

    Renvoie un DataFrame 'date' (datetime64, jour), 'heure' (index du créneau
    dans la journée, 0 à 24*60/pas - 1), 'occupation' : minutes de session
    tombant dans le créneau divisées par la durée du créneau - ex. 105 minutes
    cumulées entre 14h et 15h donnent 1,75 ordinateur occupé en moyenne.
    """
    colonnes = ["date", "heure", "occupation"]
    s = sessions.dropna(subset=["debut", "fin"])
    s = s[s["fin"] > s["debut"]]
    if duree_max is not None:
        s = s[s["fin"] - s["debut"] <= pd.Timedelta(minutes=duree_max)]
    if s.empty:
        return pd.DataFrame(columns=colonnes)
    jour = s["debut"].dt.normalize()
    debut = (s["debut"] - jour).dt.total_seconds() / 60
    fin = ((s["fin"] - jour).dt.total_seconds() / 60).clip(upper=24 * 60)
    s = pd.DataFrame({"date": jour, "debut": debut, "fin": fin})
    # une ligne par créneau couvert par chaque session, puis minutes de
    # recouvrement entre la session et le créneau
    s["heure"] = [
        np.arange(int(d // pas), int(np.ceil(f / pas)))
        for d, f in zip(s["debut"], s["fin"])]
    s = s.explode("heure")
    s["heure"] = s["heure"].astype(int)
    s["minutes"] = (
        np.minimum(s["fin"], (s["heure"] + 1) * pas)
        - np.maximum(s["debut"], s["heure"] * pas))
    occupation = s.groupby(["date", "heure"], as_index=False)["minutes"].sum()
    occupation["occupation"] = (occupation["minutes"] / pas).round(1)
    return occupation[colonnes]
