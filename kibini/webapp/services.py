"""
Logique métier du site web Kibini, portée depuis kibini_prod/lib
(adherents.pm, collections/suggestions.pm, salleEtude/form.pm,
action_culturelle.pm, action_coop/form.pm, liste.pm).
"""
from datetime import datetime

import requests
from sqlalchemy import text

from kiblib.utils.conf import Config
from kiblib.utils.db import DbConn
from kiblib.utils.email_sender import send_email as _send_email

# Hôte du back-office Koha (staff), déjà utilisé en dur dans tous les templates
# .tt d'origine pour les liens vers les notices/adhérents/suggestions.
KOHA_STAFF_URL = "https://koha.ville-roubaix.fr"


def _engine():
    return DbConn().create_engine()


def _webservice_get(path, params=None):
    base = Config().get_config_webservice()["base"]
    resp = requests.get(f"{base}{path}", params=params)
    resp.raise_for_status()
    data = resp.json()
    # svc/report renvoie du NULL SQL tel quel (None) ; sans ça, Jinja affiche
    # la chaîne "None" dans les tableaux HTML des listes.
    return [["" if v is None else v for v in row] for row in data]


# --------------------------------------------------------------------------
# adherents.pm : GetBorrowersForQA
# --------------------------------------------------------------------------

def get_borrowers_for_qa():
    borrowers = _webservice_get("/cgi-bin/koha/svc/report?id=166")
    return [b for b in borrowers if any(b[i] == "PB" for i in range(3, 11))]


# --------------------------------------------------------------------------
# collections/suggestions.pm : suggestions3, acquereurs, modSuggestion2,
# constructionCourriel
# --------------------------------------------------------------------------

_SUGGESTION_FIELDS = [
    "suggestionid", "title", "date", "author", "publishercode",
    "collectiontitle", "copyrightdate", "isbn", "suggestedby", "managedby",
    "note", "branchcode", "firstnamemanagedby", "firstnamesuggestedby",
    "surnamesuggestedby",
]


def suggestions3():
    rows = _webservice_get("/cgi-bin/koha/svc/report?id=309")
    return [dict(zip(_SUGGESTION_FIELDS, row)) for row in rows]


def acquereurs():
    return {a["borrowernumber"]: a["nom"] for a in Config().get_config_acquereurs()}


def _acquereur_mail(managedby):
    for a in Config().get_config_acquereurs():
        if a["borrowernumber"] == int(managedby):
            return f"{a['courriel']}@ville-roubaix.fr"
    return None


def mod_suggestion2(suggestionid, managedby):
    conf = Config().get_config_webservice()
    url = f"{KOHA_STAFF_URL}/api/v1/suggestions/{suggestionid}"
    requests.put(
        url,
        json={"managed_by": int(managedby)},
        auth=(conf["user"], conf["pwd"]),
    )


def construction_courriel(managedby, title):
    email = _acquereur_mail(managedby)
    from_ = "Koha suggestions<mediatheque@ville-roubaix.fr>"
    subject = f"Nouvelle suggestion : {title}"
    msg = (
        f"Nouvelle suggestion : {title}\n\n"
        f"Voir {KOHA_STAFF_URL}/cgi-bin/koha/suggestion/suggestion.pl#ASKED"
    )
    return from_, email, subject, msg


def send_email(from_, to, subject, msg):
    _send_email(from_, to, subject, msg)


# --------------------------------------------------------------------------
# salleEtude/form.pm : IsEntrance, GetTodayEntrance, GetPastEntrances
# --------------------------------------------------------------------------

def get_today_entrance():
    with _engine().begin() as conn:
        rows = conn.execute(text("""
            SELECT cardnumber, TIME(datetime_entree) AS entree, TIME(datetime_sortie) AS sortie, duree
            FROM statdb.stat_freq_etude
            WHERE DATE(datetime_entree) = CURDATE()
            ORDER BY datetime_entree DESC
        """)).mappings().all()
    return [dict(r) for r in rows]


