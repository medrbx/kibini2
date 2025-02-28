import pandas as pd
import numpy as np
from os.path import join

from kiblib.utils.db import DbConn
from kiblib.utils.conf import Config
from kiblib.utils.email_sender import send_email
from kiblib.utils.code2libelle import Code2Libelle
from kiblib.document import Document

db_conn = DbConn().create_engine()
c2l = Code2Libelle(db_conn)
c2l.get_val()

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
    i.damaged_on,
    i.withdrawn,
    i.withdrawn_on,
    i.itemlost,
    i.itemlost_on,
    i.onloan,
    i.datelastborrowed,
    i.biblionumber,
    b.title as titre,
    b.author,
    ExtractValue(m.metadata, '//datafield[@tag="200"]/subfield[@code="h"]') AS "volume",
    i.copynumber AS "volume_perio",
    bi.publicationyear,
    bi.itemtype,
    i.timestamp
FROM koha_prod.items i
JOIN koha_prod.biblioitems bi ON i.biblionumber = bi.biblionumber
JOIN koha_prod.biblio b ON i.biblionumber = b.biblionumber
JOIN koha_prod.biblio_metadata m ON m.biblionumber = bi.biblionumber
WHERE i.notforloan = 4
    AND (i.itemlost != 0 OR i.damaged = 2)
	AND DATE(i.timestamp) >= CURDATE() - INTERVAL 1 MONTH
ORDER BY i.location, i.itemcallnumber
"""

df0 = pd.read_sql(query, con=db_conn)
document = Document(df=df0, con=db_conn, c2l=c2l.dict_codes_lib)
document.get_doc_statdb_data()
document.get_doc_es_data()
document.get_doc_list_data()
df = document.doc_list_data

query = """
SELECT
    biblionumber, "oui" as "réservation"
FROM koha_prod.reserves
WHERE waitingdate IS NULL
"""
resa = pd.read_sql(query, con=db_conn)
df = df.merge(resa, how='left', left_on='doc_biblio_id', right_on='biblionumber')
df = df.drop(columns=['biblionumber'])
df.loc[df['doc_item_localisation'] == 'Magasin collectivités', 'réservation'] = np.nan



df = df.rename(columns={
	"doc_item_code_barre": "code-barres",
	"doc_item_date_creation": "création",
	"doc_item_prix": "prix",
	"doc_item_site_detenteur": "site actuel",
	"doc_item_site_rattachement": "site de rattachement",
	"doc_item_localisation": "localisation",
	"doc_item_collection_lib": "collection",
	"doc_item_cote": "cote",
	"doc_statut": "statut",
	"doc_statut_abime": "abîmé ?",
	"doc_statut_abime_date": "date abîmé",
	"doc_statut_desherbe": "désherbé ?",
	"doc_statut_desherbe_date": "date désherbé",
	"doc_statut_perdu": "perdu ?",
	"doc_statut_perdu_date": "date perdu",
	"doc_usage_date_dernier_pret": "dernier prêt",
	"doc_biblio_id": "biblionumber",
	"doc_biblio_auteur": "auteur",
	"doc_biblio_titre": "titre",
	"doc_biblio_volume": "volume",
	"doc_biblio_annee_publication": "année",
	"doc_biblio_support": "support",
	"réservation": "réservation"
})

r = len(df)
if r > 0:
    dir_data = Config().get_config_data()
    file_out = join(dir_data, "sortisCollectionsPerdus.xlsx")
    df.to_excel(file_out, header=True, index=False)

    subject = "[Kibini] Documents sortis des collections (perdus, non restitués, prétendus rendus)"
    fromaddr = 'PICHENOT François <fpichenot@ville-roubaix.fr>'
    to = ', '.join(['PICHENOT François <fpichenot@ville-roubaix.fr>'])
    #acquereurs = Config().get_config_acquereurs()
    #courriels = [f"{acquereur['courriel']}@ville-roubaix.fr" for acquereur in acquereurs]
    #to = ', '.join(courriels)

    content = f"""\
        Documents perdus ou non restitués au cours du mois précédent.
        {r} documents concernés.
    """
    send_email(fromaddr, to, subject, content, file=file_out)
