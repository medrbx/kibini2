import pandas as pd
from os.path import join

from kiblib.utils.db import DbConn
from kiblib.utils.conf import Config
from kiblib.utils.email_sender import send_email

db_conn = DbConn().create_engine()

query = """
SELECT itemnumber, barcode
FROM koha_prod.items
WHERE notforloan = 4 AND itemlost = 0 AND damaged = 0 AND withdrawn != 3 AND timestamp < NOW() - INTERVAL 1 MONTH
"""

df = pd.read_sql(query, con=db_conn)
r = len(df)
if r > 0:
    dir_data = Config().get_config_data()
    file_out = join(dir_data, "items2del.csv")
    df.to_csv(file_out, header=False, index=False)

    subject = "[Kibini] Exemplaires à supprimer (sauf perdus, abîmés, non restitués)"
    fromaddr = 'PICHENOT François <fpichenot@ville-roubaix.fr>'
    to = ', '.join(['PICHENOT François <fpichenot@ville-roubaix.fr>'])
    content = f"""\
        Exemplaires à supprimer.
        Sortis des collections depuis plus d'un mois. Pas abîmés. Pas perdus ni non restitués.
        {r} documents sont concernés.
        """
    send_email(fromaddr, to, subject, content, file=file_out)
