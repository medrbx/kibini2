import gzip
import os
import shutil
import subprocess
from pathlib import Path

from sqlalchemy import text

from kiblib.utils.conf import Config
from kiblib.utils.date import get_date_and_time
from kiblib.utils.db import DbConn
from kiblib.utils.log import Log

log = Log()
log.add_info(f'Lancement {log.script_name}')

db_conf = Config().get_config_database()
user = db_conf["user"]
pwd = db_conf["pwd"]

date = get_date_and_time("today YYYYMMDD")
data_dir = Path(__file__).resolve().parent.parent / "data"
dump_source_dir = data_dir / "dumps_koha" / "dumps"
gz_file = data_dir / f"koha_prod_{date}.sql.gz"
sql_file = data_dir / f"koha_prod_{date}.sql"

shutil.copy(dump_source_dir / f"koha_prod_{date}.sql.gz", gz_file)
with gzip.open(gz_file, "rb") as f_in, sql_file.open("wb") as f_out:
    shutil.copyfileobj(f_in, f_out)
gz_file.unlink()
log.add_info(f"dump copié et décompressé : {sql_file}")

# on saute la première ligne du dump (tail -n +2 | mysql)
tail_proc = subprocess.Popen(
    ["tail", "-n", "+2", str(sql_file)],
    stdout=subprocess.PIPE,
)
mysql_proc = subprocess.run(
    [
        "mysql",
        "-u", user,
        "--init-command=SET FOREIGN_KEY_CHECKS=0; SET UNIQUE_CHECKS=0;",
        "koha_prod",
    ],
    stdin=tail_proc.stdout,
    env={**os.environ, "MYSQL_PWD": pwd},
)
tail_proc.stdout.close()
tail_proc.wait()

if tail_proc.returncode != 0:
    raise subprocess.CalledProcessError(tail_proc.returncode, tail_proc.args)
mysql_proc.check_returncode()

sql_file.unlink()

# on corrige les ccodes des périodiques (ex-statdb_load_koha_prod_end.py,
# fusionné ici - aucun script placé entre les deux dans le crontab n'utilise ccode)
engine = DbConn().create_engine()
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

log.add_info(f"Fin traitement {log.script_name}\n\n")
