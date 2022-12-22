#!/usr/bin/env python3

import email, smtplib

from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def file_get_contents(filename):
    with open(filename) as f:
        return f.read()

port = 25  # For SSL
smtp_server = "smtp.domain.tld"
sender_email = "mail@domain.tld"  # Enter your address
user_email = "mail@domain.tld"  # Enter your address
receiver_email = "other-mail@domain.tld"  # Enter receiver address
password = "password"

# get date now
dt_now = datetime.now()

message = MIMEMultipart("alternative")
message["Subject"] = "[dmarc-reports] "+str(dt_now)
message["From"] = sender_email
message["To"] = receiver_email


filename = "report.html"


# Create the plain-text and HTML version of your message
text = file_get_contents(filename) # il affichera le code html brute
html = file_get_contents(filename)

# Open PDF file in binary mode
with open(filename, "rb") as attachment:
    # Add file as application/octet-stream
    # Email client can usually download this automatically as attachment
    part = MIMEBase("application", "octet-stream")
    part.set_payload(attachment.read())

# Encode file in ASCII characters to send by email    
encoders.encode_base64(part)

# Add header as key/value pair to attachment part
part.add_header(
    "Content-Disposition",
    f"attachment; filename= {filename}",
)

# Add attachment to message and convert message to string
message.attach(part)


# Turn these into plain/html MIMEText objects
part1 = MIMEText(text, "plain")
part2 = MIMEText(html, "html")

# Add HTML/plain-text parts to MIMEMultipart message
# The email client will try to render the last part first
message.attach(part1)
message.attach(part2)
text = message.as_string()

# Try to log in to server and send email
try:
    server = smtplib.SMTP(smtp_server,port)
    server.ehlo() # Can be omitted
    #server.starttls(context=context) # Secure the connection
    server.sendmail(sender_email, receiver_email, text)
    # TODO: Send email here
except Exception as e:
    # Print any error messages to stdout
    print(e)
finally:
    server.quit() 
