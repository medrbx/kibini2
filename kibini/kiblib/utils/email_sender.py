from email.message import EmailMessage
from email.utils import formatdate
import mimetypes
from pathlib import Path
import smtplib

from kiblib.utils.conf import Config

def send_email(fromaddr, to, subject, content, file=None):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = fromaddr
    msg['To'] = to
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(content)

    if file:
        cfile = Path(file)
        ctype, encoding = mimetypes.guess_type(cfile)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        msg.add_attachment(cfile.read_bytes(), maintype=maintype, subtype=subtype, filename=cfile.name)
    smptp_server = Config().get_config_smtp()
    with smtplib.SMTP(smptp_server) as csmtp:
        csmtp.send_message(msg)

###### Exemple
#subject = 'Un Mail avec Python ééé'
#fromaddr = 'François Pichenot <fpichenot@ville-roubaix.fr>'
#to = ', '.join(['François Pichenot <francois.pichenot@hazpic.fr>', 'François Pichenot <fpichenot@ville-roubaix.fr>'])
#content = """\
#    Salut!
#    Ci joint le fichier demandé.
#    """
#file = 'myfile.txt'
#send_email(fromaddr, to, subject, content, file=file)