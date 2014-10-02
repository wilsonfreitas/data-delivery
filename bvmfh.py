# encoding: utf-8
# bmf http handlers

import logging
from itertools import izip
from datetime import datetime, date, timedelta

from google.appengine.api import urlfetch
import tablib
from bizdays import Calendar

from scraps import *
from welgae import *
import ANBIMA
import gcs
import tinydf
import textparser as tp

CALENDAR = Calendar(ANBIMA.holidays, weekdays=('Saturday', 'Sunday'))

class asdate(object):
    def __init__(self, d=None, format='%Y-%m-%d'):
        d = d if d else date.today()
        if type(d) in (str, unicode):
            d = datetime.strptime(d, format).date()
        elif type(d) is datetime:
            d = d.date()
        elif type(d) is asdate:
            d = d.date
        elif type(d) is date:
            pass
        else:
            raise ValueError()
        self.date = d
    
    def format(self, fmts='%Y-%m-%d'):
        return datetime.strftime(self.date, fmts)
    
    def __repr__(self):
        return self.format()
    
    __str__ = __repr__


@route(r'/bvmf')
@route(r'/bvmf/')
class IndexHandler(WelHandler):
    def get(self):
        context = {}
        self.render_template('bvmf/index', **context)


class Downloader(object):
    def download(self):
        if self.fetch():
            gcs.create_file(self.filename, self.content, self.content_type)
            logging.info('created -- %s (%s)', self.filename, self.content_type)
        else:
            logging.error('%s not created (status_code = %d)', self.filename, result.status_code)

    def fetch(self):
        result = urlfetch.fetch(self.url)
        if result.status_code == 200:
            logging.info('fetched -- %s (%d bytes)', self.url, len(result.content))
            self.content = result.content
            self.content_type = result.headers['Content-Type']
            return True
        else:
            logging.error('not fetched -- %s (status_code = %d)', self.url, result.status_code)
            return False


class DownloadHandler(WelHandler):
    calendar = Calendar(ANBIMA.holidays, weekdays=('Saturday', 'Sunday'))
    id = None
    def get(self, **kwargs):
        logging.info('Starting download for refdate: %s', kwargs.get('refdate'))
        the_day = asdate(kwargs.get('refdate'))
        if self.calendar.isbizday(str(the_day)):
            self.process(**kwargs)
        else:
            logging.warning('%s not a business day - skipping', today)
        self.response.headers['Content-Type'] = 'text/plain'


class CurvesDownloader(Downloader):
    URL = 'http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/TxRef1.asp'
    def __init__(self, **kwargs):
        code = kwargs.get('code', 'PRE')
        if kwargs.get('refdate'):
            refdate = asdate(kwargs.get('refdate'))
            dstr1 = refdate.format('%d/%m/%Y')
            dstr2 = refdate.format('%Y%m%d')
            self.url = '%s?Data=%s&Data1=%s&slcTaxa=%s' % (self.URL, dstr1, dstr2, code)
            self.filename = '%s-%s-%s' % ('curves', code,  date)
        else:
            self.url = '%s?slcTaxa=%s' % (self.URL, code)
            self.filename = '%s-%s-%s' % ('curves', code,  'last')


@route(r'/bvmf/curves/download/<code>')
@route(r'/bvmf/curves/download/<code>/<refdate:\d{4}-\d{2}-\d{2}>')
class CurvesDownloadHandler(DownloadHandler):
    def process(self, **kwargs):
        downloader = CurvesDownloader(**kwargs)
        downloader.download()


class CurvesScrap(Scrap):
    data = FloatAttr(xpath='//td[@class="tabelaConteudo1"]|//td[@class="tabelaConteudo2"]', decimalsep=',')
    cols = Attribute(xpath='//*[@class="tabelaItem"]', transform=len)
    refdate = Attribute(xpath='//td[@class="TXT_Azul"]', transform=lambda d: asdate(d[0], 'Atualizado em: %d/%m/%Y'))


