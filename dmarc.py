#!/usr/bin/env python3

import datetime
import dns.resolver
import glob
import gzip
import jinja2
import mimetypes as filetype
import os
import progressbar
import socket
import sqlite3
import sys
import xml.etree.ElementTree as ET
import zipfile

TABLE_RECORDS = '''
CREATE TABLE records (id INTEGER PRIMARY KEY AUTOINCREMENT,
date_begin INTEGER,
date_end INTEGER,
count INTEGER,
report_id TEXT,
source_ip TEXT,
ip_reverse TEXT,
domain TEXT,
dkim TEXT,
spf TEXT,
type TEXT,
comment TEXT,
header_from TEXT,
dkim_domain TEXT,
dkim_result TEXT,
dkim_hresult TEXT,
spf_domain TEXT,
spf_result TEXT,
org_name TEXT)
'''

INSERT_RECORD = '''
INSERT INTO records(report_id, source_ip, dkim, spf, type, comment, header_from, dkim_domain, dkim_result, dkim_hresult, spf_domain, spf_result, org_name, domain, count, date_begin, date_end, ip_reverse) 
VALUES("%(report_id)s", "%(s_ip)s", "%(dkim)s", "%(spf)s",
"%(type)s", "%(comment)s", "%(header_from)s",
"%(dkim_domain)s", "%(dkim_result)s",
"%(dkim_hresult)s", "%(spf_domain)s",
"%(spf_result)s", "%(org_name)s", "%(domain)s", %(count)d,
"%(date_begin)s", "%(date_end)s", "%(ip_reverse)s")
'''

CHECK_RECORD = '''
SELECT id FROM records WHERE
source_ip = ? AND
report_id = ?
'''

QUERY_RECORDS = '''
SELECT source_ip, count, domain, org_name, date_begin, date_end, dkim, spf, ip_reverse, comment
FROM records ORDER by date_begin DESC, date_end ASC
'''

TABLE_RDNS = '''
CREATE TABLE rdns (ip TEXT PRIMARY KEY, rdns TEXT)
'''

QUERY_RDNS = '''
SELECT rdns FROM rdns WHERE ip="%s"
'''

INSERT_RDNS = '''
INSERT INTO rdns(ip, rdns) VALUES(?, ?)
'''

MIME_GZIP = ['application/gzip', 'application/x-gzip']
MIME_ZIP = ['application/zip', 'application/x-zip-compressed']
MIME_TRASH = ['application/octet-stream', 'text/xml']

