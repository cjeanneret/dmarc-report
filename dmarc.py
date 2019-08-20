#!/usr/bin/env python3

import datetime
import glob
import gzip
import jinja2
import os
import sqlite3
import xml.etree.ElementTree as ET
import zipfile

TABLE_RECORDS = '''
CREATE TABLE records (id INTEGER PRIMARY KEY AUTOINCREMENT,
date_begin TEXT,
date_end TEXT,
count INTEGER,
report_id TEXT,
source_ip TEXT,
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
INSERT INTO records(report_id, source_ip, dkim, spf, type, comment, header_from, dkim_domain, dkim_result, dkim_hresult, spf_domain, spf_result, org_name, domain, count, date_begin, date_end) 
VALUES("%(report_id)s", "%(s_ip)s", "%(dkim)s", "%(spf)s",
"%(type)s", "%(comment)s", "%(header_from)s",
"%(dkim_domain)s", "%(dkim_result)s",
"%(dkim_hresult)s", "%(spf_domain)s",
"%(spf_result)s", "%(org_name)s", "%(domain)s", %(count)d,
"%(date_begin)s", "%(date_end)s")
'''

CHECK_RECORD = '''
SELECT COUNT(*) FROM records WHERE
source_ip = ? AND
report_id = ?
'''

QUERY_RECORDS = '''
SELECT source_ip, SUM(count), domain, org_name, date_begin, date_end
FROM records where dkim = 'fail' or spf = 'fail' GROUP BY source_ip
ORDER by date_begin DESC, date_end ASC
'''

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

    def __prepare(self):
        if not os.path.exists(self.__db):
            conn = sqlite3.connect(self.__db)
            c = conn.cursor()
            c.execute(TABLE_RECORDS)
            conn.commit()
            conn.close()

    def __check(self):
        data = (self.__data['s_ip'], self.__data['report_id'])
        self.__cursor.execute(CHECK_RECORD, data)
        return self.__cursor.fetchone()[0] > 0

    def __format_date(self, timestamp):
        date = datetime.datetime.fromtimestamp(int(timestamp))
        return date.date()

    def __insert(self):
        inserted = 0
        self.__data['org_name'] = self.doc.findtext("report_metadata/org_name", default="NA")
        self.__data['domain'] = self.doc.findtext("policy_published/domain", default="NA")
        self.__data['report_id'] = self.doc.findtext("report_metadata/report_id", default="NA")

        self.__data['date_begin'] = self.doc.findtext("report_metadata/date_range/begin")
        self.__data['date_begin'] = self.__format_date(self.__data['date_begin'])
        self.__data['date_end'] = self.doc.findtext("report_metadata/date_range/end")
        self.__data['date_end'] = self.__format_date(self.__data['date_end'])

        container = self.doc.findall("record")
        for elem in container:
            self.__data['s_ip'] = elem.findtext("row/source_ip", default="NA")
            self.__data['dkim'] = elem.findtext("row/policy_evaluated/dkim", default="NA")
            self.__data['spf'] = elem.findtext("row/policy_evaluated/spf", default="NA")
            self.__data['type'] = elem.findtext("row/policy_evaluated/reason/type", default="NA")
            self.__data['comment'] = elem.findtext("row/policy_evaluated/reason/comment", default="NA")
            self.__data['header_from'] = elem.findtext("identifiers/header_from", default="NA")
            self.__data['dkim_domain'] = elem.findtext("auth_results/dkim/domain", default="NA")
            self.__data['dkim_result'] = elem.findtext("auth_results/dkim/result", default="NA")
            self.__data['dkim_hresult'] = elem.findtext("auth_results/dkim/human_result", default="NA")
            self.__data['spf_domain'] = elem.findtext("auth_results/spf/domain", default="NA")
            self.__data['spf_result'] = elem.findtext("auth_results/spf/result", default="NA")
            self.__data['count'] = elem.findtext("row/count", default="1")

            self.__data['count'] = int(self.__data['count'])

            if not self.__check():
                inserted += 1
                sql = INSERT_RECORD %  self.__data
                self.__cursor.execute(sql)
                self.__conn.commit()

        return inserted
        
    def render(self):
        current_path = os.path.dirname(os.path.abspath(__file__))
        template_file_path = os.path.join(current_path, self.__template_filename)
        rendered_file_path = os.path.join(current_path, self.__rendered_filename)
        render_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(current_path))

        self.__cursor.execute(QUERY_RECORDS)
        records = self.__cursor.fetchall()

        render_vars = {
            'records': records,
            'my_ip': [
                '195.201.47.87',
                '2a01:4f8:1c0c:807f::1',
                '159.69.100.16',
                '2a01:4f8:c01f:13::1',
                '95.216.176.128',
                '2a01:4f9:c01f:21::1',
                ]
        }
        output_text = render_environment.get_template(self.__template_filename).render(render_vars)
        with open(rendered_file_path, "w") as result_file:
            result_file.write(output_text)

    def parse(self):
        inserted = 0
        for f in glob.glob('./reports/*.gz'):
            with gzip.open(f, 'rb') as f:
                dom = ET.parse(f)
                self.doc = dom.getroot()
                inserted += self.__insert()
        for f in glob.glob('./reports/*.zip'):
            with zipfile.ZipFile(f, 'r') as myzip:
                with myzip.open(myzip.namelist()[0]) as zf:
                    dom = ET.parse(zf)
                    self.doc = dom.getroot()
                    inserted += self.__insert()

        print('Inserted %i record(s)' % inserted)
