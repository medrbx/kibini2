import pandas as pd
from os.path import join

from kiblib.utils.db import DbConn
from kiblib.utils.conf import Config
from kiblib.utils.email_sender import send_email

db_conn = DbConn().create_engine()

query = """
SELECT i.itemnumber
FROM koha_prod.issues iss
JOIN koha_prod.items i ON iss.itemnumber = i.itemnumber
JOIN koha_prod.borrowers bo ON bo.borrowernumber = iss.borrowernumber
WHERE iss.date_due < DATE_SUB(NOW(), INTERVAL 180 DAY) AND bo.categorycode NOT IN ('ECOL', 'CLAS', 'COLS') AND i.notforloan = 0 AND i.itemlost = 1
ORDER BY date_due
"""

df = pd.read_sql(query, con=db_conn)
r = len(df)
if r > 0:
    dir_data = Config().get_config_data()
    file_out = join(dir_data, "retards.csv")
    df.to_csv(file_out, header=False, index=False)

    subject = "[Kibini] Retards 180 jours"
    fromaddr = 'PICHENOT François <fpichenot@ville-roubaix.fr>'
    to = ', '.join(['PICHENOT François <fpichenot@ville-roubaix.fr>'])
    content = f"""\
        Documents en retard depuis plus de 180 jours, à sortir des collections.
                {r} documents concernés.
        """
    send_email(fromaddr, to, subject, content, file=file_out)
