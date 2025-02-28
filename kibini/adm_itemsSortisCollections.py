import pandas as pd
from os.path import join

from kiblib.utils.db import DbConn
from kiblib.utils.conf import Config
from kiblib.utils.email_sender import send_email

db_conn = DbConn().create_engine()

query = """
SELECT
    av.lib AS "Espace",
    i.itemcallnumber AS "Cote",
    i.barcode AS "Code-barre",
    b.author AS "Auteur",
    b.title AS "Titre",
    ExtractValue(m.metadata, '//datafield[@tag="200"]/subfield[@code="h"]') AS "Volume",
    i.copynumber AS "Volume perios",
	i.itemlost,
    DATE(i.timestamp) AS "Date derniere modif"
FROM koha_prod.items i
LEFT JOIN koha_prod.biblio b ON i.biblionumber = b.biblionumber
LEFT JOIN koha_prod.biblioitems bi ON i.biblionumber = bi.biblionumber
LEFT JOIN koha_prod.biblio_metadata m ON m.biblionumber = bi.biblionumber
LEFT JOIN koha_prod.authorised_values av ON av.authorised_value = i.location
WHERE i.notforloan = 4 
AND i.itemlost != 0
AND DATE(i.timestamp) >= CURDATE() - INTERVAL 6 MONTH
ORDER BY i.location, i.itemcallnumber
"""

df = pd.read_sql(query, con=db_conn)
r = len(df)
if r > 0:
    dir_data = Config().get_config_data()
    file_out = join(dir_data, "sortisCollectionsPerdus.xlsx")
    df.to_excel(file_out, header=True, index=False)

    subject = "[Kibini] Documents sortis des collections (perdus, non restitués)"
    fromaddr = 'PICHENOT François <fpichenot@ville-roubaix.fr>'
    to = ', '.join(['PICHENOT François <fpichenot@ville-roubaix.fr>'])
	#acquereurs = Config().get_config_acquereurs()
	#courriels = [f"{acquereur['courriel']}@ville-roubaix.fr" for acquereur in acquereurs]
	#to = ', '.join(courriels)

    content = f"""\
        Documents sortis des collections au cours des 30 derniers jours car perdus ou non restitués.
        {r} documents concernés.
        """
    send_email(fromaddr, to, subject, content, file=file_out)
