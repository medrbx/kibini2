import gzip
import os
import shutil
import subprocess
from pathlib import Path

from kiblib.utils.conf import Config
from kiblib.utils.date import get_date_and_time
from kiblib.utils.log import Log

log = Log()
log.add_info(f'Lancement {log.script_name}')

db_conf = Config().get_config_database()
user = db_conf["user"]
pwd = db_conf["pwd"]

date = get_date_and_time("today YYYYMMDD")
backup_dir = Path(__file__).resolve().parent.parent / "data" / "backup"
backup_dir.mkdir(parents=True, exist_ok=True)
backup_file = backup_dir / f"statdb_{date}.sql.gz"

mysqldump_proc = subprocess.Popen(
    ["mysqldump", "-u", user, "statdb"],
    stdout=subprocess.PIPE,
    env={**os.environ, "MYSQL_PWD": pwd},
)
with gzip.open(backup_file, "wb") as f_out:
    shutil.copyfileobj(mysqldump_proc.stdout, f_out)
mysqldump_proc.stdout.close()
mysqldump_proc.wait()

if mysqldump_proc.returncode != 0:
    raise subprocess.CalledProcessError(mysqldump_proc.returncode, mysqldump_proc.args)

log.add_info(f"sauvegarde écrite : {backup_file}")

# on ne garde jamais plus de 2 dumps sur le disque (les noms statdb_AAAAMMJJ.sql.gz
# se trient chronologiquement par ordre alphabétique)
NB_DUMPS_A_CONSERVER = 2
existing_dumps = sorted(backup_dir.glob("statdb_*.sql.gz"))
for old_dump in existing_dumps[:-NB_DUMPS_A_CONSERVER]:
    old_dump.unlink()
    log.add_info(f"ancien dump supprimé : {old_dump}")

log.add_info(f"Fin traitement {log.script_name}\n\n")