def get_past_entrances():
    with _engine().begin() as conn:
        rows = conn.execute(text("""
            SELECT
                DATE(datetime_entree) AS date,
                COUNT(cardnumber) AS nb_entrees,
                COUNT(DISTINCT cardnumber) AS nb_utilisateurs
            FROM statdb.stat_freq_etude
            GROUP BY DATE(datetime_entree)
            ORDER BY DATE(datetime_entree) DESC
            LIMIT 10
        """)).mappings().all()
    return [dict(r) for r in rows]


def is_entrance(cardnumber):
    """Bascule entrée/sortie pour une carte donnée. Renvoie 1 (entrée) ou 0 (sortie)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _engine().begin() as conn:
        last_id = conn.execute(text("""
            SELECT MAX(id) FROM statdb.stat_freq_etude
            WHERE DATE(datetime_entree) = CURDATE() AND cardnumber = :cardnumber
        """), {"cardnumber": cardnumber}).scalar()

        if last_id:
            datetime_sortie = conn.execute(text(
                "SELECT datetime_sortie FROM statdb.stat_freq_etude WHERE id = :id"
            ), {"id": last_id}).scalar()

            if datetime_sortie:
                # déjà entrée et sortie aujourd'hui : on recrée une entrée
                conn.execute(text(
                    "INSERT INTO statdb.stat_freq_etude (cardnumber, datetime_entree) "
                    "VALUES (:cardnumber, :datetime_entree)"
                ), {"cardnumber": cardnumber, "datetime_entree": now})
                return 1
            else:
                # entrée non close : on enregistre la sortie
                datetime_entree = conn.execute(text(
                    "SELECT datetime_entree FROM statdb.stat_freq_etude WHERE id = :id"
                ), {"id": last_id}).scalar()
                duree = _duree_hhmmss(datetime_entree, now)
                conn.execute(text(
                    "UPDATE statdb.stat_freq_etude SET datetime_sortie = :sortie, duree = :duree WHERE id = :id"
                ), {"sortie": now, "duree": duree, "id": last_id})
                return 0
        else:
            conn.execute(text(
                "INSERT INTO statdb.stat_freq_etude (cardnumber, datetime_entree) "
                "VALUES (:cardnumber, :datetime_entree)"
            ), {"cardnumber": cardnumber, "datetime_entree": now})
            return 1


def _duree_hhmmss(datetime_entree, datetime_sortie):
    fmt = "%Y-%m-%d %H:%M:%S"
    delta = datetime.strptime(datetime_sortie, fmt) - datetime.strptime(str(datetime_entree), fmt)
    total_seconds = int(delta.total_seconds())
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# --------------------------------------------------------------------------
# action_culturelle.pm
# --------------------------------------------------------------------------

def list_actions_culturelle():
    with _engine().begin() as conn:
        rows = conn.execute(text("""
            SELECT id, date, action, lieu, type, public, partenariat, participants
            FROM statdb.stat_action_culturelle
            ORDER BY id DESC
        """)).mappings().all()
    return [dict(r) for r in rows]


def insert_action_culturelle(date, action, lieu, type_, public, partenariat, participants):
    with _engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO statdb.stat_action_culturelle
                (date, action, lieu, type, public, partenariat, participants)
            VALUES (:date, :action, :lieu, :type, :public, :partenariat, :participants)
        """), {
            "date": date, "action": action, "lieu": lieu, "type": type_,
            "public": public, "partenariat": partenariat, "participants": participants,
        })


# --------------------------------------------------------------------------
# action_coop/form.pm
# --------------------------------------------------------------------------

def get_list_actions_cooperation():
    with _engine().begin() as conn:
        rows = conn.execute(text(
            "SELECT * FROM statdb.stat_action_coop ORDER BY id DESC"
        )).mappings().all()
    return [dict(r) for r in rows]


