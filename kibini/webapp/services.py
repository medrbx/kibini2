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


def _webservice_get(path):
    base = Config().get_config_webservice()["base"]
    resp = requests.get(f"{base}{path}")
    resp.raise_for_status()
    return resp.json()


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
_LISTE_RAPPORTS = {
    "d0azz": "128", "d0pzz": "187", "d1azz": "131", "d1pzz": "188",
    "d2azz": "132", "d2pzz": "189", "d3azz": "133", "d3pzz": "190",
    "d4azz": "170", "d4pzz": "191", "d5azz": "205", "d5pzz": "206",
    "t0azz": "144", "t0pzz": "192", "t1azz": "145", "t1pzz": "193",
    "t2azz": "146", "t2pzz": "194", "t3azz": "147", "t3pzz": "195",
    "t4azz": "172", "t4pzz": "196", "e0azz": "134", "e0pzz": "198",
    "e4zzz": "164", "e0zzz": "177", "m0zzz": "135", "m4zzz": "201",
    "p_et0_s1": "152", "p_et1_s1": "153", "p_et2_s1": "154", "p_et3_s1": "155",
    "aazzz": "207", "bbzzz": "208", "tzzzz": "307",
}

_LISTE_TEMPLATES = {
    "a": "liste_contentieux",
    "b": "liste_contentieuxb",
    "d": "liste_reservations",
    "t": "liste_reservations",
    "e": "liste_reservations",
    "m": "liste_reservations",
    "p": "liste_perdus",
}


def get_list_data(params):
    for p in ("type", "loc", "public", "wk", "resbranch"):
        params.setdefault(p, "z")

    key = params["type"] + params["loc"] + params["public"] + params["wk"] + params["resbranch"]

    titre = _LISTE_TITRES.get(key)
    template = _LISTE_TEMPLATES.get(params["type"])
    rapport = _LISTE_RAPPORTS.get(key)

    rows = _webservice_get(f"/cgi-bin/koha/svc/report?id={rapport}") if rapport else []

    return {"titre": titre, "template": template, "rows": rows}
