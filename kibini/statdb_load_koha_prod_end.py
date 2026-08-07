from sqlalchemy import text

from kiblib.utils.db import DbConn
from kiblib.utils.log import Log

log = Log()
log.add_info('Lancement')

engine = DbConn().create_engine()

# on corrige les ccodes des périodiques
with engine.begin() as conn:
    conn.execute(
        text(
            """
            UPDATE koha_prod.items s
            JOIN statdb.lib_periodiques p ON s.biblionumber = p.biblionumber
            SET s.ccode = p.ccode
            """
        )
    )

log.add_info("Fin traitement\n\n")
