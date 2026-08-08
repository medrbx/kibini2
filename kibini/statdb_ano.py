from sqlalchemy import text

from kiblib.utils.db import DbConn
from kiblib.utils.log import Log

log = Log()
log.add_info('Lancement')

engine = DbConn().create_engine()

with engine.begin() as conn:
    result = conn.execute(
        text(
            """
            UPDATE statdb.stat_sessions_webkiosk
            SET
                adherent_adherentid = NULL,
                updated_on = NOW()
            WHERE session_date_heure_debut < CURDATE() - INTERVAL 1 YEAR
              AND adherent_adherentid IS NOT NULL
            """
        )
    )

log.add_info(f"statdb_sessions_webkiosk : {result.rowcount} lignes anonymisées")
log.add_info("Fin traitement\n\n")
