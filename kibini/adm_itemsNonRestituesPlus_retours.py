import pandas as pd
from os.path import join

from kiblib.utils.db import DbConn
from kiblib.utils.conf import Config
from kiblib.utils.email_sender import send_email

db_conn = DbConn().create_engine()

query = """
SELECT b.cardnumber, i.barcode, i.itemnumber, iss.returndate, i.notforloan, i.withdrawn, i.itemlost
FROM  koha_prod.old_issues iss
LEFT JOIN koha_prod.items i ON iss.itemnumber = i.itemnumber
LEFT JOIN koha_prod.borrowers b ON iss.borrowernumber = b.borrowernumber
WHERE DATE(iss.returndate) = CURDATE() - INTERVAL 1 DAY AND DATE(iss.date_due) < CURDATE() - INTERVAL 90 DAY
AND i.location != 'MED0A'
"""

items = pd.read_sql(query, con=db_conn)
r = len(items)
if r > 0:
    dir_data = Config().get_config_data()
    file_out = join(dir_data, "items_nonRestituesPlus_retours.xlsx")
    items.to_excel(file_out, header=True, index=False)

    subject = "[Kibini] Exemplaires 'Retard > 90 jours' rendus la veille"
    fromaddr = 'PICHENOT François <fpichenot@ville-roubaix.fr>'
    to = ', '.join(['PICHENOT François <fpichenot@ville-roubaix.fr>'])
    content = f"""\
        Exemplaires 'Retard > 90 jours' rendus la veille
        {r} documents sont concernés.
        """
    send_email(fromaddr, to, subject, content, file=file_out)