CURVES_CODES_MAP = {
	'SLP': dict(compounding='discrete', daycount='business/252', calendar='ANBIMA'),
	'PRE': dict(compounding='discrete', daycount='business/252', calendar='ANBIMA'),
	'DOL': dict(compounding='simple', daycount='actual/360', calendar='actual'),
	'DOC': dict(compounding='simple', daycount='actual/360', calendar='actual'),
	'DIM': dict(compounding='discrete', daycount='business/252', calendar='ANBIMA'),
	'DIC': dict(compounding='discrete', daycount='business/252', calendar='ANBIMA'),
}

@route(r'/bvmf/curves/<code:...>/<format:(json|csv)>')
@route(r'/bvmf/curves/<code:...>/<refdate:\d{4}-\d{2}-\d{2}>/<format:(json|csv)>')
class CurvesHandler(WelHandler):
    def get(self, refdate=None, code='PRE', format='json'):
        downloader = CurvesDownloader(refdate=refdate, code=code)
        downloader.fetch()
        content = downloader.content
        # ----
        scrap = CurvesScrap()
        scrap.lxml_parser(content)
        refdate = scrap.refdate
        l = scrap.cols + 1
        data = [tuple(scrap.data[i:i+l]) for i in range(0, len(scrap.data), l)]
        ds = tinydf.DataFrame()
        ds.headers = ['Terms', 'Rates']
        ds.RefDate = str(scrap.refdate)
        ds.Name = code
        ds.Type = 'ZeroCurve'
        settings = CURVES_CODES_MAP[code]
        for k, v in settings.iteritems():
            setattr(ds, k, v)
        for row in data:
            maturity = asdate(refdate.date + timedelta(row[0]))
            _row = zip(ds.headers, (str(maturity), row[1]))
            ds.add(**dict(_row))
        # ----
        if format == 'json':
            self.response.headers['Content-Type'] = 'application/json'
            self.response.write(ds.json)
        elif format == 'csv':
            self.response.headers['Content-Type'] = 'application/csv'
            self.response.write(ds.csv)


@route(r'/bvmf/curves')
@route(r'/bvmf/curves/<code:...>')
@route(r'/bvmf/curves/<code:...>/<refdate:\d{4}-\d{2}-\d{2}>')
class ViewCurvesHandler(WelHandler):
    def get(self, refdate=None, code='PRE', format='json'):
        # downloader = CurvesDownloader(refdate=refdate, code=code)
        # downloader.fetch()
        # content = downloader.content
        # # ----
        # scrap = CurvesScrap()
        # scrap.lxml_parser(content)
        # refdate = scrap.refdate
        # l = scrap.cols + 1
        # data = [tuple(scrap.data[i:i+l]) for i in range(0, len(scrap.data), l)]
        # ds = tablib.Dataset()
        # ds.headers = ['dates', 'DU', 'DC', 'rates']
        # for row in data:
        #     maturity = asdate(refdate.date + timedelta(row[0]))
        #     ds.append((str(maturity), CALENDAR.bizdays((str(refdate), str(maturity))), int(row[0]), row[2]))
        # # ----
        # if format == 'json':
        #     self.response.headers['Content-Type'] = 'application/json'
        #     self.response.write(ds.json)
        # elif format == 'csv':
        #     self.response.headers['Content-Type'] = 'application/csv'
        #     self.response.write(ds.csv)
        # elif format == 'yaml':
        #     self.response.headers['Content-Type'] = 'text/x-yaml'
        #     self.response.write(ds.yaml)
        self.render_template('bvmf/curves')


class FuturesDownloader(Downloader):
    URL = 'http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/Ajustes1.asp'
    def __init__(self, **kwargs):
        if kwargs.get('refdate'):
            date = asdate(kwargs.get('refdate'))
            self.filename = 'futures-%s' % date.format()
            self.url = '%s?txtData=%s' % (self.URL, date.format('%d/%m/%Y'))
        else:
            self.filename = 'futures-last'
            self.url = self.URL


