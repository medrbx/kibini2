"""
Port de kibini_prod/bin/data_webkiosk.pl (PAS statdb_webkiosk.pl, qui appelle
une méthode inexistante get_data_to_statdb_webkiosk et n'a jamais dû tourner
tel quel).

Lit le CSV d'usage des postes webkiosk et alimente statdb.stat_webkiosk.
Seule la chaîne de traitement qui alimente réellement cette table a été
portée (pas l'export vers Elasticsearch, ni les champs calculés non utilisés
par cet INSERT - statdb_adherentid, statdb_attributes...).
"""
import csv
from datetime import datetime

from sqlalchemy import text

from kiblib.utils.db import DbConn
from kiblib.utils.log import Log

CSV_PATH = "/home/kibini/wk_users_logs_consommations.csv"
CSV_FIELDNAMES = ("date_heure_a", "date_heure_b", "session_groupe", "session_poste", "koha_userid")

BORROWER_QUERY = text(
    """
    SELECT dateofbirth, title, city, altcontactcountry, categorycode, branchcode, borrowernumber, dateenrolled
    FROM koha_prod.borrowers
    WHERE userid = :userid
    """
)

INSERT_QUERY = text(
    """
    INSERT INTO statdb.stat_webkiosk (
        heure_deb, heure_fin, espace, poste, id, borrowernumber,
        age, sexe, ville, iris, branchcode, categorycode, fidelite
    ) VALUES (
        :heure_deb, :heure_fin, :espace, :poste, :id, :borrowernumber,
        :age, :sexe, :ville, :iris, :branchcode, :categorycode, :fidelite
    )
    """
)

# categorycode pour lesquelles le sexe est pertinent (sinon 'NP')
CATEGORYCODES_SEXE = ("MEDA", "MEDB", "MEDC", "CSVT", "MEDP", "BIBL", "CSLT")

VILLES_OK = (
    "CROIX", "HEM", "LEERS", "LILLE", "LYS-LEZ-LANNOY", "MARCQ-EN-BAROEUL",
    "MONS-EN-BAROEUL", "MOUVAUX", "ROUBAIX", "TOURCOING", "VILLENEUVE-D'ASCQ",
    "WASQUEHAL", "WATTRELOS",
)
VILLES_RENOMMEES = {
    "LYS LEZ LANNOY": "LYS-LEZ-LANNOY",
    "MONS EN BAROEUL": "MONS-EN-BAROEUL",
    "MARCQ EN BAROEUL": "MARCQ-EN-BAROEUL",
    "VILLENEUVE D'ASCQ": "VILLENEUVE-D'ASCQ",
}


def normalize_ville(city):
    if not city:
        return None
    city = VILLES_RENOMMEES.get(city.upper(), city.upper())
    return city if city in VILLES_OK else "AUTRE"


def get_sexe_code(categorycode, title):
    if categorycode in CATEGORYCODES_SEXE:
        if title == "Madame":
            return "F"
        if title == "Monsieur":
            return "M"
        return "NC"
    return "NP"


def process_row(conn, row):
    heure_deb = datetime.strptime(row["date_heure_a"], "%Y-%m-%d %H:%M:%S")
    heure_fin = datetime.strptime(row["date_heure_b"], "%Y-%m-%d %H:%M:%S")

    borrower = conn.execute(BORROWER_QUERY, {"userid": row["koha_userid"]}).mappings().first()
    if borrower is None:
        return "skipped"

    age = heure_deb.year - borrower["dateofbirth"].year if borrower["dateofbirth"] else None
    fidelite = heure_deb.year - borrower["dateenrolled"].year if borrower["dateenrolled"] else None

    conn.execute(
        INSERT_QUERY,
        {
            "heure_deb": heure_deb,
            "heure_fin": heure_fin,
            "espace": row["session_groupe"],
            "poste": row["session_poste"],
            "id": row["koha_userid"],
            "borrowernumber": borrower["borrowernumber"],
            "age": age,
            "sexe": get_sexe_code(borrower["categorycode"], borrower["title"]),
            "ville": normalize_ville(borrower["city"]),
            "iris": borrower["altcontactcountry"],
            "branchcode": borrower["branchcode"],
            "categorycode": borrower["categorycode"],
            "fidelite": fidelite,
        },
    )
    return "inserted"


log = Log()
log.add_info('Lancement')

engine = DbConn().create_engine()

nb_inserted = 0
nb_skipped = 0
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f, fieldnames=CSV_FIELDNAMES)
    for row in reader:
        with engine.begin() as conn:
            outcome = process_row(conn, row)
        if outcome == "inserted":
            nb_inserted += 1
        else:
            nb_skipped += 1
            log.add_info(f"koha_userid={row['koha_userid']} introuvable dans koha_prod.borrowers (ignoré)")

log.add_info(f"{nb_inserted} lignes ajoutées, {nb_skipped} ignorées")
log.add_info("Fin traitement\n\n")
