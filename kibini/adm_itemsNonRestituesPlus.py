import pandas as pd
from os.path import join

from kiblib.utils.db import DbConn
from kiblib.utils.conf import Config
from kiblib.utils.email_sender import send_email

db_conn = DbConn().create_engine()

query = """
SELECT i.itemnumber
FROM koha_prod.items i
JOIN koha_prod.issues iss ON iss.itemnumber = i.itemnumber
JOIN koha_prod.borrowers b ON iss.borrowernumber = b.borrowernumber
WHERE i.withdrawn != 3 AND iss.date_due < CURDATE() - INTERVAL 90 DAY AND i.location != 'MED0A'
AND b.categorycode NOT IN ('ECOL', 'CLAS', 'COLS')
"""

df = pd.read_sql(query, con=db_conn)
r = len(df)
print(r)
if r > 0:
    dir_data = Config().get_config_data()
    file_out = join(dir_data, "items_nonRestituesPlus.csv")
    df.to_csv(file_out, header=False, index=False)

    subject = "[Kibini] Exemplaires à passer en 'Retard > 90 jours'"
    fromaddr = 'PICHENOT François <fpichenot@ville-roubaix.fr>'
    to = ', '.join(['PICHENOT François <fpichenot@ville-roubaix.fr>'])
    content = f"""\
        Exemplaires à passer en "0 - Retiré de la circulation ?" : "Retard > 90 jours".
	    Bien laisser le champ "2 - Perdu ?" en "Non restitué".
        Documents avec un retard de plus de 90 jours.
        {r} documents sont concernés.
        """
    send_email(fromaddr, to, subject, content, file=file_out)
