#!/bin/bash

echo "Fetching mails"
offlineimap -l offlineimap.log -c offlineimaprc

echo "Extracting attachments"
test -r my_ips && source my_ips
./extract.py