class dmarc():
    def __init__(self):
        self.__db = './dmarc.sqlite'
        self.__prepare()
        self.__conn = sqlite3.connect(self.__db)
        self.__cursor = self.__conn.cursor()

        self.doc = None
        self.__data = {}
        self.__template_filename = 'template.j2'
        self.__rendered_filename = 'report.html'

        self.__bar = progressbar.ProgressBar(max_value=progressbar.UnknownLength, redirect_stdout=True)
        self.__counter = 0

        self.__domain_mx = []
        if 'MY_IPS' in os.environ:
            self.__my_ips = os.environ['MY_IPS'].split()
        else:
            self.__my_ips = []

    def __del__(self):
        self.__conn.commit()
        self.__conn.close()

    def __prepare(self):
        if not os.path.exists(self.__db):
            conn = sqlite3.connect(self.__db)
            c = conn.cursor()
            c.execute(TABLE_RECORDS)
            c.execute(TABLE_RDNS)
            conn.commit()
            conn.close()

    def __check(self):
        data = (self.__data['s_ip'], self.__data['report_id'])
        self.__cursor.execute(CHECK_RECORD, data)
        return self.__cursor.fetchone() is not None

    def __format_date(self, timestamp):
        try:
            date = datetime.datetime.fromtimestamp(int(timestamp))
            return date.date()
        except:
            return timestamp

    def __get_mx(self, domain):
        if domain not in self.__domain_mx:
            print('Fetching MX for %s' % domain)
            self.__domain_mx.append(domain)
            for x in dns.resolver.query(domain, 'MX'):
                mx = x.to_text().split()[1]
                ips = [ str(i[4][0]) for i in socket.getaddrinfo(mx, 25)]
                self.__my_ips.extend(ips)

    def __rdns(self):
        self.__cursor.execute(QUERY_RDNS % self.__data['s_ip'])
        data = self.__cursor.fetchone()
        if data is not None:
            return data[0]
        else:
            try:
                rdns = socket.gethostbyaddr(self.__data['s_ip'])[0]
            except socket.herror:
                rdns = 'NXDOMAIN'
            data = (self.__data['s_ip'], rdns)
            self.__cursor.execute(INSERT_RDNS, data)
            self.__conn.commit()
            return rdns

    def __insert(self):
        inserted = 0
        self.__data['org_name'] = self.doc.findtext("report_metadata/org_name", default="NA")
        self.__data['domain'] = self.doc.findtext("policy_published/domain", default="NA")
        self.__data['report_id'] = self.doc.findtext("report_metadata/report_id", default="NA")

        self.__data['date_begin'] = int(self.doc.findtext("report_metadata/date_range/begin"))
        self.__data['date_end'] = int(self.doc.findtext("report_metadata/date_range/end"))

        if 'MY_IPS' not in os.environ:
            self.__get_mx(self.__data['domain'])

        container = self.doc.findall("record")
        for elem in container:
            self.__data['s_ip'] = elem.findtext("row/source_ip", default="NA")
            self.__data['dkim'] = elem.findtext("row/policy_evaluated/dkim", default="NA")
            self.__data['spf'] = elem.findtext("row/policy_evaluated/spf", default="NA")
            self.__data['type'] = elem.findtext("row/policy_evaluated/reason/type", default="NA")
            self.__data['comment'] = elem.findtext("row/policy_evaluated/disposition", default="NA")
            self.__data['header_from'] = elem.findtext("identifiers/header_from", default="NA")
            self.__data['dkim_domain'] = elem.findtext("auth_results/dkim/domain", default="NA")
            self.__data['dkim_result'] = elem.findtext("auth_results/dkim/result", default="NA")
            self.__data['dkim_hresult'] = elem.findtext("auth_results/dkim/human_result", default="NA")
            self.__data['spf_domain'] = elem.findtext("auth_results/spf/domain", default="NA")
            self.__data['spf_result'] = elem.findtext("auth_results/spf/result", default="NA")
            self.__data['count'] = elem.findtext("row/count", default="1")
            self.__data['ip_reverse'] = self.__rdns()

            self.__data['count'] = int(self.__data['count'])

            if not self.__check():
                self.__counter += 1
                sql = INSERT_RECORD %  self.__data
                self.__cursor.execute(sql)
                self.__conn.commit()

            self.__bar.update(self.__counter)
        
    def render(self):
        current_path = os.path.dirname(os.path.abspath(__file__))
        template_file_path = os.path.join(current_path, self.__template_filename)
        rendered_file_path = os.path.join(current_path, self.__rendered_filename)
        render_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(current_path))
        render_environment.filters['datetime'] = self.__format_date

        self.__cursor.execute(QUERY_RECORDS)
        records = self.__cursor.fetchall()

        render_vars = {
            'records': records,
            'my_ip': self.__my_ips
        }
        output_text = render_environment.get_template(self.__template_filename).render(render_vars)
        with open(rendered_file_path, "w") as result_file:
            result_file.write(output_text)

    def parse(self):
        inserted = 0

        for f in glob.glob('./reports/*'):
            fp = None
            mime = filetype.guess_type(f)[0]
            if mime is None:
                print('ERROR: ', f)
                continue
            if mime in MIME_GZIP:
                fp = gzip.open(f, 'rb')
            elif mime in MIME_ZIP:
                with zipfile.ZipFile(f, 'r') as myzip:
                    fp = myzip.open(myzip.namelist()[0])
            elif mime in MIME_TRASH:
                try:
                    with zipfile.ZipFile(f, 'r') as myzip:
                        fp = myzip.open(myzip.namelist()[0])
                except zipfile.BadZipFile:
                    fp = gzip.open(f, 'rb')

            if fp:
                try:
                    dom = ET.parse(fp)
                    self.doc = dom.getroot()
                    self.__insert()
                except OSError:
                    fp = open(f, 'r')
                    dom = ET.parse(fp)
                    self.doc = dom.getroot()
                    self.__insert()
                finally:
                    fp.close()
            else:
                print('Unknown file: %s' % f)
