#!/bin/bash

echo "Fetching mails"
offlineimap -l offlineimap.log -c offlineimaprc
echo "Extracting attachments"
./extract.py
