from kiblib.utils.conf import Config
import sqlalchemy
import mysql.connector as mc


class DbConn():
    def __init__(self):
        self.db_conf = Config().get_config_database()

    def create_engine(self):
        sqlalchemy_database_uri = f"mysql+pymysql://{self.db_conf['user']}:{self.db_conf['pwd']}@localhost:3306/{self.db_conf['db']}"
        self.engine = sqlalchemy.create_engine(
            sqlalchemy_database_uri, echo=False)
        return self.engine

    def create_db_con(self):
        self.mysql_con = mc.connect(
            user=self.db_conf['user'],
            password=self.db_conf['pwd'],
            host="localhost",
            port=3306,
            database=self.db_conf['db']
        )
        return self.mysql_con
