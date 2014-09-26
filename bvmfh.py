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

CALENDAR = Calendar(ANBIMA.holidays, weekdays=('Saturday', 'Sunday'))

@route(r'/bvmf')
@route(r'/bvmf/')
class IndexHandler(WelHandler):
    def get(self):
        context = {}
        self.render_template('bvmf/index', **context)


class CurvesScrap(Scrap):
    data = FloatAttr(xpath='//td[@class="tabelaConteudo1"]|//td[@class="tabelaConteudo2"]', decimalsep=',')
    cols = Attribute(xpath='//*[@class="tabelaItem"]', transform=len)


@route(r'/bvmf/curves')
@route(r'/bvmf/curves/<code:...>/<format:(json|csv|yaml)>')
class CurvesHandler(WelHandler):
    def get(self, code='PRE', format='json'):
        refdate = asdate(self.request.get('refdate'))
        downloader = CurvesDownloader(refdate=refdate, code=code)
        if not gcs.check_file(downloader.filename):
            downloader.download()
        content, _ = gcs.read_file(downloader.filename)
        # ----
        scrap = CurvesScrap()
        scrap.lxml_parser(content)
        l = scrap.cols + 1
        data = [tuple(scrap.data[i:i+l]) for i in range(0, len(scrap.data), l)]
        ds = tablib.Dataset()
        ds.headers = ['dates', 'DU', 'DC', 'rates']
        for row in data:
            maturity = asdate(refdate.date + timedelta(row[0]))
            ds.append((str(maturity), CALENDAR.bizdays((str(refdate), str(maturity))), int(row[0]), row[2]))
        # ----
        if format == 'json':
            self.response.headers['Content-Type'] = 'application/json'
            self.response.write(ds.json)
        elif format == 'csv':
            self.response.headers['Content-Type'] = 'application/csv'
            self.response.write(ds.csv)
        elif format == 'yaml':
            self.response.headers['Content-Type'] = 'text/x-yaml'
            self.response.write(ds.yaml)
        # context = {'header': scrap.header, 'data': data}
        # self.render_template('bvmf/futures', **context)


class FuturesScrap(Scrap):
    data = Attribute(xpath='//table[@id="tblDadosAjustes"]/tr[@class="tabelaConteudo1"]/td|//table[@id="tblDadosAjustes"]/tr[@class="tabelaConteudo2"]/td')
    header = Attribute(xpath='//table[@id="tblDadosAjustes"]/*/td[@class="tabelaTitulo"]')


@route(r'/bvmf/futures')
@route(r'/bvmf/futures/<code:...>/<format:(json|csv|yaml)>')
@route(r'/bvmf/futures/<code:...>/<date:\d{4}-\d{2}-\d{2}>/<format:(json|csv|yaml)>')
class FuturesHandler(WelHandler):
    def get(self, date=None, code=None, format='json'):
        date = asdate(date)
        downloader = FuturesDownloader(refdate=date)
        if not gcs.check_file(downloader.filename):
            downloader.download()
        content, _ = gcs.read_file(downloader.filename)
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
        ds.headers = ['contract', 'maturity_code', 'spot_price']
        for row, cel0 in zip(data, col1):
            if cel0 == code:
                ds.append((cel0+row[1], row[1], row[3]))
        # ----
        if format == 'json':
            self.response.headers['Content-Type'] = 'application/json'
            self.response.write(ds.json)
        elif format == 'csv':
            self.response.headers['Content-Type'] = 'application/csv'
            self.response.write(ds.csv)
        elif format == 'yaml':
            self.response.headers['Content-Type'] = 'text/x-yaml'
            self.response.write(ds.yaml)
        # context = {'header': scrap.header, 'data': data}
        # self.render_template('bvmf/futures', **context)


class asdate(object):
    def __init__(self, d=None):
        d = d if d else date.today()
        if type(d) in (str, unicode):
            d = datetime.strptime(d, '%Y-%m-%d').date()
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


class Downloader(object):
    def download(self):
        result = urlfetch.fetch(self.url)
        if result.status_code == 200:
            logging.info('fetched -- %s', self.url)
            gcs.create_file(self.filename, result.content, result.headers['Content-Type'])
            logging.info('%s created - %s', self.filename, result.headers['Content-Type'])
        else:
            logging.error('%s not created (status_code = %d)', self.filename, result.status_code)


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


class FuturesDownloader(Downloader):
    URL = 'http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/Ajustes1.asp'
    def __init__(self, **kwargs):
        date = asdate(kwargs.get('refdate'))
        self.filename = 'futures-%s' % date.format()
        self.url = '%s?txtData=%s' % (self.URL, date.format('%d/%m/%Y'))


class CurvesDownloader(Downloader):
    URL = 'http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/TxRef1.asp'
    def __init__(self, **kwargs):
        code = kwargs.get('code', 'PRE')
        refdate = asdate(kwargs.get('refdate'))
        dstr1 = refdate.format('%d/%m/%Y')
        dstr2 = refdate.format('%Y%m%d')
        self.url = '%s?Data=%s&Data1=%s&slcTaxa=%s' % (self.URL, dstr1, dstr2, code)
        self.filename = '%s-%s-%s' % ('curves', code,  date)


@route(r'/bvmf/futures/download')
@route(r'/bvmf/futures/download/<refdate:\d{4}-\d{2}-\d{2}>')
class FuturesDownloadHandler(DownloadHandler):
    def process(self, **kwargs):
        downloader = FuturesDownloader(**kwargs)
        downloader.download()


@route(r'/bvmf/curves/download/<code>')
@route(r'/bvmf/curves/download/<code>/<refdate:\d{4}-\d{2}-\d{2}>')
class CurvesDownloadHandler(DownloadHandler):
    def process(self, **kwargs):
        downloader = CurvesDownloader(**kwargs)
        downloader.download()




# Declaring app -- instantiated in welgae

app = welapp
