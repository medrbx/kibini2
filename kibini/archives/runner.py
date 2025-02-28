from kiblib.utils.db import DbConn
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.document import Document
from kiblib.adherent import Adherent
from kiblib.pret import Pret

import pandas as pd

engine = DbConn().create_db_con()
c2l = Code2Libelle(engine)
c2l.get_val()
#print(va.val_aut)
#print(c2l.dict_codes_lib['age'])
#doc = Document(engine=engine, va=va.val_aut)#df=None, engine=engine, va=va.val_aut)
#doc.get_doc_statdb_data()
#doc.get_doc_es_data()
#print(doc.df['doc_biblio_support'].value_counts())

#adh = Adherent()
#adh.get_adherent_statdb_data()
#adh.get_adherent_es_data()
#print(adh.df)

query = """
                SELECT
	                iss.issue_id, -- pret_id,
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
                ORDER BY iss.issue_id DESC
                LIMIT 1000
                """
df = pd.read_sql(query, con=engine)

pret = Pret(df=df, engine=engine, c2l=c2l.dict_codes_lib)
#pret.get_pret_statdb_data()
#pret.add_pret_data()
#pret.get_pret_es_data()
#print(pret.df.columns)
#print(pret.pret_statdb_data.columns)
#pret.pret_es_data.to_csv("test.csv", index=False)
#print(c2l.dict_codes_lib)
