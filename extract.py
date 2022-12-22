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
        'application/xml',
        ]

def save_file(attachment, mtime):
    f_name = attachment.get_filename()

    if f_name:
        dest = os.path.join('./reports', f_name)
        if os.path.exists(dest):
            return
        with open(dest, 'wb') as f:
            f.write(attachment.get_payload(decode=True))
        os.utime(dest, (mtime, mtime))

if not os.path.isdir('./reports'):
    os.mkdir('./reports')

for root, dirs, files in os.walk('./mails/INBOX/'):
    for f in files:
        mail_file = os.path.join(root, f)
        mtime = os.path.getmtime(mail_file)
        msg = email.message_from_file(open(mail_file))
        if msg.is_multipart():
            for attach in msg.get_payload():
                if attach.get_content_type() in ACCEPTED_MIME:
                    save_file(attach, mtime)
        else:
            save_file(msg, mtime)

i_dmarc = dmarc.dmarc()
i_dmarc.parse()
i_dmarc.render()
