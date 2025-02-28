import pandas as pd
import numpy as np
import datetime
from unidecode import unidecode

from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle

class Document():
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
                    i.itemnumber,
                    i.barcode,
                    i.dateaccessioned,
                    i.price,
                    i.homebranch,
                    i.holdingbranch,
                    i.location,
                    i.ccode,
                    i.itemcallnumber,
                    i.notforloan,
                    i.damaged,
                    DATE(i.damaged_on),
                    i.withdrawn,
                    DATE(i.withdrawn_on),
                    i.itemlost,
                    DATE(i.itemlost_on),
                    i.onloan,
                    i.datelastborrowed,
                    i.datelastseen,
                    i.biblionumber,
                    b.title as titre,
                    bi.publicationyear,
                    bi.itemtype,
                    i.timestamp
                FROM koha_prod.items i
                JOIN koha_prod.biblioitems bi ON i.biblionumber = bi.biblionumber
                JOIN koha_prod.biblio b ON i.biblionumber = b.biblionumber
                LIMIT 10000
            """
            self.df = pd.read_sql(query, con=self.db_conn)

        super(Document, self).__init__()

        # en sortie, on doit obtenir les champs suivants pour statdb :
        self.doc_statdb_columns = [
            'doc_item_id',
            'doc_item_code_barre',
            'doc_item_date_creation',
            'doc_item_prix',
            'doc_item_site_detenteur_code',
            'doc_item_site_rattachement_code',
            'doc_item_localisation_code',
            'doc_item_collection_ccode',
            'doc_item_cote',
            'doc_statut_code',
            'doc_statut_abime_code',
            'doc_statut_abime_date',
            'doc_statut_desherbe_code',
            'doc_statut_desherbe_date',
            'doc_statut_perdu_code',
            'doc_statut_perdu_date',
            'doc_usage_emprunt_date',
            'doc_usage_date_dernier_pret',
            'doc_usage_date_vu_dernier',
            'doc_biblio_id',
            'doc_biblio_auteur'
            'doc_biblio_titre',
            'doc_biblio_auteur',
            'doc_biblio_annee_publication',
            'doc_biblio_support_code',
            'doc_item_pilon_annee',
            'doc_item_pilon_motif',
            'doc_item_date_modif'
        ]

        # en sortie, on doit obtenir les champs suivants pour es :
        self.doc_es_columns = [
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
            'doc_statut_abime_date',
            'doc_statut_desherbe_code',
            'doc_statut_desherbe',
            'doc_statut_desherbe_date',
            'doc_statut_desherbe_annee',
            'doc_statut_perdu_code',
            'doc_statut_perdu',
            'doc_statut_perdu_date',
            'doc_statut_perdu',
            'doc_usage_emprunt_date',
            'doc_usage_date_vu_dernier',
            'doc_usage_emprunt',
            'doc_usage_date_dernier_pret',
            'doc_usage_date_dernier_pret_annee',
            'doc_biblio_id',
            'doc_biblio_auteur'
            'doc_biblio_titre',
            'doc_biblio_volume',
            'doc_biblio_annee_publication',
            'doc_biblio_support_code',
            'doc_biblio_support',
            'doc_item_pilon_annee',
            'doc_item_pilon_motif',
            'doc_item_date_modif'
        ]

    def get_doc_statdb_data(self):
        self.get_doc_item_id()
        self.get_doc_item_code_barre()
        self.get_doc_item_date_creation()
        self.get_doc_item_prix()
        self.get_doc_item_site_detenteur_code()
        self.get_doc_item_site_rattachement_code()
        self.get_doc_item_localisation_code()
        self.get_doc_item_collection_ccode()
        self.get_doc_item_cote()
        self.get_doc_statut_code()
        self.get_doc_statut_abime_code()
        self.get_doc_statut_abime_date()
        self.get_doc_statut_desherbe_code()
        self.get_doc_statut_desherbe_date()
        self.get_doc_statut_perdu_code()
        self.get_doc_statut_perdu_date()
        self.get_doc_usage_emprunt_date()
        self.get_doc_usage_date_dernier_pret()
        self.get_doc_usage_date_vu_dernier()
        self.get_doc_biblio_id()
        self.get_doc_biblio_auteur()
        self.get_doc_biblio_titre()
        self.get_doc_biblio_volume()
        self.get_doc_biblio_annee_publication()
        self.get_doc_biblio_support_code()
        self.get_doc_item_pilon_annee()
        self.get_doc_item_pilon_motif()
        self.get_doc_item_date_modif()

    def get_doc_es_data(self):
        self.get_doc_item_date_creation_annee()
        self.get_doc_item_site_detenteur()
        self.get_doc_item_site_rattachement()
        self.get_doc_item_localisation()
        self.get_doc_item_site_poldoc()
        self.get_doc_item_collection_lib()
        self.get_doc_item_collection_lib1()
        self.get_doc_item_collection_lib2()
        self.get_doc_item_collection_lib3()
        self.get_doc_item_collection_lib4()
        self.get_doc_statut()
        self.get_doc_statut_abime()
        self.get_doc_statut_abime_annee()
        self.get_doc_statut_desherbe()
        self.get_doc_statut_desherbe_annee()
        self.get_doc_statut_perdu()
        self.get_doc_statut_perdu_annee()
        self.get_doc_usage_emprunt()
        self.get_doc_usage_date_dernier_pret_annee()
        self.get_doc_biblio_support()
        self.get_doc_sll_data()

    def get_doc_item_id(self):
        if 'itemnumber' in self.df and 'doc_item_id' not in self.df:
            self.df['doc_item_id'] = self.df['itemnumber']

    def get_doc_item_code_barre(self):
        if ('barcode' in self.df
                and 'doc_item_code_barre' not in self.df):
            self.df['doc_item_code_barre'] = self.df['barcode']

    def get_doc_item_date_creation(self):
        if ('dateaccessioned' in self.df and
                'doc_item_date_creation' not in self.df):
            self.df['doc_item_date_creation'] = self.df['dateaccessioned']

    def get_doc_item_date_creation_annee(self):
        if ('doc_item_date_creation' in self.df and
                'doc_item_date_creation_annee' not in self.df):
            self.df['doc_item_date_creation_annee'] = self.df['doc_item_date_creation'].astype(
                'datetime64[ns]').dt.year

    def get_doc_item_prix(self):
        if 'price' in self.df and 'doc_item_prix' not in self.df:
            self.df['doc_item_prix'] = self.df['price']

    def get_doc_item_site_detenteur_code(self):
        if ('homebranch' in self.df and
                'doc_item_site_detenteur_code' not in self.df):
            self.df['doc_item_site_detenteur_code'] = self.df['homebranch']

    def get_doc_item_site_detenteur(self):
        if ('doc_item_site_detenteur_code' in self.df and
                'doc_item_site_detenteur' not in self.df):
            self.df['doc_item_site_detenteur'] = self.df['doc_item_site_detenteur_code'].apply(
                lambda x: self.c2l['site'][x] if x in self.c2l['site'] else np.nan)

    def get_doc_item_site_rattachement_code(self):
        if ('holdingbranch' in self.df and
                'doc_item_site_rattachement_code' not in self.df):
            self.df['doc_item_site_rattachement_code'] = self.df['holdingbranch']

    def get_doc_item_site_rattachement(self):
        if ('doc_item_site_rattachement_code' in self.df and
                'doc_item_site_rattachement' not in self.df):
            self.df['doc_item_site_rattachement'] = self.df['doc_item_site_rattachement_code'].apply(
                lambda x: self.c2l['site'][x] if x in self.c2l['site'] else np.nan)

    def get_doc_item_localisation_code(self):
        if ('location' in self.df and
                'doc_item_localisation_code' not in self.df):
            self.df['doc_item_localisation_code'] = self.df['location']

    def get_doc_item_localisation(self):
        if ('doc_item_localisation_code' in self.df and
                'doc_item_localisation' not in self.df):
            self.df['doc_item_localisation'] = self.df['doc_item_localisation_code'].apply(
                lambda x: self.c2l['localisation'][x]['lib']
                if x in self.c2l['localisation'] else np.nan)

    def get_doc_item_site_poldoc(self):
        if ('doc_item_localisation_code' in self.df and
                'doc_item_site_poldoc' not in self.df):
            self.df['doc_item_site_poldoc'] = 'Médiathèque'
            self.df.loc[self.df['doc_item_localisation_code'] ==
                        'MED0A', 'doc_item_site_poldoc'] = 'Collectivités'
            self.df.loc[self.df['doc_item_localisation_code']
                        == 'BUS1A', 'doc_item_site_poldoc'] = 'Zèbre'

    def get_doc_item_collection_ccode(self):
        if ('ccode' in self.df and
                'doc_item_collection_ccode' not in self.df):
            self.df['doc_item_collection_ccode'] = self.df['ccode']

    def get_doc_item_collection_lib(self):
        if ('doc_item_collection_ccode' in self.df and
                'doc_item_collection_lib' not in self.df):
            self.df['doc_item_collection_lib'] = self.df['doc_item_collection_ccode'].apply(
                lambda x: self.c2l['ccode'][x]['lib'] if x in self.c2l['ccode'] else np.nan)

    def get_doc_item_collection_lib1(self):
        if ('doc_item_collection_ccode' in self.df and
                'doc_item_collection_lib1' not in self.df):
            self.df['doc_item_collection_lib1'] = self.df['doc_item_collection_ccode'].apply(
                lambda x: self.c2l['ccode'][x]['lib1'] if x in self.c2l['ccode'] else np.nan)

    def get_doc_item_collection_lib2(self):
        if ('doc_item_collection_ccode' in self.df and
                'doc_item_collection_lib2' not in self.df):
            self.df['doc_item_collection_lib2'] = self.df['doc_item_collection_ccode'].apply(
                lambda x: self.c2l['ccode'][x]['lib2'] if x in self.c2l['ccode'] else np.nan)

    def get_doc_item_collection_lib3(self):
        if ('doc_item_collection_ccode' in self.df and
                'doc_item_collection_lib3' not in self.df):
            self.df['doc_item_collection_lib3'] = self.df['doc_item_collection_ccode'].apply(
                lambda x: self.c2l['ccode'][x]['lib3'] if x in self.c2l['ccode'] else np.nan)

    def get_doc_item_collection_lib4(self):
        if ('doc_item_collection_ccode' in self.df and
                'doc_item_collection_lib4' not in self.df):
            self.df['doc_item_collection_lib4'] = self.df['doc_item_collection_ccode'].apply(
                lambda x: self.c2l['ccode'][x]['lib4'] if x in self.c2l['ccode'] else np.nan)

    def get_doc_item_cote(self):
        if ('itemcallnumber' in self.df and
                'doc_item_cote' not in self.df):
            self.df['doc_item_cote'] = self.df['itemcallnumber']

    def get_doc_statut_code(self):
        if ('notforloan' in self.df and
                'doc_statut_code' not in self.df):
            self.df['doc_statut_code'] = self.df['notforloan']

    def get_doc_statut(self):
        if ('doc_statut_code' in self.df and
                'doc_statut' not in self.df):
            self.df['doc_statut'] = self.df['doc_statut_code'].astype('str').apply(
                lambda x: self.c2l['doc_statut'][x]['lib']
                if x in self.c2l['doc_statut'] else np.nan)

    def get_doc_statut_abime_code(self):
        if ('damaged' in self.df and
                'doc_statut_abime_code' not in self.df):
            self.df['doc_statut_abime_code'] = self.df['damaged']

    def get_doc_statut_abime(self):
        if ('doc_statut_abime_code' in self.df and
                'doc_statut_abime' not in self.df):
            self.df['doc_statut_abime'] = self.df['doc_statut_abime_code'].astype('str').apply(
                lambda x: self.c2l['doc_statut_abime'][x]['lib']
                if x in self.c2l['doc_statut_abime'] else np.nan)

    def get_doc_statut_abime_date(self):
        if ('damaged_on' in self.df and
                'doc_statut_abime_date' not in self.df):
            self.df['doc_statut_abime_date'] = self.df['damaged_on']

    def get_doc_statut_abime_annee(self):
        if ('doc_statut_abime_date' in self.df and
                'doc_statut_abime_annee' not in self.df):
            self.df['doc_statut_abime_annee'] = self.df['doc_statut_abime_date'].astype(
                'datetime64[ns]').dt.year

    def get_doc_statut_desherbe_code(self):
        if ('withdrawn' in self.df and
                'doc_statut_desherbe_code' not in self.df):
            self.df['doc_statut_desherbe_code'] = self.df['withdrawn']

    def get_doc_statut_desherbe(self):
        if ('doc_statut_desherbe_code' in self.df and
                'doc_statut_desherbe' not in self.df):
            self.df['doc_statut_desherbe'] = self.df['doc_statut_desherbe_code'].astype('str').apply(
                lambda x: self.c2l['doc_statut_desherbe'][x]['lib']
                if x in self.c2l['doc_statut_desherbe'] else np.nan)

    def get_doc_statut_desherbe_date(self):
        if ('withdrawn_on' in self.df and
                'doc_statut_desherbe_date' not in self.df):
            self.df['doc_statut_desherbe_date'] = self.df['withdrawn_on']

    def get_doc_statut_desherbe_annee(self):
        if ('doc_statut_desherbe_date' in self.df and
                'doc_statut_desherbe_annee' not in self.df):
            self.df['doc_statut_desherbe_annee'] = self.df['doc_statut_desherbe_date'].astype(
                'datetime64[ns]').dt.year

    def get_doc_statut_perdu_code(self):
        if ('itemlost' in self.df and
                'doc_statut_perdu_code' not in self.df):
            self.df['doc_statut_perdu_code'] = self.df['itemlost']

    def get_doc_statut_perdu(self):
        if ('doc_statut_perdu_code' in self.df and
                'doc_statut_perdu' not in self.df):
            self.df['doc_statut_perdu'] = self.df['doc_statut_perdu_code'].astype('str').apply(
                lambda x: self.c2l['doc_statut_perdu'][x]['lib']
                if x in self.c2l['doc_statut_perdu'] else np.nan)

    def get_doc_statut_perdu_date(self):
        if ('itemlost_on' in self.df and
                'doc_statut_perdu_date' not in self.df):
            self.df['doc_statut_perdu_date'] = self.df['itemlost_on']

    def get_doc_statut_perdu_annee(self):
        if ('doc_statut_perdu_date' in self.df and
                'doc_statut_perdu_annee' not in self.df):
            self.df['doc_statut_perdu_annee'] = self.df['doc_statut_perdu_date'].astype(
                'datetime64[ns]').dt.year

    def get_doc_usage_emprunt_date(self):
        if ('onloan' in self.df and
                'doc_usage_emprunt_date' not in self.df):
            self.df['doc_usage_emprunt_date'] = self.df['onloan']

    def get_doc_usage_emprunt(self):
        if ('doc_usage_emprunt_date' in self.df and
                'doc_usage_emprunt' not in self.df):
            self.df['doc_usage_emprunt'] = 'non'
            self.df.loc[self.df['doc_usage_emprunt_date'].astype(
                'str').str.startswith('2'), 'doc_usage_emprunt'] = 'emprunté'

    def get_doc_usage_date_dernier_pret(self):
        if ('datelastborrowed' in self.df and
                'doc_usage_date_dernier_pret' not in self.df):
            self.df['doc_usage_date_dernier_pret'] = self.df['datelastborrowed']

    def get_doc_usage_date_dernier_pret_annee(self):
        if ('doc_usage_date_dernier_pret' in self.df and
                'doc_usage_date_dernier_pret_annee' not in self.df):
            self.df['doc_usage_date_dernier_pret_annee'] = self.df['doc_usage_date_dernier_pret'].astype(
                'datetime64[ns]').dt.year

    def get_doc_usage_date_vu_dernier(self):
        if ('datelastseen' in self.df and 'doc_usage_date_vu_dernier' not in self.df):
            self.df['doc_usage_date_vu_dernier'] = self.df['datelastseen']

    def get_doc_biblio_id(self):
        if ('biblionumber' in self.df and
                'doc_biblio_id' not in self.df):
            self.df['doc_biblio_id'] = self.df['biblionumber']

    def get_doc_biblio_auteur(self):
            if ('author' in self.df and
                    'doc_biblio_auteur' not in self.df):
                self.df['doc_biblio_auteur'] = self.df['author']

    def get_doc_biblio_titre(self):
        if ('titre' in self.df and
                'doc_biblio_titre' not in self.df):
            self.df['doc_biblio_titre'] = self.df['titre']
        if 'doc_biblio_titre' in self.df:
            self.df['doc_biblio_titre'] = self.df['doc_biblio_titre'].astype('str').apply(
                lambda x: unidecode(x))

    def get_doc_biblio_volume(self):
        if ('volume' in self.df and
                'doc_biblio_volume' not in self.df):
            self.df['doc_biblio_volume'] = self.df['volume']
        if ('volume_perio' in self.df and
                'doc_biblio_volume' not in self.df):
            self.df['doc_biblio_volume'] = self.df['volume_perio']

    def get_doc_biblio_annee_publication(self):
        if ('publicationyear' in self.df and
                'doc_biblio_annee_publication' not in self.df):
            self.df['publicationyear'] = self.df['publicationyear'].astype('str')
            self.df['doc_biblio_annee_publication'] = self.df['publicationyear'].str.extract(r'(^\d{4}$)')

    def get_doc_biblio_support_code(self):
        if ('itemtype' in self.df and
                'doc_biblio_support_code' not in self.df):
            self.df['doc_biblio_support_code'] = self.df['itemtype']

    def get_doc_biblio_support(self):
        if ('doc_biblio_support_code' in self.df and
                'doc_biblio_support' not in self.df):
            self.df['doc_biblio_support'] = self.df['doc_biblio_support_code'].astype('str').apply(
                lambda x: self.c2l['doc_biblio_support'][x]['lib']
                if x in self.c2l['doc_biblio_support'] else np.nan)

    def get_doc_item_pilon_annee(self):
        if ('annee_mise_pilon' in self.df and
                'doc_item_pilon_annee' not in self.df):
            self.df['doc_item_pilon_annee'] = self.df['annee_mise_pilon']

    def get_doc_item_pilon_motif(self):
        if ('motif' in self.df and
                'doc_item_pilon_motif' not in self.df):
            self.df['doc_item_pilon_motif'] = self.df['motif']
            
    def get_doc_item_date_modif(self):
        if ('timestamp' in self.df and
                'doc_item_date_modif' not in self.df):
            self.df['doc_item_date_modif'] = self.df['timestamp']
            
    def get_doc_sll_data(self):
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

            # collection et prêts
            self.df['sll_collection'] = 'D1 - Livres imprimés'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["PE"]),
                'sll_collection'] = 'D1 - Publications en série imprimées'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["IC"]),
                'sll_collection'] = 'D3 - Documents graphiques'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["JE"]),
                'sll_collection'] = 'D3 - Autres documents'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["CA"]),
                'sll_collection'] = 'D3 – Documents cartographiques'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["PA"]),
                'sll_collection'] = 'D3 – Musique imprimée'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["LS"])
                & self.df['sll_public'].astype('str').isin(["adultes"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds adultes / Documents sonores : livres enregistrés'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["LS"])
                & self.df['sll_public'].astype('str').isin(["enfants"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds enfants / Documents sonores : livres enregistrés'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["DC", "DV", "DG", "K7"])
                & self.df['sll_public'].astype('str').isin(["adultes"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds adultes / Documents sonores : musique'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["DC", "DV", "DG", "K7"])
                & self.df['sll_public'].astype('str').isin(["enfants"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds enfants / Documents sonores : musique'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["VD", "VI"])
                & self.df['sll_public'].astype('str').isin(["adultes"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds adultes / documents vidéo adultes'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["VD", "VI"])
                & self.df['sll_public'].astype('str').isin(["enfants"]),
                'sll_collection'] = 'D4 - Documents audiovisuels fonds enfants / documents vidéo enfants'

            self.df.loc[self.df['doc_biblio_support_code'].astype('str').isin(["CR", "ML"]),
                'sll_collection'] = 'D4 - Total documents multimédia sur support'


    def get_doc_list_data(self):
        columns_to_keep = [
                    'doc_item_id',
                    'doc_item_code_barre',
                    'doc_item_date_creation',
                    'doc_item_prix',
                    'doc_item_site_detenteur',
                    'doc_item_site_rattachement',
                    'doc_item_localisation',
                    'doc_item_collection_lib',
                    'doc_item_cote',
                    'doc_statut',
                    'doc_statut_abime',
                    'doc_statut_abime_date',
                    'doc_statut_desherbe',
                    'doc_statut_desherbe_date',
                    'doc_statut_perdu',
                    'doc_statut_perdu_date',
                    'doc_usage_date_dernier_pret',
                    'doc_usage_date_vu_dernier',
                    'doc_biblio_id',
                    'doc_biblio_auteur',
                    'doc_biblio_titre',
                    'doc_biblio_volume',
                    'doc_biblio_annee_publication',
                    'doc_biblio_support',
                    'doc_item_date_modif'
                ]
        self.doc_list_data = self.df[columns_to_keep]
