import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from kiblib.utils.conf import Config
from kiblib.utils.date import get_date_and_time

class Log():
    def __init__(self):
        dir_log = Config().get_config_log()
        date = get_date_and_time('today YYYYMMDD')
        file_log = dir_log + "/crontab/" + "lanceur_" + date + ".log"
        logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(filename)s - %(levelname)s - %(message)s',
                    datefmt='%y-%m-%d %H:%M:%S',
                    filename=file_log,
                    filemode='a')
        logger = logging.getLogger()
        self.logger = logger
        self.script_name = Path(sys.argv[0]).name

    def add_info(self, text):
        self.logger.info(text)