class FuturesScrap(Scrap):
    data = Attribute(xpath='//table[@id="tblDadosAjustes"]/tr[@class="tabelaConteudo1"]/td|//table[@id="tblDadosAjustes"]/tr[@class="tabelaConteudo2"]/td')
    header = Attribute(xpath='//table[@id="tblDadosAjustes"]/*/td[@class="tabelaTitulo"]')
    refdate = Attribute(xpath='//td[@class="TXT_Azul"]')


@route(r'/bvmf/futures/download')
@route(r'/bvmf/futures/download/<refdate:\d{4}-\d{2}-\d{2}>')
class FuturesDownloadHandler(DownloadHandler):
    def process(self, **kwargs):
        downloader = FuturesDownloader(**kwargs)
        downloader.download()


def contract_to_maturity(contract):
    mat_month = dict(F=1,G=2,H=3,J=4,K=5,M=6,N=7,Q=8,U=9,V=10,X=11,Z=12)
    month = mat_month[contract[0]]
    year = 2000 + int(contract[1:])
    return date(year, month, 1).isoformat()


@route(r'/bvmf/futures/<format:(json|csv)>')
@route(r'/bvmf/futures/<code:...>/<format:(json|csv)>')
@route(r'/bvmf/futures/<code:...>/<date:\d{4}-\d{2}-\d{2}>/<format:(json|csv)>')
class FuturesHandler(WelHandler):
    def get(self, date=None, code=None, format='json'):
        downloader = FuturesDownloader(refdate=date)
        downloader.fetch()
        content = downloader.content
        # ----
        scrap = FuturesScrap()
        scrap.lxml_parser(content)
        # ----
        l = len(scrap.header)
        data = [tuple(scrap.data[i:i+l]) for i in range(0, len(scrap.data), l)]
        def fulfill(x, y):
            x.append(y if y else x[-1])
            return x
        col1 = [x.split('-')[0].strip() for x in reduce(fulfill, [row[0] for row in data], [])]
        ds = tinydf.DataFrame()
        ds.headers = ['Name', 'Currency', 'SpotPrice', 'Maturity', 'Notional', 'StrikePrice', 'Type']
        for row, cel0 in zip(data, col1):
            try:
                mat = contract_to_maturity(row[1])
            except:
                logging.warn(row)
                logging.warn('Error parsing contract code')
            else:
                _row = zip(ds.headers, (cel0+row[1], 'BRL', tp.parse(row[3]), mat, 100000.0, tp.parse(row[3]), 'Future'))
                if not code:
                    ds.add(**dict(_row))
                elif code and cel0 == code:
                    ds.add(**dict(_row))
        # ----
        if format == 'json':
            self.response.headers['Content-Type'] = 'application/json'
            self.response.write(ds.json)
        elif format == 'csv':
            self.response.headers['Content-Type'] = 'text/csv'
            self.response.write(ds.csv)


@route(r'/bvmf/futures')
class ViewFuturesHandler(WelHandler):
    def get(self):
        downloader = FuturesDownloader()
        downloader.fetch()
        content = downloader.content
        # ----
        scrap = FuturesScrap()
        scrap.lxml_parser(content)
        l = len(scrap.header)
        data = [tuple(scrap.data[i:i+l]) for i in range(0, len(scrap.data), l)]
        def fulfill(x, y):
            x.append(y if y else x[-1])
            return x
        col1 = [x.split('-')[0].strip() for x in reduce(fulfill, [row[0] for row in data], [])]
        ds = tablib.Dataset()
        ds.headers = ['asset', 'contract', 'maturity_code', 'spot_price']
        for row, cel0 in zip(data, col1):
            ds.append((cel0, cel0+row[1], row[1], row[3]))
        # ----
        # self.response.headers['Content-Type'] = 'application/json'
        # self.response.write(ds.json)
        context = {'ds': ds}
        self.render_template('bvmf/futures', **context)


# Declaring app -- instantiated in welgae
app = welapp
