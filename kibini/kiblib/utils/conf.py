from yaml import safe_load
import os.path


class Config():
    def __init__(self):
        my_path = os.path.abspath(os.path.dirname(__file__))
        config_file_path = os.path.join(my_path, '../../conf/kibini_conf.yml')
        with open(config_file_path, 'r') as stream:
            try:
                self.dataconfig = safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def get_config_database(self):
        return self.dataconfig['database']

    def get_config_webservice(self):
        return self.dataconfig['webservice']

    def get_config_salt(self):
        return self.dataconfig['salt']

    def get_config_log(self):
        return self.dataconfig['dir_log']
        
    def get_config_data(self):
        return self.dataconfig['dir_data']
        
    def get_config_webdav(self):
        return self.dataconfig['dir_webdav']
        
    def get_config_smtp(self):
        return self.dataconfig['smtp']
        
    def get_config_acquereurs(self):
        return self.dataconfig['acquereurs']

    def get_config_stat_sugg(self):
        return self.dataconfig['stat_sugg']
