import os
import subprocess
from pathlib import Path

from kiblib.utils.conf import Config
from kiblib.utils.date import get_date_and_time
from kiblib.utils.log import Log

log = Log()
log.add_info('Lancement')

db_conf = Config().get_config_database()
user = db_conf["user"]
pwd = db_conf["pwd"]

date = get_date_and_time("today YYYYMMDD")
data_dir = Path(__file__).resolve().parent / "data" / "dumps_koha"
sql_file = data_dir / f"koha_prod_{date}.sql"

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

log.add_info("Fin traitement\n\n")