def add_action_cooperation(date, lieu, type_action, nom, type_structure, nom_structure, participants, referent_action):
    with _engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO statdb.stat_action_coop
                (date, lieu, type, nom, type_structure, nom_structure, participants, referent_action)
            VALUES (:date, :lieu, :type, :nom, :type_structure, :nom_structure, :participants, :referent_action)
        """), {
            "date": date, "lieu": lieu, "type": type_action, "nom": nom,
            "type_structure": type_structure, "nom_structure": nom_structure,
            "participants": participants, "referent_action": referent_action,
        })


# --------------------------------------------------------------------------
# liste.pm : GetListData
# --------------------------------------------------------------------------

_LISTE_TITRES = {
    "d0azz": "Réservations sur documents disponibles, public, RDC",
    "d0pzz": "Réservations sur documents disponibles, personnel, RDC",
    "d1azz": "Réservations sur documents disponibles, public, 1er étage",
    "d1pzz": "Réservations sur documents disponibles, personnel, 1er étage",
    "d2azz": "Réservations sur documents disponibles, public, 2e étage",
    "d2pzz": "Réservations sur documents disponibles, personnel, 2e étage",
    "d3azz": "Réservations sur documents disponibles, public, 3e étage",
    "d3pzz": "Réservations sur documents disponibles, personnel, 3e étage",
    "d4azz": "Réservations sur documents disponibles, public, Zèbre",
    "d4pzz": "Réservations sur documents disponibles, personnel, Zèbre",
    "d5azz": "Réservations sur documents disponibles, public, Quarantaine",
    "d5pzz": "Réservations sur documents disponibles, personnel, Quarantaine",
    "t0azz": "Réservations sur documents en traitement, public, RDC",
    "t0pzz": "Réservations sur documents en traitement, personnel, RDC",
    "t1azz": "Réservations sur documents en traitement, public, 1er étage",
    "t1pzz": "Réservations sur documents en traitement, personnel, 1er étage",
    "t2azz": "Réservations sur documents en traitement, public, 2e étage",
    "t2pzz": "Réservations sur documents en traitement, personnel, 2e étage",
    "t3azz": "Réservations sur documents en traitement, public, 3e étage",
    "t3pzz": "Réservations sur documents en traitement, personnel, 3e étage",
    "t4azz": "Réservations sur documents en traitement, public, Zèbre",
    "t4pzz": "Réservations sur documents en traitement, personnel, Zèbre",
    "e0azz": "Réservations expirées, pour retrait Médiathèque, public",
    "e0pzz": "Réservations expirées, pour retrait Médiathèque, personnel",
    "e4zzz": "Réservations expirées, pour retrait Zèbre",
    "e0zzz": "Réservations annulées la veille, pour retrait Médiathèque",
    "m0zzz": "Réservations mises de côté, pour retrait Médiathèque",
    "m4zzz": "Réservations mises de côté, pour retrait Zèbre",
    "p_et0_s1": "Documents perdus depuis une semaine, RDC",
    "p_et1_s1": "Documents perdus depuis une semaine, 1er étage",
    "p_et2_s1": "Documents perdus depuis une semaine, 2e étage",
    "p_et3_s1": "Documents perdus depuis une semaine, 3e étage",
    "p_et0_s3": "Documents perdus depuis trois semaines, RDC",
    "p_et1_s3": "Documents perdus depuis trois semaines, 1er étage",
    "p_et2_s3": "Documents perdus depuis trois semaines, 2e étage",
    "p_et3_s3": "Documents perdus depuis trois semaines, 3e étage",
    "p_et0_s5": "Documents perdus depuis cinq semaines, RDC",
    "p_et1_s5": "Documents perdus depuis cinq semaines, 1er étage",
    "p_et2_s5": "Documents perdus depuis cinq semaines, 2e étage",
    "p_et3_s5": "Documents perdus depuis cinq semaines, 3e étage",
    "aazzz": "Contentieux, personnes à appeler",
    "bbzzz": "Contentieux, titres de recettes à créer",
    "tzzzz": "Réservations reparties en rayons",
}

# NB : dans liste.pm, les 4 dernières entrées "p_et*_s1" du dictionnaire
# rap (les mêmes clés répétées avec des valeurs différentes) écrasent les
# précédentes en Perl (%hash) ; on ne garde donc que la dernière définition
# de chaque clé, comme le fait Perl.
#
# Les clés "d0azz" à "d4pzz" (réservations disponibles, hors quarantaine),
# "t0azz" à "t4pzz" (en traitement), "m0zzz"/"m4zzz" (mise de côté),
# "e0azz"/"e0pzz"/"e4zzz" (expirées, hors "annulées la veille" e0zzz qui reste
# ici) et "p_et0_s1" à "p_et3_s5" (perdus) ne sont plus dans cette table :
# elles sont servies par les rapports consolidés ci-dessous (_DISPO_PARAMS,
# _DISPO_BUS_PARAMS, _TRAIT_PARAMS, _TRAIT_BUS_PARAMS, _MISECOTE_PARAMS,
# _EXPIREES_PARAMS, _PERDUS_PARAMS).
_LISTE_RAPPORTS = {
    "d5azz": "205", "d5pzz": "206",
    "e0zzz": "177",
    "aazzz": "207", "bbzzz": "208", "tzzzz": "307",
}

# Rapport SQL Koha consolidé pour les réservations disponibles (d0azz..d4pzz),
# paramétré via les paramètres runtime Koha <<Localisation|list>>, <<Site>>
# et <<Cible est personnel>> (voir svc/report : sql_params/param_names).
_RAPPORT_DISPO_ID = "333"

_MED3_LOCATIONS = [f"MED3{lettre}" for lettre in "ABCDEFGHIJKLMNOPQRST"]

# Clé -> (codes de localisation, site de retrait, cible personnel ("1") ou public ("0"))
# Le Bus (d4azz/d4pzz) n'est pas ici : la jointure items/reserves par titre
# fait remonter, pour ce site, des réservations d'usagers sans rapport avec
# le Bus dès qu'un titre a par ailleurs un exemplaire en BUS1A. Un simple
# filtre sur le site de l'exemplaire ne suffit pas à écarter ces faux
# positifs ; il faut filtrer sur le site de rattachement de l'usager
# (bo.branchcode), d'où un rapport dédié (_RAPPORT_DISPO_BUS_ID) plutôt
# qu'une entrée paramétrée ici.
_DISPO_PARAMS = {
    "d0azz": (["MED0C"], "MED", "0"),
    "d0pzz": (["MED0C"], "MED", "1"),
    "d1azz": (["MED1A"], "MED", "0"),
    "d1pzz": (["MED1A"], "MED", "1"),
    "d2azz": (["MED2A", "MED2C"], "MED", "0"),
    "d2pzz": (["MED2A", "MED2C"], "MED", "1"),
    "d3azz": (_MED3_LOCATIONS, "MED", "0"),
    "d3pzz": (_MED3_LOCATIONS, "MED", "1"),
}

# Rapport SQL Koha dédié aux réservations disponibles pour le Bus (d4azz/d4pzz),
# avec filtre sur bo.branchcode = 'BUS' (site de rattachement de l'usager).
_RAPPORT_DISPO_BUS_ID = "334"

# Clé -> cible personnel ("1") ou public ("0")
_DISPO_BUS_PARAMS = {
    "d4azz": "0",
    "d4pzz": "1",
}

# Rapport SQL Koha consolidé pour les réservations en traitement (t0azz..t3pzz),
# même paramétrage que _RAPPORT_DISPO_ID. Le Bus (t4azz/t4pzz) est à part pour
# la même raison que pour dispo (voir _RAPPORT_DISPO_BUS_ID).
_RAPPORT_TRAIT_ID = "336"

_TRAIT_PARAMS = {
    "t0azz": (["MED0C"], "MED", "0"),
    "t0pzz": (["MED0C"], "MED", "1"),
    "t1azz": (["MED1A"], "MED", "0"),
    "t1pzz": (["MED1A"], "MED", "1"),
    "t2azz": (["MED2A", "MED2C"], "MED", "0"),
    "t2pzz": (["MED2A", "MED2C"], "MED", "1"),
    "t3azz": (_MED3_LOCATIONS, "MED", "0"),
    "t3pzz": (_MED3_LOCATIONS, "MED", "1"),
}

_RAPPORT_TRAIT_BUS_ID = "337"

_TRAIT_BUS_PARAMS = {
    "t4azz": "0",
    "t4pzz": "1",
}

# Rapport SQL Koha consolidé pour les réservations mises de côté (m0zzz/m4zzz).
# Pas de risque de remontée d'exemplaires d'un autre site ici (jointure sur
# itemnumber, pas sur biblionumber comme pour dispo/trait), donc un seul
# rapport suffit, paramétré par <<Est Bus>> ("1" = Bus, "0" = reste).
_RAPPORT_MISECOTE_ID = "338"

_MISECOTE_PARAMS = {
    "m0zzz": "0",
    "m4zzz": "1",
}

# Rapport SQL Koha consolidé pour les réservations expirées (e0azz/e0pzz/e4zzz).
# Le Bus (164 à l'origine) n'a pas de distinction public/personnel ; plutôt
# que d'en inventer une, <<Ignorer categorie>> désactive le filtre catégorie
# pour ce cas (voir le SQL du rapport : le filtre catégorie n'agit que si
# <<Ignorer categorie>> vaut "0"). Clé -> (site, cible personnel, ignorer categorie).
_RAPPORT_EXPIREES_ID = "339"

_EXPIREES_PARAMS = {
    "e0azz": ("MED", "0", "0"),
    "e0pzz": ("MED", "1", "0"),
    "e4zzz": ("BUS", "0", "1"),
}

# Rapport SQL Koha consolidé pour les documents perdus (p_et0_s1..p_et3_s5) :
# remplace 15 rapports quasi-identiques (WS_perdus_{une,trois,cinq}_semaines_
# et{0..3} + variante Bus), qui ne différaient que par la localisation et le
# nombre de semaines (<<Semaines>> dans YEARWEEK(... - INTERVAL <<Semaines>>
# WEEK)). Pas de risque de fan-out titre ici (jointure directe sur items, pas
# sur reserves/biblionumber comme pour dispo/trait) : le Bus pourrait passer
# par ce même rapport sans rapport dédié, simplement non exposé pour l'instant
# (aucune clé p_et4_s* dans _LISTE_TITRES).
# NB : avant cette consolidation, "p_et0_s1".."p_et3_s1" (depuis une semaine)
# pointaient par erreur vers les rapports "cinq semaines" (152-155) ; les
# rapports "trois"/"cinq" semaines existaient déjà côté Koha mais n'étaient
# jamais câblés ici (d'où le "gap" precedemment repéré dans le README).
_RAPPORT_PERDUS_ID = "340"

# Clé -> (codes de localisation, nombre de semaines)
_PERDUS_PARAMS = {
    "p_et0_s1": (["MED0C"], "1"),
    "p_et1_s1": (["MED1A"], "1"),
    "p_et2_s1": (["MED2A", "MED2C"], "1"),
    "p_et3_s1": (_MED3_LOCATIONS, "1"),
    "p_et0_s3": (["MED0C"], "3"),
    "p_et1_s3": (["MED1A"], "3"),
    "p_et2_s3": (["MED2A", "MED2C"], "3"),
    "p_et3_s3": (_MED3_LOCATIONS, "3"),
    "p_et0_s5": (["MED0C"], "5"),
    "p_et1_s5": (["MED1A"], "5"),
    "p_et2_s5": (["MED2A", "MED2C"], "5"),
    "p_et3_s5": (_MED3_LOCATIONS, "5"),
}

_LISTE_TEMPLATES = {
    "a": "liste_contentieux",
    "b": "liste_contentieuxb",
    "d": "liste_reservations",
    "t": "liste_reservations",
    "e": "liste_expirees",
    "m": "liste_misecote",
    "p": "liste_perdus",
}


def _rapport_localise(rapport_id, locations, site, cible_personnel):
    # param_names doit reprendre le texte exact entre << et >> dans le rapport
    # (suffixe |list inclus) : c'est la clé utilisée par Koha
    # (Koha::Report::prep_report) pour retrouver la valeur correspondante.
    return _webservice_get(
        f"/cgi-bin/koha/svc/report?id={rapport_id}",
        params=[
            ("param_names", "Localisation|list"),
            ("param_names", "Site"),
            ("param_names", "Cible est personnel"),
            ("sql_params", "\n".join(locations)),
            ("sql_params", site),
            ("sql_params", cible_personnel),
        ],
    )


def _rapport_param(rapport_id, param_name, value):
    return _webservice_get(
        f"/cgi-bin/koha/svc/report?id={rapport_id}",
        params=[
            ("param_names", param_name),
            ("sql_params", value),
        ],
    )


def _rapport_expirees(rapport_id, site, cible_personnel, ignorer_categorie):
    return _webservice_get(
        f"/cgi-bin/koha/svc/report?id={rapport_id}",
        params=[
            ("param_names", "Site"),
            ("param_names", "Cible est personnel"),
            ("param_names", "Ignorer categorie"),
            ("sql_params", site),
            ("sql_params", cible_personnel),
            ("sql_params", ignorer_categorie),
        ],
    )


def _rapport_perdus(rapport_id, locations, semaines):
    return _webservice_get(
        f"/cgi-bin/koha/svc/report?id={rapport_id}",
        params=[
            ("param_names", "Localisation|list"),
            ("param_names", "Semaines"),
            ("sql_params", "\n".join(locations)),
            ("sql_params", semaines),
        ],
    )


def get_list_data(params):
    for p in ("type", "loc", "public", "wk", "resbranch"):
        params.setdefault(p, "z")

    key = params["type"] + params["loc"] + params["public"] + params["wk"] + params["resbranch"]

    titre = _LISTE_TITRES.get(key)
    template = _LISTE_TEMPLATES.get(params["type"])

    if key in _DISPO_PARAMS:
        rows = _rapport_localise(_RAPPORT_DISPO_ID, *_DISPO_PARAMS[key])
    elif key in _DISPO_BUS_PARAMS:
        rows = _rapport_param(_RAPPORT_DISPO_BUS_ID, "Cible est personnel", _DISPO_BUS_PARAMS[key])
    elif key in _TRAIT_PARAMS:
        rows = _rapport_localise(_RAPPORT_TRAIT_ID, *_TRAIT_PARAMS[key])
    elif key in _TRAIT_BUS_PARAMS:
        rows = _rapport_param(_RAPPORT_TRAIT_BUS_ID, "Cible est personnel", _TRAIT_BUS_PARAMS[key])
    elif key in _MISECOTE_PARAMS:
        rows = _rapport_param(_RAPPORT_MISECOTE_ID, "Est Bus", _MISECOTE_PARAMS[key])
    elif key in _EXPIREES_PARAMS:
        rows = _rapport_expirees(_RAPPORT_EXPIREES_ID, *_EXPIREES_PARAMS[key])
    elif key in _PERDUS_PARAMS:
        rows = _rapport_perdus(_RAPPORT_PERDUS_ID, *_PERDUS_PARAMS[key])
    else:
        rapport = _LISTE_RAPPORTS.get(key)
        rows = _webservice_get(f"/cgi-bin/koha/svc/report?id={rapport}") if rapport else []

    return {"titre": titre, "template": template, "rows": rows}
