import pandas as pd
from os.path import join

from kiblib.utils.db import DbConn
from kiblib.utils.conf import Config
from kiblib.utils.email_sender import send_email

db_conn = DbConn().create_engine()

query = """
SELECT itemnumber
FROM koha_prod.items
WHERE notforloan = 0
    AND ((itemlost = 2 AND YEARWEEK(itemlost_on) < YEARWEEK(CURDATE() - INTERVAL 9 WEEK)) OR (damaged = 2 AND YEARWEEK(damaged_on) < YEARWEEK(CURDATE() - INTERVAL 9 WEEK)))
"""

df = pd.read_sql(query, con=db_conn)
r = len(df)
if r > 0:
    dir_data = Config().get_config_data()
    file_out = join(dir_data, "items_perdus_pretendus_rendus.csv")
    df.to_csv(file_out, header=False, index=False)

    subject = "[Kibini] Exemplaires à sortir des collections (perdus et prétendus rendus)"
    fromaddr = 'PICHENOT François <fpichenot@ville-roubaix.fr>'
    to = ', '.join(['PICHENOT François <fpichenot@ville-roubaix.fr>'])
    content = f"""\
        Exemplaires à sortir des collections.
        Documents passés en perdu ou prétendus rendus depuis plus de 9 semaines.
        {r} documents sont concernés.
        """
    send_email(fromaddr, to, subject, content, file=file_out)
