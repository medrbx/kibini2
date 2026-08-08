from collections import defaultdict

from sqlalchemy import bindparam, text

from kiblib.utils.db import DbConn
from kiblib.utils.log import Log

CATEGORY_CODES = (
    "ECOL", "CLAS", "CSVT", "CSLT", "BIBL", "MEDB",
    "MEDA", "MEDC", "MEDP", "COLD", "COLI", "COLS",
)

# les 5 sources d'usage à combiner (clé interne, table, colonne date, filtre branche éventuel)
USE_SOURCES = (
    ("prets_mediatheque", "statdb.stat_issues", "issuedate", "MED"),
    ("prets_bus", "statdb.stat_issues", "issuedate", "BUS"),
    ("postes_informatiques", "statdb.stat_webkiosk", "heure_deb", None),
    ("wifi", "statdb.stat_wifi", "start_wifi", None),
    ("salle_etude", "statdb.stat_freq_etude", "datetime_entree", None),
)

BORROWERS_QUERY = text(
    """
    SELECT
        CURDATE() AS date_extraction,
        b.borrowernumber AS adherent_id,
        b.sex AS sexe,
        YEAR(CURDATE()) - YEAR(b.dateofbirth) AS age,
        b.city AS geo_ville,
        b.altcontactcountry AS geo_roubaix_iris,
        b.branchcode AS inscription_code_site,
        b.categorycode AS inscription_code_carte,
        YEAR(CURDATE()) - YEAR(b.dateenrolled) AS inscription_fidelite
    FROM koha_prod.borrowers b
    WHERE b.dateexpiry > CURDATE()
      AND b.categorycode IN :category_codes
    """
).bindparams(bindparam("category_codes", expanding=True))

INSERT_QUERY = text(
    """
    INSERT INTO statdb.stat_adherents (
        date_extraction, age, geo_ville, geo_roubaix_iris, sexe,
        inscription_code_carte, inscription_code_site, inscription_attribut,
        inscription_fidelite, nb_venues_prets_mediatheque, nb_venues_prets_bus,
        nb_venues_postes_informatiques, nb_venues_wifi, nb_venues_salle_etude,
        nb_venues
    ) VALUES (
        :date_extraction, :age, :geo_ville, :geo_roubaix_iris, :sexe,
        :inscription_code_carte, :inscription_code_site, :inscription_attribut,
        :inscription_fidelite, :nb_venues_prets_mediatheque, :nb_venues_prets_bus,
        :nb_venues_postes_informatiques, :nb_venues_wifi, :nb_venues_salle_etude,
        :nb_venues
    )
    """
)


def fetch_attributes_by_borrower(conn):
    """
    Un seul aller-retour pour tous les attributs (6 600 lignes environ, contre
    une requête par adhérent dans le portage 1:1 initial).

    Format confirmé sur les données réelles de statdb.stat_adherents (ex.
    'AM01|B08', 'AM07|PCS05') : seule la valeur 'attribute' est conservée,
    jointe par '|' - pas 'code'. Cohérent avec la colonne varchar(50) en
    base, et avec le comportement probable du fetchrow_array en contexte
    scalaire dans le Perl d'origine (ambigu, cf. discussion).
    """
    rows = conn.execute(text("SELECT borrowernumber, attribute FROM koha_prod.borrower_attributes"))
    by_borrower = defaultdict(list)
    for borrowernumber, attribute in rows:
        by_borrower[borrowernumber].append(attribute)
    return {borrowernumber: "|".join(parts) for borrowernumber, parts in by_borrower.items()}


def fetch_dates_by_borrower(conn, table, date_col, since, until, branch=None):
    """
    Un seul aller-retour par source d'usage pour tous les adhérents (au lieu
    d'une requête par adhérent par source).
    """
    branch_filter = " AND branch = :branch" if branch else ""
    params = {"since": since, "until": until}
    if branch:
        params["branch"] = branch
    rows = conn.execute(
        text(
            f"""
            SELECT DISTINCT borrowernumber, DATE({date_col}) FROM {table}
            WHERE {date_col} >= :since AND {date_col} < :until{branch_filter}
            """
        ),
        params,
    )
    by_borrower = defaultdict(set)
    for borrowernumber, day in rows:
        by_borrower[borrowernumber].add(day)
    return by_borrower


log = Log()
log.add_info('Lancement')

engine = DbConn().create_engine()
with engine.begin() as conn:
    today, since = conn.execute(text("SELECT CURDATE(), CURDATE() - INTERVAL 1 YEAR")).one()
    adherents = conn.execute(BORROWERS_QUERY, {"category_codes": CATEGORY_CODES}).mappings().all()
    attributes_by_borrower = fetch_attributes_by_borrower(conn)
    dates_by_source = {
        key: fetch_dates_by_borrower(conn, table, date_col, since, today, branch)
        for key, table, date_col, branch in USE_SOURCES
    }

log.add_info(f"{len(adherents)} adhérents éligibles")

rows_to_insert = []
for adherent in adherents:
    borrower_id = adherent["adherent_id"]

    venues = {key: dates_by_source[key].get(borrower_id, set()) for key, *_ in USE_SOURCES}
    toutes_dates = set().union(*venues.values())

    rows_to_insert.append(
        {
            "date_extraction": adherent["date_extraction"],
            "age": adherent["age"],
            "geo_ville": adherent["geo_ville"],
            "geo_roubaix_iris": adherent["geo_roubaix_iris"],
            "sexe": adherent["sexe"],
            "inscription_code_carte": adherent["inscription_code_carte"],
            "inscription_code_site": adherent["inscription_code_site"],
            "inscription_attribut": attributes_by_borrower.get(borrower_id, ""),
            "inscription_fidelite": adherent["inscription_fidelite"],
            "nb_venues_prets_mediatheque": len(venues["prets_mediatheque"]),
            "nb_venues_prets_bus": len(venues["prets_bus"]),
            "nb_venues_postes_informatiques": len(venues["postes_informatiques"]),
            "nb_venues_wifi": len(venues["wifi"]),
            "nb_venues_salle_etude": len(venues["salle_etude"]),
            "nb_venues": len(toutes_dates),
        }
    )

with engine.begin() as conn:
    conn.execute(INSERT_QUERY, rows_to_insert)

log.add_info(f"{len(rows_to_insert)} adhérents ajoutés")
log.add_info("Fin traitement\n\n")
