import time

from sqlalchemy import text

from kiblib.utils.db import DbConn
from kiblib.utils.log import Log

STAT_ISSUES_COLUMNS = """
    issuedate, date_due, returndate, renewals, branch, borrowernumber,
    cardnumber, age, sexe, ville, iris, branchcode, categorycode, fidelite,
    itemnumber, homebranch, location, ccode, itemcallnumber, itemtype,
    publicationyear, biblionumber, dateaccessioned
"""

# on insère dans statdb les prêts de la veille
INSERT_STAT_ISSUES = f"""
    INSERT INTO statdb.stat_issues ({STAT_ISSUES_COLUMNS})
    SELECT
        o.issuedate, o.date_due, o.returndate, o.renewals_count, o.branchcode,
        o.borrowernumber, b.cardnumber,
        CASE
            WHEN b.categorycode NOT IN ('BIBL', 'CSLT', 'CSVT', 'MEDA', 'MEDB', 'MEDC', 'MEDP')
            THEN 'NP'
            ELSE YEAR(o.issuedate) - YEAR(b.dateofbirth)
        END,
        b.sex, b.city, b.altcontactcountry, b.branchcode, b.categorycode,
        YEAR(o.issuedate) - YEAR(b.dateenrolled),
        o.itemnumber, i.homebranch, i.location, i.ccode, i.itemcallnumber,
        bi.itemtype, bi.publicationyear, i.biblionumber, i.dateaccessioned
    FROM koha_prod.{{table}} o
    LEFT JOIN koha_prod.borrowers b ON o.borrowernumber = b.borrowernumber
    LEFT JOIN koha_prod.items i ON o.itemnumber = i.itemnumber
    LEFT JOIN koha_prod.biblioitems bi ON i.biblionumber = bi.biblionumber
    WHERE o.issuedate >= CURDATE() - INTERVAL 1 DAY AND o.issuedate < CURDATE()
"""


def run(engine, label, query):
    log.add_info(label)
    start = time.perf_counter()
    with engine.begin() as conn:
        result = conn.execute(text(query))
    elapsed = time.perf_counter() - start
    log.add_info(f"{label} : {elapsed:.2f}s ({result.rowcount} lignes)")


log = Log()
log.add_info('Lancement')

engine = DbConn().create_engine()

run(
    engine,
    "MaJ cle stat_issues",
    """
    UPDATE statdb.stat_issues
    SET cle = CONCAT(issuedate, '-', itemnumber)
    WHERE cle IS NULL
    """,
)

# ajoute la colonne 'cle' à koha_prod.old_issues si elle n'existe pas déjà
# (l'ALTER TABLE d'origine n'était pas gardé et échouait dès le 2e lancement)
log.add_info("ajout colonne cle sur old_issues (si absente)")
start = time.perf_counter()
with engine.begin() as conn:
    column_exists = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE table_schema = 'koha_prod'
              AND table_name = 'old_issues'
              AND column_name = 'cle'
            """
        )
    ).scalar()
    if not column_exists:
        conn.execute(
            text(
                """
                ALTER TABLE koha_prod.old_issues
                ADD COLUMN cle VARCHAR(75) NULL DEFAULT NULL AFTER issuedate,
                ADD INDEX index_cle (cle ASC)
                """
            )
        )
elapsed = time.perf_counter() - start
log.add_info(f"ajout colonne cle : {elapsed:.2f}s")

run(
    engine,
    "MaJ cle old_issues",
    """
    UPDATE koha_prod.old_issues
    SET cle = CONCAT(issuedate, '-', itemnumber)
    WHERE returndate >= CURDATE() - INTERVAL 1 DAY AND returndate < CURDATE()
    """,
)

# on insère dans statdb les prêts de la veille encore en cours
run(engine, "insertion issues", INSERT_STAT_ISSUES.format(table="issues"))

# on insère dans statdb les prêts de la veille déjà rendus
run(engine, "insertion old_issues", INSERT_STAT_ISSUES.format(table="old_issues"))

# on répercute dans statdb les retours de la veille
run(
    engine,
    "MaJ retours",
    """
    UPDATE statdb.stat_issues i
    JOIN koha_prod.old_issues o ON i.cle = o.cle
    SET i.returndate = o.returndate, i.renewals = o.renewals_count
    WHERE i.returndate IS NULL
      AND o.returndate >= CURDATE() - INTERVAL 1 DAY AND o.returndate < CURDATE()
    """,
)

# on affecte les arrêts de bus de la veille
run(
    engine,
    "MaJ arrets bus",
    """
    UPDATE statdb.stat_issues
    SET arret_bus = CASE
        WHEN DAYOFWEEK(issuedate) = 3 AND TIME(issuedate) BETWEEN '13:55:00' AND '15:05:00' THEN 'B01'
        WHEN DAYOFWEEK(issuedate) = 3 AND TIME(issuedate) BETWEEN '15:10:00' AND '16:20:00' THEN 'B13'
        WHEN DAYOFWEEK(issuedate) = 3 AND TIME(issuedate) BETWEEN '16:30:00' AND '18:20:00' THEN 'B03'
        WHEN DAYOFWEEK(issuedate) = 4 AND TIME(issuedate) BETWEEN '09:20:00' AND '10:40:00' THEN 'B24'
        WHEN DAYOFWEEK(issuedate) = 4 AND TIME(issuedate) BETWEEN '10:50:00' AND '11:50:00' THEN 'B14'
        WHEN DAYOFWEEK(issuedate) = 4 AND TIME(issuedate) BETWEEN '13:55:00' AND '15:05:00' THEN 'B07'
        WHEN DAYOFWEEK(issuedate) = 4 AND TIME(issuedate) BETWEEN '15:10:00' AND '16:20:00' THEN 'B08'
        WHEN DAYOFWEEK(issuedate) = 4 AND TIME(issuedate) BETWEEN '16:25:00' AND '17:45:00' THEN 'B09'
        WHEN DAYOFWEEK(issuedate) = 6 AND TIME(issuedate) BETWEEN '15:55:00' AND '17:10:00' THEN 'B23'
        WHEN DAYOFWEEK(issuedate) = 7 AND TIME(issuedate) BETWEEN '10:20:00' AND '11:45:00' THEN 'B26'
        WHEN DAYOFWEEK(issuedate) = 7 AND TIME(issuedate) BETWEEN '13:55:00' AND '15:10:00' THEN 'B17'
        WHEN DAYOFWEEK(issuedate) = 7 AND TIME(issuedate) BETWEEN '15:15:00' AND '16:45:00' THEN 'B19'
        ELSE 'INC'
    END
    WHERE branch = 'BUS' AND arret_bus IS NULL
      AND issuedate >= CURDATE() - INTERVAL 1 DAY AND issuedate < CURDATE()
    """,
)

# on corrige les ccodes des périodiques
run(
    engine,
    "MaJ ccode periodiques",
    """
    UPDATE statdb.stat_issues s
    JOIN statdb.lib_periodiques p ON s.biblionumber = p.biblionumber
    SET s.ccode = p.ccode
    WHERE s.issuedate >= CURDATE() - INTERVAL 1 DAY AND s.issuedate < CURDATE()
    """,
)

log.add_info("Fin traitement\n\n")
