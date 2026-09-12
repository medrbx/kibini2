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

        # en sortie, colonnes attendues par le jeu de données open data publié sur
        # data.lillemetropole.fr ("caracteristiques_des_adherents_a_la_mediatheque_
        # la_grand_plage") - noms et ordre retrouvés par rétro-ingénierie du CSV
        # publié (comparaison de ~2000 lignes avec les compteurs nb_venues_*, voir
        # get_adherent_opendata_data). Le CSV historiquement publié présente une
        # corruption connue sur ~3% des lignes (attribut_inscription /
        # inscription_personnalite / inscription_site_inscription /
        # inscription_type_carte se chevauchent - JSON mal échappé lors d'un export
        # antérieur) : volontairement non reproduite ici, ces colonnes sont
        # recalculées proprement à partir des données statdb/koha.
        self.adherent_opendata_columns = [
            'date_extraction',
            'activite',
            'activite_emprunteur',
            'activite_emprunteur_bus',
            'activite_emprunteur_med',
            'activite_salle_etude',
            'activite_utilisateur_postes_informatiques',
            'activite_utilisateur_wifi',
            'tranches_d_age_1',
            'tranches_d_age_2',
            'roubaisien_ou_non',
            'code_iris_de_roubaix',
            'nom_de_l_iris_a_roubaix',
            'commune_de_residence',
            'attribut_inscription',
            'inscription_attribut_action',
            'inscription_attribut_collectivites',
            'inscription_attribut_zebre',
            'inscription_carte',
            'nombre_d_annees_d_adhesion',
            'type_inscription',
            'inscription_personnalite',
            'inscription_site_inscription',
            'inscription_type_carte',
            'nb_venues',
            'nb_venues_postes_informatiques',
            'nb_venues_prets',
            'nb_venues_prets_bus',
            'nb_venues_prets_mediatheque',
            'nb_venues_salle_etude',
            'nb_venues_wifi',
            'sexe',
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

    def get_adherent_opendata_data(self):
        self.get_adherent_statdb_data()
        self.get_adherent_es_data()
        self.get_opendata_sexe()
        self.get_opendata_nb_venues_prets()
        self.get_opendata_activite_emprunteur()
        self.get_opendata_activite_flags()
        self.get_opendata_activite()

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
            self.df['adh_age'] = self.df['adh_age'].apply(
                lambda x: f"a{int(x)}" if pd.notna(x) else np.nan)
            self.df['adh_age_code'] = self.df['adh_age'].apply(
                lambda x: self.c2l['age'][x]['acode'] if x in self.c2l['age'] else 'NC')
            self.df.loc[self.df['adh_inscription_carte_personnalite_code'] == 'I', 'adh_age_code'] = 'NP'

    def get_age_code_by_age(self):
        if 'adh_age' in self.df and 'adh_age_code' not in self.df:
            self.df['adh_age'] = self.df['adh_age'].apply(
                lambda x: f"a{int(x)}" if pd.notna(x) else np.nan)
            self.df['adh_age_code'] = self.df['adh_age'].apply(
                lambda x: self.c2l['age'][x]['acode'] if x in self.c2l['age'] else 'NC')
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

    def get_opendata_sexe(self):
        """
        adh_sexe_code porte ici la valeur brute statdb.stat_adherents.sexe
        (copiée telle quelle de koha_prod.borrowers.sex par data_adherents.py,
        codes 'M'/'F' - à ne pas confondre avec adh_sexe, dérivé ailleurs de la
        civilité 'title' pour d'autres usages).
        """
        if 'adh_sexe_code' in self.df and 'sexe' not in self.df:
            self.df['sexe'] = self.df['adh_sexe_code'].map(
                {'M': 'Homme', 'F': 'Femme'})

    def get_opendata_nb_venues_prets(self):
        if ('nb_venues_prets_mediatheque' in self.df and
                'nb_venues_prets_bus' in self.df and
                'nb_venues_prets' not in self.df):
            self.df['nb_venues_prets'] = (
                self.df['nb_venues_prets_mediatheque'] +
                self.df['nb_venues_prets_bus'])

    def get_opendata_activite_emprunteur(self):
        if 'nb_venues_prets' in self.df and 'activite_emprunteur' not in self.df:
            self.df['activite_emprunteur'] = self.df['nb_venues_prets'].apply(
                lambda x: 'Emprunteur' if x and x > 0 else 'Non emprunteur')

    def get_opendata_activite_flags(self):
        flags = {
            'nb_venues_prets_mediatheque': (
                'Emprunteur Médiathèque', 'Non emprunteur Médiathèque',
                'activite_emprunteur_med'),
            'nb_venues_prets_bus': (
                'Emprunteur Zèbre', 'Non emprunteur Zèbre',
                'activite_emprunteur_bus'),
            'nb_venues_salle_etude': (
                "Utilisateur Salle d'étude", "Non utilisateur Salle d'étude",
                'activite_salle_etude'),
            'nb_venues_postes_informatiques': (
                'Utilisateur postes informatiques',
                'Non utilisateur postes informatiques',
                'activite_utilisateur_postes_informatiques'),
            'nb_venues_wifi': (
                'Utilisateur Wifi', 'Non utilisateur Wifi',
                'activite_utilisateur_wifi'),
        }
        for source_col, (label_yes, label_no, target_col) in flags.items():
            if source_col in self.df and target_col not in self.df:
                self.df[target_col] = self.df[source_col].apply(
                    lambda x: label_yes if x and x > 0 else label_no)

    def get_opendata_activite(self):
        """
        Libellé composite ('prêt + étude', 'aucune trace'...), retrouvé par
        comparaison avec les compteurs nb_venues_* sur le CSV publié : ordre
        fixe prêt/étude/postes/wifi, jointure par ' + ', 'aucune trace' si rien.
        """
        required = [
            'nb_venues_prets', 'nb_venues_salle_etude',
            'nb_venues_postes_informatiques', 'nb_venues_wifi']
        if 'activite' not in self.df and all(c in self.df for c in required):
            def compose(row):
                parts = []
                if row['nb_venues_prets'] > 0:
                    parts.append('prêt')
                if row['nb_venues_salle_etude'] > 0:
                    parts.append('étude')
                if row['nb_venues_postes_informatiques'] > 0:
                    parts.append('postes')
                if row['nb_venues_wifi'] > 0:
                    parts.append('wifi')
                return ' + '.join(parts) if parts else 'aucune trace'
            self.df['activite'] = self.df.apply(compose, axis=1)

    def get_adherent_opendata_data_columns(self):
        rename_map = {
            'adh_geo_gentilite': 'roubaisien_ou_non',
            'adh_geo_rbx_iris_code': 'code_iris_de_roubaix',
            'adh_geo_rbx_iris': 'nom_de_l_iris_a_roubaix',
            'adh_geo_ville': 'commune_de_residence',
            'adh_age_lib1': 'tranches_d_age_1',
            'adh_age_lib2': 'tranches_d_age_2',
            'adh_inscription_nb_annees_adhesion': 'nombre_d_annees_d_adhesion',
            'adh_inscription_carte_gratuite': 'type_inscription',
            'adh_inscription_carte_personnalite': 'inscription_personnalite',
            'adh_inscription_site': 'inscription_site_inscription',
            'adh_inscription_carte_type': 'inscription_type_carte',
            'adh_inscription_attribut_pcs': 'attribut_inscription',
            'adh_inscription_attribut_action': 'inscription_attribut_action',
            'adh_inscription_attribut_collect': 'inscription_attribut_collectivites',
            'adh_inscription_attribut_bus': 'inscription_attribut_zebre',
        }
        df = self.df.rename(columns=rename_map)
        # colonnes manquantes forcées à vide plutôt qu'omises, pour garder le
        # même schéma (nombre et ordre de colonnes) que le CSV publié sur
        # data.lillemetropole.fr. Cas actuel : quand self.df vient de
        # statdb.stat_adherents seul (ex. stat_adh2oa.py), les 4 colonnes
        # inscription_attribut_*/attribut_inscription restent vides - la table
        # ne conserve pas borrowernumber, nécessaire pour que
        # get_inscription_attributs_code() rejoigne
        # koha_prod.borrower_attributes. Ce n'est pas une limite du mapping
        # lui-même : quand borrowernumber est disponible en entrée (comme dans
        # data/adherents_2015-2025.csv.gz), ces 4 colonnes se remplissent
        # normalement.
        for c in self.adherent_opendata_columns:
            if c not in df:
                df[c] = None
        self.adherent_opendata_data = df[self.adherent_opendata_columns]

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
