#!/bin/bash

if [ ! -r my_ips ]; then
  echo 'Cannot find "my_ips" file, please create it!'
  exit 1
fi

echo "Fetching mails"
offlineimap -l offlineimap.log -c offlineimaprc

echo "Extracting attachments"
source my_ips
./extract.py
