"""
Port de kibini_prod/bin/statdb_wifi.pl.

Lit le CSV des connexions wifi (/home/kibini/wk_web_wifi_logs.csv, sans
en-tête) et alimente statdb.stat_wifi, en résolvant le borrowernumber Koha à
partir du login (userid). Comme dans l'original, une ligne sans
correspondance dans koha_prod.borrowers est tout de même insérée, avec
borrowernumber = NULL.
"""
import csv

from sqlalchemy import text

from kiblib.utils.db import DbConn
from kiblib.utils.log import Log

CSV_PATH = "/home/kibini/wk_web_wifi_logs.csv"
CSV_FIELDNAMES = ("wifi_id", "start_wifi", "end_wifi", "login")

BORROWERNUMBER_QUERY = text("SELECT borrowernumber FROM koha_prod.borrowers WHERE userid = :login")

INSERT_QUERY = text(
    """
    INSERT INTO statdb.stat_wifi (wifi_id, start_wifi, end_wifi, login, borrowernumber)
    VALUES (:wifi_id, :start_wifi, :end_wifi, :login, :borrowernumber)
    """
)


def process_row(conn, row):
    borrowernumber = conn.execute(BORROWERNUMBER_QUERY, {"login": row["login"]}).scalar()
    conn.execute(
        INSERT_QUERY,
        {
            "wifi_id": row["wifi_id"],
            "start_wifi": row["start_wifi"],
            "end_wifi": row["end_wifi"],
            "login": row["login"],
            "borrowernumber": borrowernumber,
        },
    )


log = Log()
log.add_info(f'Lancement {log.script_name}')

engine = DbConn().create_engine()

nb_inserted = 0
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f, fieldnames=CSV_FIELDNAMES)
    for row in reader:
        with engine.begin() as conn:
            process_row(conn, row)
        nb_inserted += 1

log.add_info(f"{nb_inserted} lignes ajoutées")
log.add_info(f"Fin traitement {log.script_name}\n\n")
