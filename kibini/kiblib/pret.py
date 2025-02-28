import pandas as pd
import numpy as np
import datetime

from kiblib.adherent import Adherent
from kiblib.document import Document
from kiblib.utils.es import Pd2Es
from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.utils.date import get_date_and_time, dfcol_split_datetime
from kiblib.utils.zebre import get_zebre_stop_by_datetime


class Pret(Adherent, Document):
    def __init__(self, **kwargs):
        if 'db_conn' in kwargs:
            self.db_conn = kwargs.get('db_conn')
        else:
            self.db_conn = DbConn().create_engine()

        if 'c2l' in kwargs:
            self.c2l = kwargs.get('c2l')
        #else:
        #    c2l = Code2Libelle(self.db_conn)
        #    c2l.get_val()
        #    self.c2l = c2l.dict_codes_lib

        if 'statdb_table' in kwargs:
            self.statdb_pret_table = kwargs.get('statdb_table')
        else:
            self.statdb_pret_table = 'stat_prets'

        if 'df' in kwargs:
            self.df = kwargs.get('df')
        else:
            query = """
                SELECT
                    -- iss.issue_id, -- pret_koha_id,
                    iss.issuedate, -- pret_date,
                    iss.returndate, -- pret_date_retour_effectif,
                    iss.date_due, -- pret_date_retour_prevue,
                    iss.renewals, -- pret_nb_renouvellement,
                    iss.branchcode as issue_branchcode , -- pret_site_pret_code,
                    iss.borrowernumber, -- adh_id,
                    bo.title, -- adh_sexe_code,
                    bo.dateofbirth, -- adh_age_code,
                    bo.city, -- adh_geo_ville,
                    bo.altcontactcountry, -- adh_geo_rbx_iris_code,
                    bo.categorycode , -- adh_inscription_carte_code,
                    bo.branchcode , -- adh_inscription_site_code,
                    bo.dateenrolled , -- adh_inscription_nb_annees_adhesion,
                    i.biblionumber , -- doc_biblio_id,
                    b.title as titre, -- doc_biblio_titre,
                    bi.itemtype, -- doc_biblio_support_code,
                    bi.publicationyear, -- doc_biblio_annee_publication,
                    iss.itemnumber, -- doc_item_id,
                    i.barcode, -- doc_item_code_barre,
                    i.ccode, -- doc_item_collection_ccode,
                    i.homebranch, -- doc_item_site_detenteur_code,
                    i.location, -- doc_item_localisation_code,
                    i.itemcallnumber, -- doc_item_cote,
                    i.dateaccessioned -- doc_item_date_creation
                FROM koha2019.old_issues iss
                LEFT JOIN koha2019.items i ON i.itemnumber = iss.itemnumber
                LEFT JOIN koha2019.biblio b ON b.biblionumber = i.biblionumber
                LEFT JOIN koha2019.biblioitems bi ON bi.biblionumber = i.biblionumber
                LEFT JOIN koha2019.borrowers bo ON bo.borrowernumber = iss.borrowernumber
                ORDER BY iss.issue_id DESC
                LIMIT 1000
                """
            #self.df = pd.read_sql(query, con=self.db_conn)

        #super(Pret, self).__init__(**kwargs)

        # en sortie, on doit obtenir les champs suivants pour statdb :
        self.pret_statdb_columns = [
            'pret_koha_id',
            'pret_date_pret',
            'pret_date_retour_effectif',
            'pret_date_retour_prevue',
            'pret_nb_renouvellement',
            'pret_site_pret_code',
            'pret_bus_arret_code',
            'pret_site_retour_code',
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
            'adh_inscription_attribut_pcs_code',
            'doc_biblio_id',
            'doc_biblio_titre',
            'doc_biblio_support_code',
            'doc_biblio_annee_publication',
            'doc_item_id',
            'doc_item_code_barre',
            'doc_item_collection_ccode',
            'doc_item_site_detenteur_code',
            'doc_item_localisation_code',
            'doc_item_cote',
            'doc_item_date_creation'
        ]

        # en sortie, on doit obtenir les champs suivants pour statdb :
        self.pret_es_columns = [
            'pret_id',
            'pret_koha_id',
            'pret_date_pret',
            'pret_date_pret_annee',
            'pret_date_pret_heure',
            'pret_date_pret_jour',
            'pret_date_pret_jour_semaine',
            'pret_date_pret_mois',
            'pret_date_pret_semaine',
            'pret_date_retour_effectif',
            'pret_date_retour_effectif_annee',
            'pret_date_retour_effectif_heure',
            'pret_date_retour_effectif_jour',
            'pret_date_retour_effectif_jour_semaine',
            'pret_date_retour_effectif_mois',
            'pret_date_retour_effectif_semaine',
            'pret_date_retour_prevue',
            'pret_nb_renouvellement',
            'pret_site_pret_code',
            'pret_site_pret',
            'pret_bus_arret_code',
            'pret_bus_arret',
            'pret_site_retour_code',
            'pret_site_retour',
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
            'adh_inscription_attribut_pcs',
            'doc_item_id',
            'doc_item_code_barre',
            'doc_item_date_creation',
            'doc_item_date_creation_annee',
            'doc_item_prix',
            'doc_item_site_detenteur_code',
            'doc_item_site_detenteur',
            'doc_item_site_rattachement_code',
            'doc_item_site_rattachement',
            'doc_item_localisation_code',
            'doc_item_localisation',
            'doc_item_site_poldoc',
            'doc_item_collection_ccode',
            'doc_item_collection_lib',
            'doc_item_collection_lib1',
            'doc_item_collection_lib2',
            'doc_item_collection_lib3',
            'doc_item_collection_lib4',
            'doc_item_cote',
            'doc_statut_code',
            'doc_statut',
            'doc_statut_abime_code',
            'doc_statut_abime',
            'doc_statut_desherbe_code',
            'doc_statut_desherbe',
            'doc_statut_desherbe_date',
            'doc_statut_desherbe_annee',
            'doc_statut_perdu_code',
            'doc_statut_perdu',
            'doc_statut_perdu_date',
            'doc_statut_perdu',
            'doc_usage_emprunt_date',
            'doc_usage_emprunt',
            'doc_usage_date_dernier_pret',
            'doc_usage_date_dernier_pret_annee',
            'doc_biblio_id',
            'doc_biblio_titre',
            'doc_biblio_annee_publication',
            'doc_biblio_support_code',
            'doc_biblio_support',
            'doc_item_pilon_annee',
            'doc_item_pilon_motif',
            'sll_acces',
            'sll_collection',
            'sll_prets',
            'sll_prets_coll',
            'sll_public'
        ]



    def get_pret_statdb_data(self):
        self.get_adherent_statdb_data()
        self.get_doc_statdb_data()
        self.get_pret_koha_id()
        self.get_pret_date_pret()
        self.get_pret_date_retour_effectif()
        self.get_pret_date_retour_prevue()
        self.get_pret_nb_renouvellement()
        self.get_pret_site_pret_code()
        self.get_pret_bus_arret_code()
        self.get_pret_site_retour_code()
        self.get_pret_statdb_data_columns()

    def get_pret_es_data(self):
        self.get_adherent_es_data()
        self.get_doc_es_data()
        self.get_pret_date_pret_det()
        self.get_pret_date_retour_effectif_det()
        self.get_pret_site_pret()
        self.get_pret_bus_arret()
        self.get_pret_site_retour()
        self.get_pret_sll_data()
        self.get_pret_es_data_columns()

    def get_pret_koha_id(self):
        if ('issue_id' in self.df and
                'pret_koha_id' not in self.df):
            self.df['pret_koha_id'] = self.df['issue_id']

    def get_pret_date_pret(self):
        if ('issuedate' in self.df and
                'pret_date_pret' not in self.df):
            self.df['pret_date_pret'] = self.df['issuedate']

    def get_pret_date_pret_det(self):
        if 'pret_date_pret' in self.df:
            self.df = dfcol_split_datetime(self.df, 'pret_date_pret')

    def get_pret_date_retour_effectif(self):
        if ('returndate' in self.df and
                'pret_date_retour_effectif' not in self.df):
            self.df['pret_date_retour_effectif'] = self.df['returndate']

    def get_pret_date_retour_effectif_det(self):
        if 'pret_date_retour_effectif' in self.df:
            self.df = dfcol_split_datetime(self.df, 'pret_date_retour_effectif')

    def get_pret_date_retour_prevue(self):
        if ('date_due' in self.df and
                'pret_date_retour_prevue' not in self.df):
            self.df['pret_date_retour_prevue'] = self.df['date_due']

    def get_pret_nb_renouvellement(self):
        if ('renewals' in self.df and
                'pret_nb_renouvellement' not in self.df):
            self.df['pret_nb_renouvellement'] = self.df['renewals'].fillna(0)

    def get_pret_site_pret_code(self):
        if ('issue_branchcode' in self.df and
                'pret_site_pret_code' not in self.df):
            self.df['pret_site_pret_code'] = self.df['issue_branchcode']

    def get_pret_site_pret(self):
        if ('pret_site_pret_code' in self.df and
                'pret_site_pret' not in self.df):
            self.df['pret_site_pret'] = self.df['pret_site_pret_code'].apply(
                lambda x: self.c2l['site'][x] if x in self.c2l['site'] else np.nan)

    def get_pret_bus_arret_code(self):
        if ('pret_site_pret_code' in self.df and
                'pret_date_pret' in self.df and
                          'pret_bus_arret_code' not in self.df):
            self.df['pret_bus_arret_code'] = self.df.apply(lambda x: get_zebre_stop_by_datetime(x['pret_date_pret']) if x['pret_site_pret_code'] == 'BUS' else np.nan, axis=1)

    def get_pret_bus_arret(self):
        if ('pret_bus_arret_code' in self.df and
                'pret_bus_arret' not in self.df):
            self.df['pret_bus_arret'] = self.df['pret_bus_arret_code'].apply(
                lambda x: self.c2l['attributs'][x] if x in self.c2l['attributs'] else np.nan)

    def get_pret_site_retour_code(self):
        if ('returnbranch' in self.df and
                'pret_site_retour_code' not in self.df):
            self.df['pret_site_retour_code'] = self.df['returnbranch']

    def get_pret_site_retour(self):
        if ('pret_site_retour_code' in self.df and
                'pret_site_retour' not in self.df):
            self.df['pret_site_retour'] = self.df['pret_site_retour_code'].apply(
                lambda x: self.c2l['site'][x] if x in self.c2l['site'] else np.nan)

    def get_pret_sll_data(self):
        if ('doc_item_collection_ccode' in self.df
                and 'doc_item_localisation_code' in self.df
                and 'doc_biblio_support_code' in self.df):
            # public
            jeunesse = ["A143", "A144", "E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08", "E09", "E10", "E11", "E12", "E13", "E14", "E15", "E16", "E17", "E18", "E19", "E20", "E21", "E22", "E23", "E24", "E25", "E26", "E27"]
            self.df['sll_public'] = 'adultes'
            self.df.loc[self.df['doc_item_collection_ccode'].astype('str').str.startswith(
                'J'), 'sll_public'] = 'enfants'
            self.df.loc[self.df['doc_item_collection_ccode'].astype('str').isin(jeunesse),
                'sll_public'] = 'enfants'
            self.df.loc[self.df['doc_item_collection_ccode'].astype('str').isin(["P17"])
                & self.df['doc_item_localisation_code'].astype('str').isin(["MED2A"]),
                'sll_public'] = 'enfants'

            # libre-accès
            libre_acces_loc = ["BUS1A", "MED0B", "MED0C", "MED1A", "MED2A", "MED2B", "MED3A", "MED3B"]
            self.df['sll_acces'] = 'accès indirect'
            self.df.loc[self.df['doc_item_localisation_code'].astype('str').isin(libre_acces_loc),
                'sll_acces'] = 'accès direct'

            # prets aux collectivités
            self.df['sll_prets_coll'] = 'Pas de prêt aux collectivités'
            self.df.loc[self.df['doc_item_localisation_code'].astype('str').isin(['MED0A']),
                'sll_prets_coll'] = 'Prêt aux collectivités'

            # collection et prêts
            self.df['sll_collection'] = 'D1 - Livres imprimés'
            self.df['sll_prets'] = 'E2 - Livres'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["PE"]),
                'sll_collection'] = 'D1 - Publications en série imprimées'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["PE"]),
                'sll_prets'] = 'E2 – Publications en série imprimées'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["IC"]),
                'sll_collection'] = 'D3 - Documents graphiques'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["IC"]),
                'sll_prets'] = 'Autres documents'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["JE"]),
                'sll_collection'] = 'D3 - Autres documents'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["JE"]),
                'sll_prets'] = 'Autres documents'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["CA"]),
                'sll_collection'] = 'D3 – Documents cartographiques'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["CA"]),
                'sll_prets'] = 'Autres documents'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["PA"]),
                'sll_collection'] = 'D3 – Musique imprimée'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["PA"]),
                'sll_prets'] = 'Autres documents'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["LS"])
                & self.df['sll_public'].astype('str').isin(["adultes"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds adultes / Documents sonores : livres enregistrés'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["LS"])
                & self.df['sll_public'].astype('str').isin(["adultes"]),
                'sll_prets'] = 'E2 – Documents sonores : livres'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["LS"])
                & self.df['sll_public'].astype('str').isin(["enfants"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds enfants / Documents sonores : livres enregistrés'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["LS"])
                & self.df['sll_public'].astype('str').isin(["enfants"]),
                'sll_prets'] = 'E2 – Documents sonores : livres'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["DC", "DV", "DG", "K7"])
                & self.df['sll_public'].astype('str').isin(["adultes"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds adultes / Documents sonores : musique'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["DC", "DV", "DG", "K7"])
                & self.df['sll_public'].astype('str').isin(["adultes"]),
                'sll_prets'] = 'E2 – Documents sonores : musique'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["DC", "DV", "DG", "K7"])
                & self.df['sll_public'].astype('str').isin(["enfants"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds enfants / Documents sonores : musique'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["DC", "DV", "DG", "K7"])
                & self.df['sll_public'].astype('str').isin(["enfants"]),
                'sll_prets'] = 'E2 – Documents sonores : musique'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["VD", "VI"])
                & self.df['sll_public'].astype('str').isin(["adultes"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds adultes / documents vidéo adultes'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["VD", "VI"])
                & self.df['sll_public'].astype('str').isin(["adultes"]),
                'sll_prets'] = 'E2 - Documents vidéo'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["VD", "VI"])
                & self.df['sll_public'].astype('str').isin(["enfants"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds enfants / documents vidéo enfants'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["VD", "VI"])
                & self.df['sll_public'].astype('str').isin(["enfants"]),
                'sll_prets'] = 'E2 - Documents vidéo'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["CR", "ML"]),
                'sll_collection'] = 'D4 - Total documents multimédia sur support'
            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["CR", "ML"]),
                'sll_prets'] = 'Autres documents'




    def get_pret_statdb_data_columns(self):
        columns_to_keep = []
        for c in self.pret_statdb_columns:
            if c in self.df:
                columns_to_keep.append(c)
        self.pret_statdb_data = self.df[columns_to_keep]

    def add_statdb_pret_data(self, todo):
        to_sql_conn = DbConn().create_engine()
        if todo == 'insert':
            self.pret_statdb_data.to_sql(self.statdb_pret_table, con=to_sql_conn, if_exists='append', index=False)
        elif todo == 'update':
            table_tmp = self.statdb_pret_table + "_tmp"
            self.pret_statdb_data.to_sql(table_tmp, con=to_sql_conn, if_exists='replace', index=False)
            query = """
                UPDATE $table p
                JOIN $table_tmp t ON p.pret_koha_id = t.pret_koha_id
                SET
                    -- p.pret_date_pret = t.pret_date_pret,
                    p.pret_date_retour_effectif = t.pret_date_retour_effectif,
                    p.pret_date_retour_prevue = t.pret_date_retour_prevue,
                    p.pret_nb_renouvellement = t.pret_nb_renouvellement,
                    -- p.pret_site_pret_code = t.pret_site_pret_code,
                    -- p.pret_bus_arret_code = t.pret_bus_arret_code,
                    -- p.pret_site_retour_code = t.pret_site_retour_code, -- colonne qui n'existe pas
                    -- p.adh_id = t.adh_id,
                    -- p.adh_sexe_code = t.adh_sexe_code,
                    -- p.adh_age_code = t.adh_age_code,
                    p.adh_geo_ville = t.adh_geo_ville,
                    p.adh_geo_rbx_iris_code = t.adh_geo_rbx_iris_code,
                    -- p.adh_inscription_carte_code = t.adh_inscription_carte_code,
                    -- p.adh_inscription_site_code = t.adh_inscription_site_code,
                    -- p.adh_inscription_carte_personnalite_code = t.adh_inscription_carte_personnalite_code,
                    -- p.adh_inscription_nb_annees_adhesion = t.adh_inscription_nb_annees_adhesion,
                    -- p.adh_inscription_attribut_action_code = t.adh_inscription_attribut_action_code,
                    -- p.adh_inscription_attribut_bus_code = t.adh_inscription_attribut_bus_code,
                    -- p.adh_inscription_attribut_collect_code = t.adh_inscription_attribut_collect_code,
                    -- p.adh_inscription_attribut_pcs_code = t.adh_inscription_attribut_pcs_code,
                    -- p.doc_biblio_id = t.doc_biblio_id,
                    -- p.doc_biblio_titre = t.doc_biblio_titre,
                    -- p.doc_biblio_support_code = t.doc_biblio_support_code,
                    -- p.doc_biblio_annee_publication = t.doc_biblio_annee_publication,
                    -- p.doc_item_id = t.doc_item_id,
                    -- p.doc_item_code_barre = t.doc_item_code_barre,
                    -- p.doc_item_collection_ccode = t.doc_item_collection_ccode,
                    -- p.doc_item_site_detenteur_code = t.doc_item_site_detenteur_code,
                    -- p.doc_item_localisation_code = t.doc_item_localisation_code,
                    -- p.doc_item_cote = t.doc_item_cote,
                    p.doc_item_date_creation = t.doc_item_date_creation

            """
            query = query.replace("$table", self.statdb_pret_table)
            con = DbConn().create_db_con()
            cur = con.cursor()
            cur.execute(query)
            con.commit()

    def ano_pret_statdb_data(self):
        query= """
            UPDATE $table
            SET adh_id = null
            WHERE DATE(pret_date_pret) < CURDATE() - INTERVAL 1 YEAR
        """
        query = query.replace("$table", self.statdb_pret_table)
        con = DbConn().create_db_con()
        cur = con.cursor()
        cur.execute(query)
        con.commit()

    def get_pret_es_data_columns(self):
        columns_to_keep = []
        for c in self.pret_es_columns:
            if c in self.df:
                columns_to_keep.append(c)
        self.pret_es_data = self.df[columns_to_keep]

    def add_es_pret_data(self):
        pd2es = Pd2Es()
        pd2es.es_write(self.pret_es_data, "prets2020", "prets", uid_name='pret_id')
