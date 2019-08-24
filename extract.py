#!/usr/bin/env python3

import dmarc
import email
import os

ACCEPTED_MIME = [
        'application/gzip',
        'application/x-gzip',
        'application/zip',
        'application/x-zip-compressed',
        'application/octet-stream',
        ]

def save_file(attachment):
    f_name = attachment.get_filename()
    dest = os.path.join('./reports', f_name)
    with open(dest, 'wb') as f:
        f.write(attachment.get_payload(decode=True))

if not os.path.isdir('./reports'):
    os.mkdir('./reports')

for root, dirs, files in os.walk('./mails/INBOX/'):
    for f in files:
        mail_file = os.path.join(root, f)
        msg = email.message_from_file(open(mail_file))
        if msg.is_multipart():
            for attach in msg.get_payload():
                if attach.get_content_type() in ACCEPTED_MIME: save_file(attach)
        else:
            save_file(msg)

i_dmarc = dmarc.dmarc()
i_dmarc.parse()
i_dmarc.render()
