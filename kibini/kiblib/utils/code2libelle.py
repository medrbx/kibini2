import pandas as pd
from kiblib.utils.db import DbConn


class Code2Libelle():
    def __init__(self, db_conn):
        self.dict_codes_lib = {}
        self.db_conn = db_conn

    def get_val(self):
        self.get_val_age()
        self.get_val_age_code()
        self.get_val_ccode()
        self.get_val_iris()
        self.get_val_carte()
        self.get_val_site()
        self.get_val_attribut()
        self.get_val_localisation()
        self.get_val_doc_statut()
        self.get_val_doc_statut_abime()
        self.get_val_doc_statut_desherbe()
        self.get_val_doc_statut_perdu()
        self.get_val_doc_support()

    def get_val_age(self):
        query = """
            SELECT CONCAT("a", age) as age, acode, trinsee, trmeda, trmedb
            FROM statdb.lib_age2
        """
        df = pd.read_sql(query, con=self.db_conn)
        df = df.set_index('age')
        self.dict_codes_lib['age'] = df.to_dict('index')

    def get_val_age_code(self):
        query = """
            SELECT acode, trinsee, trmeda, trmedb
            FROM statdb.lib_age2
            GROUP BY acode
        """
        df = pd.read_sql(query, con=self.db_conn)
        df = df.set_index('acode')
        self.dict_codes_lib['adh_age_code'] = df.to_dict('index')

    def get_val_ccode(self):
        query = """
            SELECT ccode, lib1, lib2, lib3, lib4, lib
            FROM statdb.lib_collections2
        """
        df = pd.read_sql(query, con=self.db_conn)
        df = df.set_index('ccode')
        self.dict_codes_lib['ccode'] = df.to_dict('index')

    def get_val_iris(self):
        query = """
            SELECT irisInsee, irisNom, quartier, secteur
            FROM statdb.iris_lib
        """
        df = pd.read_sql(query, con=self.db_conn)
        df = df.set_index('irisInsee')
        self.dict_codes_lib['iris'] = df.to_dict('index')

    def get_val_carte(self):
        query = """
            SELECT categorycode, carte, carte_type, category_type, carte_gratuite, carte_prix, carte_personnalite
            FROM statdb.lib_categories
        """
        df = pd.read_sql(query, con=self.db_conn)
        df = df.set_index('categorycode')
        self.dict_codes_lib['carte'] = df.to_dict('index')

    def get_val_site(self):
        self.dict_codes_lib['site'] = {
            'MED': 'Médiathèque',
            'BUS': 'Zèbre',
            'MUS': 'Musée Diligent'}

    def get_val_attribut(self):
        self.dict_codes_lib['attributs'] = {
            "AM01": "Action éducative",
            "AM02": "Apéro culture",
            "AM03": "Eveil au livre",
            "AM04": "Médiation",
            "AM05": "Espace multimédia",
            "AM06": "Nouveaux habitants",
            "AM07": "Personnel Ville de Roubaix",
            "AM08": "Personnel \"La Redoute\"",
            "AM09": "Visite de classe",
            "AM10": "Chut on lit",
            "B00": "Arrêts foyers logements",
            "B01": "Arrêt Bus Rue Louis Braille",
            "B02": "Arrêt Bus Rue de Lannoy",
            "B03": "Arrêt Bus Place du Travail",
            "B04": "Arrêt Bus Rue du Danemark",
            "B05": "Arrêt Bus Place du Progrès",
            "B06": "Arrêt Bus Rue du Stand de tir",
            "B07": "Arrêt Bus Place Carnot",
            "B08": "Arrêt Bus Rue de France",
            "B09": "Arrêt Bus Rue de Rome",
            "B10": "Arrêt Bus Rue Léon Blum",
            "B11": "Arrêt Bus Place la de la Nation",
            "B12": "Arrêt Bus Rue de Philippeville",
            "B13": "Arrêt Bus Rue de la Fraternité",
            "B14": "Arrêt Bus Rue Jacques Prévert",
            "B15": "Arrêt Bus Rue Jean-Baptiste Vercoutère",
            "B16": "Arrêt Bus Avenue du Président Coty",
            "B17": "Arrêt Bus Rue Montgolfier",
            "B18": "Arrêt Bus Place Roussel",
            "B19": "Arrêt Bus Boulevard de Fourmies",
            "B20": "Arrêt Bus Rue d'Alger",
            "B21": "Arrêt Bus Rue Léo Lagrange",
            "B22": "Arrêt Bus Rue de Beaumont",
            "B23": "Arrêt Bus Rue de Philippeville",
            "B24": "Arrêt Bus Rue Drouot",
            "B25": "Arrêt Bus Avenue Julien Lagache",
            "B26": "Arrêt Bus Place de la Citoyenneté",
            "COL01": "Maternelle",
            "COL02": "Elémentaire",
            "COL03": "Structure petite enfance",
            "COL04": "Centre social",
            "COL05": "Accueil spécialisé",
            "COL06": "ALSH",
            "COL07": "Périscolaire",
            "COL08": "secondaire",
            "PCS01": "Agriculteurs exploitants",
            "PCS02": "Artisans, commerçants et chefs d'entreprise",
            "PCS03": "Cadres et professions intellectuelles supérieures",
            "PCS04": "Professions Intermédiaires",
            "PCS05": "Employés",
            "PCS06": "Ouvriers",
            "PCS07": "Retraités",
            "PCS08": "Lycéens",
            "PCS09": "Etudiants",
            "PCS10": "Autres personnes sans activité professionnelle"
        }

    def get_val_localisation(self):
        query = """
            SELECT authorised_value, lib
            FROM koha_prod.authorised_values
            WHERE category = 'LOC'
        """
        df = pd.read_sql(query, con=self.db_conn)
        df = df.set_index('authorised_value')
        self.dict_codes_lib['localisation'] = df.to_dict('index')

    def get_val_doc_statut(self):
        query = """
            SELECT authorised_value, lib
            FROM koha_prod.authorised_values
            WHERE category = 'ETAT'
        """
        df = pd.read_sql(query, con=self.db_conn)
        df = df.set_index('authorised_value')
        self.dict_codes_lib['doc_statut'] = df.to_dict('index')

    def get_val_doc_statut_abime(self):
        query = """
            SELECT authorised_value, lib
            FROM koha_prod.authorised_values
            WHERE category = 'DAMAGED'
        """
        df = pd.read_sql(query, con=self.db_conn)
        df = df.set_index('authorised_value')
        self.dict_codes_lib['doc_statut_abime'] = df.to_dict('index')

    def get_val_doc_statut_desherbe(self):
        query = """
            SELECT authorised_value, lib
            FROM koha_prod.authorised_values
            WHERE category = 'RETIRECOLL'
        """
        df = pd.read_sql(query, con=self.db_conn)
        df = df.set_index('authorised_value')
        self.dict_codes_lib['doc_statut_desherbe'] = df.to_dict('index')

    def get_val_doc_statut_perdu(self):
        query = """
            SELECT authorised_value, lib
            FROM koha_prod.authorised_values
            WHERE category = 'LOST'
        """
        df = pd.read_sql(query, con=self.db_conn)
        df = df.set_index('authorised_value')
        self.dict_codes_lib['doc_statut_perdu'] = df.to_dict('index')

    def get_val_doc_support(self):
        query = """
            SELECT authorised_value, lib
            FROM koha_prod.authorised_values
            WHERE category = 'TYPEDOC'
        """
        df = pd.read_sql(query, con=self.db_conn)
        df = df.set_index('authorised_value')
        self.dict_codes_lib['doc_biblio_support'] = df.to_dict('index')
