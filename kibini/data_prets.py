import pandas as pd

from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.utils.date import get_date_and_time
from kiblib.utils.log import Log
from kiblib.pret import Pret

log = Log()
log.add_info('Lancement')

date = get_date_and_time('yesterday')

db_conn = DbConn().create_engine()

c2l = Code2Libelle(db_conn)
c2l.get_val()

chunksize = 10000

#####################################################
# insertion issues
log.add_info('insertion issues')

query = """
    SELECT
        iss.issue_id, -- pret_koha_id,
        iss.issuedate, -- pret_date_pret,
        iss.returndate, -- pret_date_retour_effectif,
        iss.date_due, -- pret_date_retour_prevue,
        iss.renewals, -- pret_nb_renouvellement,
        iss.branchcode as issue_branchcode, -- pret_site_pret_code,
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
    FROM koha_prod.issues iss
    LEFT JOIN koha_prod.items i ON i.itemnumber = iss.itemnumber
    LEFT JOIN koha_prod.biblio b ON b.biblionumber = i.biblionumber
    LEFT JOIN koha_prod.biblioitems bi ON bi.biblionumber = i.biblionumber
    LEFT JOIN koha_prod.borrowers bo ON bo.borrowernumber = iss.borrowernumber
    WHERE DATE(iss.issuedate) >= %s
"""

nb_lignes = 0
for df in pd.read_sql(query, params={date}, con=db_conn, chunksize=chunksize):
    if df.empty:
        log.add_info("issues : dataframe vide")
    else:
        pret = Pret(df=df, con=db_conn, c2l=c2l.dict_codes_lib)
        pret.get_pret_statdb_data()
        pret.get_pret_statdb_data_columns()
        pret.add_statdb_pret_data('insert')
        nb_lignes = nb_lignes + len(df.index)

log.add_info(f"{nb_lignes} ajoutées")

#####################################################
# insertion old_issues
log.add_info('insertion old_issues')

query = """
    SELECT
        iss.issue_id, -- pret_koha_id,
        iss.issuedate, -- pret_date,
        iss.returndate, -- pret_date_retour_effectif,
        iss.date_due, -- pret_date_retour_prevue,
        iss.renewals, -- pret_nb_renouvellement,
        iss.branchcode as issue_branchcode, -- pret_site_pret_code,
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
    FROM koha_prod.old_issues iss
    LEFT JOIN koha_prod.items i ON i.itemnumber = iss.itemnumber
    LEFT JOIN koha_prod.biblio b ON b.biblionumber = i.biblionumber
    LEFT JOIN koha_prod.biblioitems bi ON bi.biblionumber = i.biblionumber
    LEFT JOIN koha_prod.borrowers bo ON bo.borrowernumber = iss.borrowernumber
    WHERE DATE(iss.issuedate) >= %s
"""

nb_lignes = 0
for df in pd.read_sql(query, params={date}, con=db_conn, chunksize=chunksize):
    if df.empty:
        log.add_info("old_issues : dataframe vide")
    else:
        pret = Pret(df=df, con=db_conn, c2l=c2l.dict_codes_lib)
        pret.get_pret_statdb_data()
        pret.get_pret_statdb_data_columns()
        pret.add_statdb_pret_data('insert')
        nb_lignes = nb_lignes + len(df.index)

log.add_info(f"{nb_lignes} ajoutées")

#####################################################
# MaJ old_issues
log.add_info('MaJ old issues')

query = """
    SELECT
        iss.issue_id, -- pret_koha_id,
        iss.issuedate, -- pret_date_pret,
        iss.returndate, -- pret_date_retour_effectif,
        iss.date_due, -- pret_date_retour_prevue,
        iss.renewals, -- pret_nb_renouvellement,
        iss.branchcode as issue_branchcode, -- pret_site_pret_code,
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
    FROM koha_prod.old_issues iss
    LEFT JOIN koha_prod.items i ON i.itemnumber = iss.itemnumber
    LEFT JOIN koha_prod.biblio b ON b.biblionumber = i.biblionumber
    LEFT JOIN koha_prod.biblioitems bi ON bi.biblionumber = i.biblionumber
    LEFT JOIN koha_prod.borrowers bo ON bo.borrowernumber = iss.borrowernumber
    WHERE DATE(iss.issuedate) < %s AND DATE(iss.timestamp) >= %s
"""

nb_lignes = 0
for df in pd.read_sql(query, params=(date, date), con=db_conn, chunksize=chunksize):
    if df.empty:
        log.add_info("maj old_issues : dataframe vide")
    else:
        pret = Pret(df=df, con=db_conn, c2l=c2l.dict_codes_lib)
        pret.get_pret_statdb_data()
        pret.get_pret_statdb_data_columns()
        pret.add_statdb_pret_data('update')
        nb_lignes = nb_lignes + len(df.index)

log.add_info(f"{nb_lignes} mises à jour")

#####################################################
# Anonymisation prêts > 1 an
#log.add_info("Anonymisation prêts > 1 an")
#pret = Pret(con=db_conn)
#pret.ano_pret_statdb_data()

log.add_info("Fin traitement\n\n")
