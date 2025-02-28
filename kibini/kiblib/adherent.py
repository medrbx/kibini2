import pandas as pd
import numpy as np
import datetime

from kiblib.utils.db import DbConn
from kiblib.utils.hashid import hash_identifier
from kiblib.utils.code2libelle import Code2Libelle

class Adherent():
    """
    Gérer l'ensemble des informations relatives aux adhérents.
    """

    def __init__(self, **kwargs):
        if 'db_conn' in kwargs:
            self.db_conn = kwargs.get('db_conn')
        else:
            self.db_conn = DbConn().create_db_con()

        if 'c2l' in kwargs:
            self.c2l = kwargs.get('c2l')
        else:
            c2l = Code2Libelle(self.db_conn)
            c2l.get_val()
            self.c2l = c2l.dict_codes_lib

        if 'df' in kwargs:
            self.df = kwargs.get('df')
        else:
            query = """
                SELECT
                    borrowernumber,
                    cardnumber,
                    title,
                    dateofbirth,
                    city,
                    altcontactcountry,
                    branchcode,
                    categorycode,
                    dateenrolled
                FROM koha_prod.borrowers
                ORDER BY borrowernumber ASC
                LIMIT 100
            """
            self.df = pd.read_sql(query, con=self.db_conn)


        # en sortie, on doit obtenir les champs suivants pour statdb :
        self.adherent_statdb_columns = [
            'adh_id',
            'adh_sexe_code',
            'adh_age_code',
            'adh_geo_ville',
            'adh_geo_rbx_iris_code',
            'adh_inscription_carte_code',
            'adh_inscription_site_code',
            'adh_inscription_nb_annees_adhesion',
            'adh_inscription_attribut_action_code',
            'adh_inscription_attribut_bus_code',
            'adh_inscription_attribut_collect_code',
            'adh_inscription_attribut_pcs_code',
            'adh_inscription_carte_personnalite_code'
        ]

        # en sortie, on doit obtenir les champs suivants pour es :
        self.adherent_es_columns = [
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
            'adh_geo_rbx_iris_code',
            'adh_geo_rbx_iris',
            'adh_geo_rbx_quartier',
            'adh_geo_rbx_secteur',
            'adh_inscription_carte'
            'adh_inscription_carte_code',
            'adh_inscription_carte_type',
            'adh_inscription_carte_gratuite',
            'adh_inscription_carte_prix',
            'adh_inscription_carte_personnalite_code',
            'adh_inscription_carte_personnalite',
            'adh_inscription_site_code',
            'adh_inscription_site',
            'adh_inscription_nb_annees_adhesion',
            'adh_inscription_nb_annees_adhesion_tra',
            'adh_inscription_attribut_action_code',
            'adh_inscription_attribut_bus_code',
            'adh_inscription_attribut_collect_code',
            'adh_inscription_attribut_pcs_code',
            'adh_inscription_attribut_action',
            'adh_inscription_attribut_bus',
            'adh_inscription_attribut_collect',
            'adh_inscription_attribut_pcs'
        ]

    def get_adherent_statdb_data(self):
        self.get_adherent_id()
        self.get_inscription_carte_code()
        self.get_inscription_carte_personnalite_code()
        self.get_inscription_site_code()
        self.get_inscription_attributs_code()
        self.get_sexe_code()
        self.get_age_code_by_dateofbirth()
        self.get_age_code_by_age()
        self.get_geo_ville()
        self.get_geo_rbx_iris()
        self.get_inscription_nb_annees_adhesion()

    def get_adherent_es_data(self):
        self.get_adherent_id()
        self.get_sexe()
        self.get_age_lib1()
        self.get_age_lib2()
        self.get_age_lib3()
        self.get_geo_gentilite()
        self.get_geo_rbx_nom_iris()
        self.get_geo_rbx_quartier()
        self.get_geo_rbx_secteur()
        self.get_inscription_carte()
        self.get_inscription_carte_type()
        self.get_inscription_carte_gratuite()
        self.get_inscription_carte_prix()
        self.get_inscription_carte_personnalite()
        self.get_inscription_site()
        self.get_inscription_nb_annees_adhesion_tra()
        self.get_inscription_attribut_action()
        self.get_inscription_attribut_bus()
        self.get_inscription_attribut_collect()
        self.get_inscription_attribut_pcs()

    def get_adherent_id(self):
        if 'borrowernumber' in self.df and 'adh_id' not in self.df:
            self.df['adh_id'] = self.df['borrowernumber'].apply(
                hash_identifier)

    def get_sexe_code(self):
        if 'title' in self.df and 'adh_sexe_code' not in self.df:
            self.df['adh_sexe_code'] = 'NC'
            self.df.loc[self.df['title'] == 'Madame', 'adh_sexe_code'] = 'F'
            self.df.loc[self.df['title'] == 'Monsieur', 'adh_sexe_code'] = 'M'
            self.df.loc[self.df['title'] == 'Madame', 'adh_sexe_code'] = 'F'
            self.df.loc[self.df['adh_inscription_carte_personnalite_code'] == 'I', 'adh_sexe_code'] = 'NP'


    def get_sexe(self):
        if 'adh_sexe_code' in self.df and 'adh_sexe' not in self.df:
            self.df.loc[self.df['adh_sexe_code'] == 'F', 'adh_sexe'] = 'Féminin'
            self.df.loc[self.df['adh_sexe_code'] == 'M', 'adh_sexe'] = 'Masculin'
            self.df.loc[self.df['adh_sexe_code'] == 'NC', 'adh_sexe'] = 'Inconnu'
            self.df.loc[self.df['adh_sexe_code'] == 'NP', 'adh_sexe'] = 'Non pertinent'

    def get_age_code_by_dateofbirth(self):
        if 'dateofbirth' in self.df and 'adh_age_code' not in self.df:
            now = datetime.date.today().year
            birth_year = self.df['dateofbirth'].astype(
                'datetime64[ns]').dt.year
            self.df['adh_age'] = now - birth_year
            if self.df['adh_age'].notna:
                self.df['adh_age'] = "a" + self.df['adh_age'].astype('str').str.extract(pat = '([0-9]*)\.')
                self.df['adh_age_code'] = self.df['adh_age'].apply(
                    lambda x: self.c2l['age'][x]['acode'] if x in self.c2l['age'] else 'NC')
            else:
                self.df['adh_age_code'] = 'NC'
            self.df.loc[self.df['adh_inscription_carte_personnalite_code'] == 'I', 'adh_age_code'] = 'NP'

    def get_age_code_by_age(self):
        if 'adh_age' in self.df and 'adh_age_code' not in self.df:
            if self.df['adh_age'].notna:
                self.df['adh_age'] = "a" + self.df['adh_age'].astype('str').str.extract(pat = '([0-9]*)\.')
                self.df['adh_age_code'] = self.df['adh_age'].apply(
                    lambda x: self.c2l['age'][x]['acode'] if x in self.c2l['age'] else 'NC')
            else:
                self.df['adh_age_code'] = 'NC'
            self.df.loc[self.df['adh_inscription_carte_personnalite_code'] == 'I', 'adh_age_code'] = 'NP'

    def get_age_lib1(self):
        if 'adh_age_code' in self.df and 'adh_age_lib1' not in self.df:
            self.df['adh_age_lib1'] = self.df['adh_age_code'].apply(
                lambda x: self.c2l['adh_age_code'][x]['trinsee'] if x in self.c2l['adh_age_code'] else np.nan)
            self.df.loc[self.df['adh_age_code'] == 'NC', 'adh_age_lib1'] = 'Inconnu'
            self.df.loc[self.df['adh_age_code'] == 'NP', 'adh_age_lib1'] = 'Non pertinent'

    def get_age_lib2(self):
        if 'adh_age_code' in self.df and 'adh_age_lib2' not in self.df:
            self.df['adh_age_lib2'] = self.df['adh_age_code'].apply(
                lambda x: self.c2l['adh_age_code'][x]['trmeda'] if x in self.c2l['adh_age_code'] else np.nan)
            self.df.loc[self.df['adh_age_code'] == 'NC', 'adh_age_lib2'] = 'Inconnu'
            self.df.loc[self.df['adh_age_code'] == 'NP', 'adh_age_lib2'] = 'Non pertinent'

    def get_age_lib3(self):
        if 'adh_age_code' in self.df and 'adh_age_lib3' not in self.df:
            self.df['adh_age_lib3'] = self.df['adh_age_code'].apply(
                lambda x: self.c2l['adh_age_code'][x]['trmedb'] if x in self.c2l['adh_age_code'] else np.nan)
            self.df.loc[self.df['adh_age_code'] == 'NC', 'adh_age_lib3'] = 'Inconnu'
            self.df.loc[self.df['adh_age_code'] == 'NP', 'adh_age_lib3'] = 'Non pertinent'

    def get_geo_ville(self):
        if 'city' in self.df and 'adh_geo_ville' not in self.df:
            villes_ok = ["CROIX", "HEM", "LEERS", "LILLE", "LYS-LEZ-LANNOY",
                         "MARCQ-EN-BAROEUL", "MONS-EN-BAROEUL",
                         "MOUVAUX", "ROUBAIX", "TOURCOING",
                         "VILLENEUVE-D'ASCQ", "WASQUEHAL", "WATTRELOS"]
            villes_limitrophe = ["CROIX", "HEM", "LEERS", "LYS-LEZ-LANNOY",
                                 "ROUBAIX", "TOURCOING", "WATTRELOS"]
            villes_bm = ["LILLE", "LYS-LEZ-LANNOY",
                         "MARCQ-EN-BAROEUL", "MONS-EN-BAROEUL",
                         "MOUVAUX", "ROUBAIX", "TOURCOING",
                         "VILLENEUVE-D'ASCQ", "WASQUEHAL", "WATTRELOS"]

            self.df['city'] = self.df['city'].str.upper()
            self.df.loc[self.df['city'] ==
                        'LYS LEZ LANNOY', 'city'] = 'LYS-LEZ-LANNOY'
            self.df.loc[self.df['city'] == 'MARCQ EN BAROEUL',
                        'city'] = 'MARCQ-EN-BAROEUL'
            self.df.loc[self.df['city'] == 'MONS EN BAROEUL',
                        'city'] = 'MONS-EN-BAROEUL'
            self.df.loc[self.df['city'] == 'VILLENEUVE D\'ASCQ',
                        'city'] = 'VILLENEUVE-D\'ASCQ'

            # geo_ville
            self.df['adh_geo_ville'] = "AUTRE"
            self.df.loc[self.df['city'].isin(
                villes_ok), 'adh_geo_ville'] = self.df['city']

            # geo_ville_bm
            self.df['adh_geo_ville_bm'] = "NP"
            self.df.loc[self.df['city'].isin(
                villes_ok), 'adh_geo_ville_bm'] = "non"
            self.df.loc[self.df['city'].isin(
                villes_bm), 'adh_geo_ville_bm'] = "ville_bm"

            # geo_ville_limitrophe
            self.df['adh_geo_ville_limitrophe'] = "non"
            self.df.loc[self.df['city'].isin(
                villes_limitrophe), 'adh_geo_ville_limitrophe'] = "limitrophe"

    def get_geo_gentilite(self):
        if 'adh_geo_ville' in self.df and 'adh_geo_gentilite' not in self.df:
            self.df['adh_geo_gentilite'] = "Non Roubaisien"
            self.df.loc[self.df['adh_geo_ville'] == 'ROUBAIX',
                        'adh_geo_gentilite'] = "Roubaisien"

    def get_geo_rbx_iris(self):
        if ('altcontactcountry' in self.df and
                'adh_geo_rbx_iris_code' not in self.df):
            self.df['altcontactcountry'] = self.df['altcontactcountry'].astype(
                'str')
            self.df.loc[self.df['altcontactcountry'].str.startswith(
                '59'), 'adh_geo_rbx_iris_code'] = self.df['altcontactcountry']

    def get_geo_rbx_nom_iris(self):
        if ('adh_geo_rbx_iris_code' in self.df and
                'adh_geo_rbx_iris' not in self.df):
            self.df['adh_geo_rbx_iris'] = self.df['adh_geo_rbx_iris_code'].apply(
                lambda x: self.c2l['iris'][x]['irisNom'] if x in self.c2l['iris'] else np.nan)

    def get_geo_rbx_quartier(self):
        if ('adh_geo_rbx_iris_code' in self.df and
                'adh_geo_rbx_quartier' not in self.df):
            self.df['adh_geo_rbx_quartier'] = self.df['adh_geo_rbx_iris_code'].apply(
                lambda x: self.c2l['iris'][x]['quartier'] if x in self.c2l['iris'] else np.nan)

    def get_geo_rbx_secteur(self):
        if ('adh_geo_rbx_iris_code' in self.df and
                'geo_rbx_secteur' not in self.df):
            self.df['geo_rbx_secteur'] = self.df['adh_geo_rbx_iris_code'].apply(
                lambda x: self.c2l['iris'][x]['secteur'] if x in self.c2l['iris'] else np.nan)

    def get_inscription_carte_code(self):
        if ('categorycode' in self.df and
                'adh_inscription_carte_code' not in self.df):
            self.df['adh_inscription_carte_code'] = self.df['categorycode']

    def get_inscription_carte(self):
        if ('adh_inscription_carte_code' in self.df and
                'inscription_carte' not in self.df):
            self.df['inscription_carte'] = self.df['adh_inscription_carte_code'].apply(
                lambda x: self.c2l['carte'][x]['carte'] if x in self.c2l['carte'] else np.nan)

    def get_inscription_carte_type(self):
        if ('adh_inscription_carte_code' in self.df and
                'adh_inscription_carte_type' not in self.df):
            self.df['adh_inscription_carte_type'] = self.df['adh_inscription_carte_code'].apply(
                lambda x: self.c2l['carte'][x]['carte_type'] if x in self.c2l['carte'] else np.nan)

    def get_inscription_carte_gratuite(self):
        if ('adh_inscription_carte_code' in self.df and
                'adh_inscription_carte_gratuite' not in self.df):
            self.df['adh_inscription_carte_gratuite'] = self.df['adh_inscription_carte_code'].apply(
                lambda x: self.c2l['carte'][x]['carte_gratuite'] if x in self.c2l['carte'] else np.nan)

    def get_inscription_carte_prix(self):
        if ('adh_inscription_carte_code' in self.df and
                'adh_inscription_carte_prix' not in self.df):
            self.df['adh_inscription_carte_prix'] = self.df['adh_inscription_carte_code'].apply(
                lambda x: self.c2l['carte'][x]['carte_prix'] if x in self.c2l['carte'] else np.nan)

    def get_inscription_carte_personnalite_code(self):
        if ('adh_inscription_carte_code' in self.df and
                'adh_inscription_carte_personnalite_code' not in self.df):
            self.df['adh_inscription_carte_personnalite_code'] = self.df['adh_inscription_carte_code'].apply(
                lambda x: self.c2l['carte'][x]['category_type'] if x in self.c2l['carte'] else np.nan)

    def get_inscription_carte_personnalite(self):
        if ('adh_inscription_carte_personnalite_code' in self.df and
                'adh_inscription_carte_personnalite' not in self.df):
            self.df.loc[self.df['adh_inscription_carte_personnalite_code'] == 'C', 'adh_inscription_carte_personnalite'] = 'Personne'
            self.df.loc[self.df['adh_inscription_carte_personnalite_code'] == 'I', 'adh_inscription_carte_personnalite'] = 'Collectivité'




    def get_inscription_site_code(self):
        if ('branchcode' in self.df and
                'adh_inscription_site_code' not in self.df):
            self.df['adh_inscription_site_code'] = self.df['branchcode'].astype('str')

    def get_inscription_site(self):
        if ('adh_inscription_site_code' in self.df and
                'adh_inscription_site' not in self.df):
            self.df['adh_inscription_site'] = self.df['adh_inscription_site_code'].apply(
                lambda x: self.c2l['site'][x] if x in self.c2l['site'] else np.nan)

    def get_inscription_nb_annees_adhesion(self):
        if ('dateenrolled' in self.df and
                'adh_inscription_nb_annees_adhesion' not in self.df):
            now = datetime.date.today().year
            year_enrolled = self.df['dateenrolled'].astype(
                'datetime64[ns]').dt.year
            self.df['adh_inscription_nb_annees_adhesion'] = now - year_enrolled

    def get_inscription_nb_annees_adhesion_tra(self):
        if ('adh_inscription_nb_annees_adhesion' in self.df and
                'adh_inscription_nb_annees_adhesion_tra' not in self.df):
            def get_inscription_nb_annees_adhesion_tra(
                    inscription_nb_annees_adhesion):
                if inscription_nb_annees_adhesion == 0:
                    inscription_nb_annees_adhesion_tra = "a/ 0"
                elif inscription_nb_annees_adhesion == 1:
                    inscription_nb_annees_adhesion_tra = "b/ 1"
                elif inscription_nb_annees_adhesion == 2:
                    inscription_nb_annees_adhesion_tra = "c/ 2"
                elif inscription_nb_annees_adhesion == 3:
                    inscription_nb_annees_adhesion_tra = "d/ 3"
                elif inscription_nb_annees_adhesion == 4:
                    inscription_nb_annees_adhesion_tra = "e/ 4"
                elif (inscription_nb_annees_adhesion > 4 and
                      inscription_nb_annees_adhesion <= 10):
                    inscription_nb_annees_adhesion_tra = "f/ 5 - 10 ans"
                else:
                    inscription_nb_annees_adhesion_tra = "g/ Plus de 10 ans"
                return inscription_nb_annees_adhesion_tra
            self.df['adh_inscription_nb_annees_adhesion_tra'] = self.df['adh_inscription_nb_annees_adhesion'].apply(
                get_inscription_nb_annees_adhesion_tra)

    def get_inscription_attributs_code(self):
        if ('borrowernumber' in self.df and
                'adh_inscription_attribut_action_code' not in self.df):
            borrowernumbers = self.df['borrowernumber'].dropna().tolist()
            if len(borrowernumbers) > 0:
                query = """
                    SELECT borrowernumber, code, attribute
                    FROM koha_prod.borrower_attributes
                    WHERE borrowernumber in ({0})
                """
                query = query.format(','.join(['%s'] * len(borrowernumbers)))
                attributes = pd.read_sql(query, params=(borrowernumbers), con=self.db_conn)
                if not attributes.empty:
                    attributes.drop_duplicates(
                        subset=[
                            'borrowernumber',
                            'code'],
                        keep='first',
                        inplace=True)
                    attributes = attributes.pivot(
                        index='borrowernumber',
                        columns='code',
                        values='attribute')
                    attributes = attributes.reset_index()
                    for c in ['ACTION', 'BUS', 'COLLECT', 'PCS']:
                        if c not in attributes:
                            attributes[c] = np.nan
                    attributes.columns = [
                        'borrowernumber',
                        'adh_inscription_attribut_action_code',
                        'adh_inscription_attribut_bus_code',
                        'adh_inscription_attribut_collect_code',
                        'adh_inscription_attribut_pcs_code']

                    self.df = pd.merge(
                        self.df,
                        attributes,
                        on='borrowernumber',
                        how='left')

    def get_inscription_attribut_action(self):
        if ('adh_inscription_attribut_action_code' in self.df and
                'adh_inscription_attribut_action' not in self.df):
            self.df['adh_inscription_attribut_action'] = self.df['adh_inscription_attribut_action_code'].apply(
                lambda x: self.c2l['attributs'][x] if x in self.c2l['attributs'] else np.nan)

    def get_inscription_attribut_bus(self):
        if ('adh_inscription_attribut_bus_code' in self.df and
                'adh_inscription_attribut_bus' not in self.df):
            self.df['adh_inscription_attribut_bus'] = self.df['adh_inscription_attribut_bus_code'].apply(
                lambda x: self.c2l['attributs'][x] if x in self.c2l['attributs'] else np.nan)

    def get_inscription_attribut_collect(self):
        if ('adh_inscription_attribut_collect_code' in self.df and
                'adh_inscription_attribut_collect' not in self.df):
            self.df['adh_inscription_attribut_collect'] = self.df['adh_inscription_attribut_collect_code'].apply(
                lambda x: self.c2l['attributs'][x] if x in self.c2l['attributs'] else np.nan)

    def get_inscription_attribut_pcs(self):
        if ('adh_inscription_attribut_pcs_code' in self.df and
                'adh_inscription_attribut_pcs' not in self.df):
            self.df['adh_inscription_attribut_pcs'] = self.df['adh_inscription_attribut_pcs_code'].apply(
                lambda x: self.c2l['attributs'][x] if x in self.c2l['attributs'] else np.nan)

    def get_adherent_statdb_data_columns(self):
        columns_to_keep = []
        for c in self.adherent_statdb_columns:
            if c in self.df:
                columns_to_keep.append(c)
        self.adherent_statdb_data = self.df[columns_to_keep]

    def get_adherent_es_data_columns(self):
        columns_to_keep = []
        for c in self.adherent_es_columns:
            if c in self.df:
                columns_to_keep.append(c)
        self.adherent_es_data = self.df[columns_to_keep]
