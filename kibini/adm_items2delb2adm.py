import pandas as pd
from os.path import join

from kiblib.utils.db import DbConn
from kiblib.utils.conf import Config
from kiblib.utils.email_sender import send_email

db_conn = DbConn().create_engine()

query = """
SELECT itemnumber
FROM koha_prod.items
WHERE notforloan = 4 AND timestamp < NOW() - INTERVAL 6 MONTH
AND itemnumber NOT IN (SELECT itemnumber FROM koha_prod.issues)
"""

df = pd.read_sql(query, con=db_conn)
r = len(df)
if r > 0:
    dir_data = Config().get_config_data()
    file_out = join(dir_data, "items2del2.csv")
    df.to_csv(file_out, header=False, index=False)

    subject = "[Kibini] Exemplaires à supprimer (tout)"
    fromaddr = 'PICHENOT François <fpichenot@ville-roubaix.fr>'
    to = ', '.join(['PICHENOT François <fpichenot@ville-roubaix.fr>'])
    content = f"""\
        Exemplaires à supprimer.
        Sortis des collections depuis plus de 6 mois, incluant les abîmés, non restitués (pas en prêt) et perdus.
                {r} documents sont concernés.
        """
    send_email(fromaddr, to, subject, content, file=file_out)
