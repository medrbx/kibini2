import pandas as pd
import numpy as np
import datetime

from kiblib.adherent import Adherent
from kiblib.utils.es import Pd2Es
from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.utils.date import get_date_and_time, dfcol_split_datetime

class Webkiosk(Adherent):
    def __init__(self, **kwargs):
        if 'db_conn' in kwargs:
            self.db_conn = kwargs.get('db_conn')
        else:
            self.db_conn = DbConn().create_db_con()

        if 'c2l' in kwargs:
            self.c2l = kwargs.get('c2l')

        if 'df' in kwargs:
            self.df = kwargs.get('df')

        if 'session_mode' in kwargs:
            self.session_mode = kwargs.get('session_mode')

        self.webkiosk_statdb_columns = [
            'session_date_heure_deb',
            'session_date_heure_fin',
            'session_mode',
            'session_groupe',
            'session_poste',
            'adh_id',
            'adh_sexe_code',
            'adh_age_code',
            'adh_geo_ville',
            'adh_geo_rbx_iris_code',
            'adh_inscription_carte_code',
            'adh_inscription_site_code',
            'adh_inscription_carte_personnalite_code',
            'adh_inscription_nb_annees_adhesion',
            'adh_inscription_attribut_action_code',
            'adh_inscription_attribut_bus_code',
            'adh_inscription_attribut_collect_code',
            'adh_inscription_attribut_pcs_code'
        ]

        self.webkiosk_es_columns = [
            'session_id',
            'session_date_heure_deb',
            'session_date_heure_deb_annee',
            'session_date_heure_deb_heure',
            'session_date_heure_deb_jour',
            'session_date_heure_deb_jour_semaine',
            'session_date_heure_deb_mois',
            'session_date_heure_deb_semaine',
            'session_date_heure_fin',
            'session_date_heure_fin_annee',
            'session_date_heure_fin_heure',
            'session_date_heure_fin_jour',
            'session_date_heure_fin_jour_semaine',
            'session_date_heure_fin_mois',
            'session_date_heure_fin_semaine',
            'session_duration',
            'session_mode',
            'session_groupe',
            'session_poste',
            'adh_id',
            'adh_sexe',
            'adh_age_code',
            'adh_age_lib1',
            'adh_age_lib2',
            'adh_age_lib3',
            'adh_geo_ville',
            'adh_geo_ville_bm'
            'adh_geo_ville_limitrophe',
            'adh_geo_gentilite',
            'adh_geo_rbx_iris',
            'adh_geo_rbx_quartier',
            'adh_geo_rbx_secteur',
            'adh_inscription_carte',
            'adh_inscription_carte_type',
            'adh_inscription_carte_gratuite',
            'adh_inscription_carte_prix',
            'adh_inscription_carte_personnalite',
            'adh_inscription_site',
            'adh_inscription_nb_annees_adhesion',
            'adh_inscription_nb_annees_adhesion_tra',
            'adh_inscription_attribut_action',
            'adh_inscription_attribut_bus',
            'adh_inscription_attribut_collect',
            'adh_inscription_attribut_pcs'
        ]

    def get_webkiosk_statdb_data(self):
        #self.get_adherent_statdb_data()
        self.get_session_date_heure_fin()
        self.get_webkiosk_statdb_adh_data()
        self.get_webkiosk_statdb_data_columns()

    def get_webkiosk_es_data(self):
        self.get_adherent_es_data()
        self.get_session_date_heure_deb_det()
        self.get_session_date_heure_fin_det()
        self.get_session_duration()
        self.get_webkiosk_es_data_columns()

    def get_session_date_heure_fin(self):
        self.df.loc[self.df['session_date_heure_fin'] == '0000-00-00 00:00:00',
                    'session_date_heure_fin'] = self.df['session_date_heure_deb']
        self.df.loc[self.df['session_date_heure_fin'].isna(),
                    'session_date_heure_fin'] = self.df['session_date_heure_deb']

    def get_webkiosk_statdb_adh_data(self):
        if 'adh_cardnumber' in self.df:
            cardnumbers = self.df['adh_cardnumber'].dropna().tolist()
            if len(cardnumbers) > 0:
                query = """
                    SELECT
                        borrowernumber,
                        cardnumber as adh_cardnumber,
                        title,
                        dateofbirth,
                        city,
                        altcontactcountry,
                        branchcode,
                        categorycode,
                        dateenrolled
                    FROM koha_prod.borrowers
                    WHERE cardnumber in ({0})
                """
                query = query.format(','.join(['%s'] * len(cardnumbers)))
                bo = pd.read_sql(query, params=(cardnumbers), con=self.db_conn)
                adh = Adherent(df=bo, con=self.db_conn, c2l=self.c2l)
                adh.get_adherent_statdb_data()
                print(adh.df['age'])
                #adh.get_adherent_statdb_data_columns()
                self.df = pd.merge(self.df, adh.df,
                                   how='left',
                                   on='adh_cardnumber')

    def get_session_date_heure_deb_det(self):
        if 'session_date_heure_deb' in self.df:
            self.df = dfcol_split_datetime(self.df, 'session_date_heure_deb')

    def get_session_date_heure_fin_det(self):
        if 'session_date_heure_fin' in self.df:
            self.df = dfcol_split_datetime(self.df, 'session_date_heure_fin')

    def get_session_duration(self):
        if ('session_date_heure_deb' in self.df
                and 'session_date_heure_fin' in self.df):
            d1 = pd.to_datetime(self.df['session_date_heure_deb'])
            d2 = pd.to_datetime(self.df['session_date_heure_fin'])
            self.df['session_duration'] = np.around((d2 - d1).dt.seconds / 60).astype('int')

    def get_webkiosk_statdb_data_columns(self):
        if 'session_mode' not in self.df:
            if hasattr(self, 'session_mode'):
                self.df['session_mode'] = self.session_mode
        if 'session_mode' in self.df:
            columns_to_keep = []
            for c in self.webkiosk_statdb_columns:
                if c in self.df:
                    columns_to_keep.append(c)
            self.webkiosk_statdb_data = self.df[columns_to_keep]

    def get_webkiosk_es_data_columns(self):
        if 'session_mode' not in self.df:
            if hasattr(self, 'session_mode'):
                self.df['session_mode'] = self.session_mode
        if 'session_mode' in self.df:
            columns_to_keep = []
            for c in self.webkiosk_es_columns:
                if c in self.df:
                    columns_to_keep.append(c)
            self.webkiosk_es_data = self.df[columns_to_keep]

    def add_statdb_webkiosk_data(self):
        to_sql_conn = DbConn().create_engine()
        if 'session_mode' in self.df:
            self.webkiosk_statdb_data.to_sql('stat_webkiosk2020_1', con=to_sql_conn, if_exists='append', index=False)
        else:
            print("session_mode n'est pas renseigné")

    def ano_webkiosk_statdb_data(self):
        query= """
            UPDATE stat_webkiosk2020_1
            SET adh_id = null
            WHERE DATE(session_date_heure_deb) < CURDATE() - INTERVAL 1 YEAR
        """
        con = DbConn().create_engine()
        cur = con.cursor()
        cur.execute(query)
        con.commit()

    def add_es_webkiosk_data(self):
        if 'session_mode' in self.df:
            pd2es = Pd2Es()
            pd2es.es_write(self.webkiosk_es_data, "webkiosk2020", "sessions", uid_name='session_id')
        else:
            print("session_mode n'est pas renseigné")
