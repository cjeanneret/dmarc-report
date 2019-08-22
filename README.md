# DMARC reporting tool
Simple scripts providing an easy way to get a human readable reporting for DMARC

## Dependencies
- offlineimap
- (python3) dns
- (python3) jinja2
- (python3) socket
- (python3) sqlite3
- (python3) zipfile
- (python3) xml

## Content
### extract.py
Extracts attachments (zip, gzip) and save them in "reports" directory.

### dmarc.py
Magical script that will read DMARC reports, and inject new records into an sqlite3 DB

### template.j2
Template used to generate the report (report.html). Nothing fancy.

### offlineimaprc.sample
Sample for offlineimap configuration file. You should ensure its mode is set to 0400.
Name *must* be offlineimaprc

### script.sh
The script you want to launch on a regular basis. Will call the other ones in order to
provide you an easy to read report.

## IPs
The report will highlight when your IPs are listed (red if failed, else green). There are
two ways to provide them:
- either create a "my_ips" file, based on the provided sample
- or let the script detect your MX.

Please note: the script won't check your SPF record, meaning it won't fetch specific
IPs (at least for now). If you have other IPs than your MX, you must provide the full
list using the MY_IPS environment variable.

## License
Shipped under MIT license.
