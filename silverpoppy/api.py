import sys
import logging
import os
import tempfile
import time
import urllib
import urllib2
import StringIO
from ftplib import FTP
from xml.sax.saxutils import escape

from lxml import etree as ET


OUTPATH = tempfile.gettempdir() + '/'

logger = logging.getLogger(__name__)
if sys.version_info < (2, 7):
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
else:
    from logging import NullHandler

logger.addHandler(NullHandler())


class Engage(object):
    def __init__(self, api_url, username=None, password=None, ftp_url=None, *args, **kwargs):

        self.api_url = api_url
        self.username = username
        self.password = password
        self.ftp_url = ftp_url
        self.jsessionid = None

    def login(self, username=None, password=None):
        self.username = username if username else self.username
        self.password = password if password else self.password

        if not (self.username and self.password):
            raise ValueError("Engage.login() requires username and password be set.")

        xml_login = """
        <Envelope>
            <Body>
                <Login>
                    <USERNAME>{0}</USERNAME>
                    <PASSWORD>{1}</PASSWORD>
                </Login>
            </Body>
        </Envelope>
        """.format(self.username, escape(self.password))

        xml_resp = self._xml_request(self.api_url, xml_login)

        tree = ET.ElementTree(ET.fromstring(xml_resp))
        root = tree.getroot()

        res = root.xpath('/Envelope/Body/RESULT/SUCCESS/text()')[0]
        res = False if res.lower() == 'false' else True

        if res:
            self.jsessionid = root.xpath('/Envelope/Body/RESULT/SESSIONID/text()')[0]
            logger.info("Engage logged in, jsessionid:{0}".format(self.jsessionid))

        return res

    def logout(self):
        xml_logout = """
        <Envelope>
            <Body>
                <Logout/>
            </Body>
        </Envelope>
        """

        resp = self.xml_engage_request(xml_logout)

        if resp.SUCCESS:
            logger.info("Engage logged out, jsessionid:{0}".format(self.jsessionid))
            self.jsessionid = None

        return resp.SUCCESS

    def xml_engage_request(self, xml_req):
        if not self.jsessionid:
            self.login()

        api_url_jsid = self.api_url + ';jsessionid={0}'.format(self.jsessionid)

        tree = ET.ElementTree(ET.fromstring(xml_req))
        root = tree.getroot()

        callname = root.xpath('name(/Envelope/Body/*[1])')

        logger.debug("XML request for API call to '{0}':\n{1}".format(callname, xml_req))

        xml_resp = self._xml_request(api_url_jsid, xml_req)

        logger.debug("XML response for API call to '{0}':\n{1}".format(callname, xml_resp))

        return EngageResponse(xml_resp, callname, self)

    def ftp_putfile(self, filename, to='upload', as_filename=None, move_to=None):
        result = None
        if not os.path.isfile(filename):
            logger.error("ftp_putfile: {0} not found.".format(filename))
            return result

        with open(filename, 'r') as f:
            if self.ftp_url:
                ftp = FTP(self.ftp_url)
            else:
                raise ValueError("Engage.ftp_putfile() requires ftp_url be set.")

            ftp.login(self.username, self.password)

            ftp.cwd(to)

            if not as_filename:
                fname = filename[((filename.rfind('/')) + 1):]
            else:
                fname = as_filename

            result = ftp.storlines('STOR ' + fname, f)
            logger.debug("ftp_putfile: stored {0}{1} ({2})".format(filename,
                                                                   " as {0}".format(fname) if as_filename else "",
                                                                   result))

            if move_to:
                rfrom = os.path.join(to, fname)
                rto = os.path.join(move_to, fname)
                rename = ftp.rename(rfrom, rto)
                logger.debug("ftp_putfile: moved {0} to {1} ({2})".format(rfrom, rto, rename))

            ftp.quit()

        return result

    def ftp_getfile(self, filename, outfilepath):
        if self.ftp_url:
            ftp = FTP(self.ftp_url)
        else:
            raise ValueError("Engage.ftp_getfile() requires ftp_url be set.")

        buf = StringIO.StringIO()
        ftp = FTP(self.ftp_url)
        ftp.login(self.username, self.password)
        #ftp.cwd('upload')
        #fname = filename[((filename.rfind('/'))+1):]
        res = ftp.retrlines('RETR ' + filename, lambda s, w=buf.write: w(s + '\n'))

        ftp.quit()

        with open(outfilepath, 'w') as of:
            of.writelines(buf.getvalue())

        buf.close()

        logger.debug("ftp_getfile: retrieved {0}".format(filename))

        return res

    def _xml_request(self, api_url, xml):
        """submit a custom xml request
        api_url, xml, are required
        returns the silverpop response (xml)
        """

        headers = {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}
        xml = urllib.urlencode({'xml': xml})
        request = urllib2.Request(api_url, xml, headers)

        handle = urllib2.urlopen(request)

        response = handle.read()
        return response


class EngageResponse(object):
    def __init__(self, xml_resp, callname, engage, *args, **kwargs):

        self.xml_response = xml_resp
        self.callname = callname
        self.Engage = engage
        self.tree = ET.ElementTree(ET.fromstring(self.xml_response))
        self.root = self.tree.getroot()
        self.job_id = None
        self.job_status = None
        self.job_polling_seconds = 5

        res = self.root.xpath('/Envelope/Body/RESULT/SUCCESS/text()')[0]

        self.job_id = self.result('JOB_ID')

        self.SUCCESS = True if res.lower() == 'true' or res.lower() == 'success' else False

    def __str__(self):
        return self.xml_response

    def result(self, item):
        res = self.root.xpath('/Envelope/Body/RESULT/{0}/text()'.format(item))
        if res:
            ret = res[0]
        else:
            ret = None
        return ret

    def _writeout(self, filename):
        with open(filename, 'wa') as f:
            f.write(self.xml_response)

    def get_job_status(self):
        xml_getjobstatus = """
        <Envelope>
            <Body>
                <GetJobStatus>
                    <JOB_ID>{0}</JOB_ID>
                </GetJobStatus>
            </Body>
        </Envelope>
        """

        if self.job_id:
            res = self.Engage.xml_engage_request(xml_getjobstatus.format(self.job_id))
            if res.SUCCESS:
                status = res.result('JOB_STATUS')
                if self.job_status != status:
                    self.job_status = status
                    if self.job_status not in ['WAITING', 'RUNNING']:
                        #print res
                        out_jobstatusfile = '{0}{1}_JOBID{2}.status'.format(OUTPATH, self.callname, self.job_id)
                        res._writeout(out_jobstatusfile)

                return self.job_status

            return res.SUCCESS

        return None

    def handle_job(self):
            if self.SUCCESS:
                status_msg = "{0}: JOB_ID: {1}, STATUS: {2}"
                logger.info(
                    "{0}: API called, JOB_ID: {1}".format(self.callname, self.job_id))

                while self.get_job_status() in ['WAITING', 'RUNNING']:
                    logger.info(status_msg.format(self.callname, self.job_id, self.job_status))
                    time.sleep(self.job_polling_seconds)

                logger.info(status_msg.format(self.callname, self.job_id, self.job_status))
            else:
                err_msg = "{0}: API call failed."
                logger.error(err_msg)
                self._writeout(OUTPATH + '{0}_JOBID{1}.err'.format(self.callname, self.job_id))
                raise ValueError(err_msg)
