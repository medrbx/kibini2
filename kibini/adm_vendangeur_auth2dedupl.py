import re
from os.path import join

from kiblib.utils.email_sender import send_email
from kiblib.utils.conf import Config
from kiblib.utils.date import get_date_and_time

today = get_date_and_time('today')

dir_webdav = Config().get_config_webdav()
file = join(dir_webdav, "vendangeur", "to_dedupl.txt")

arks_to_dedupl = []

with open(file, 'r') as f:
    logs = f.readlines()

for log in logs:
    log_date = log[30:40]
    if log_date == today:
        arks = re.findall(r'(/ark:/12148/cb\w*)\.', log)
        if len(arks) > 0:
            ark = 'https://catalogue.bnf.fr' + arks[0]
            arks_to_dedupl.append(ark)
            
#for log in logs:
#    year = log[30:34]
#    if year == year_today:
#        month = log[35:37]
#        month = month.lstrip("0")
#        if month == month_today:
#            arks = re.findall(r'(/ark:/12148/cb\w*)\.', log)
#            if len(arks) > 0:
#                ark = 'https://catalogue.bnf.fr' + arks[0]
#                arks_to_dedupl.append(ark)
                
r = len(arks_to_dedupl)

if r > 0:
    subject = "[Kibini] Vendangeur : autorités à dédoublonner"
    fromaddr = 'PICHENOT François <fpichenot@ville-roubaix.fr>'
    to = ', '.join(['PICHENOT François <fpichenot@ville-roubaix.fr>'])
    arks_to_print = "\n".join(arks_to_dedupl)
    content = f"""
    Autorités à dédoublonner.
    {r} autorités sont concernées.
        
    {arks_to_print}
    """
    send_email(fromaddr, to, subject, content)
