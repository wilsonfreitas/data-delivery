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

CALENDAR = Calendar(ANBIMA.holidays, weekdays=('Saturday', 'Sunday'), name='ANBIMA')

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
    id = None
    def get(self, **kwargs):
        logging.info('Starting download for refdate: %s', kwargs.get('refdate'))
        the_day = asdate(kwargs.get('refdate'))
        if CALENDAR.isbizday(str(the_day)):
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


def apply_close_to_rule(expr, weekday, adjust):
    widx = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun').index(weekday)
    def compute_maturity(year, month):
        dt = CALENDAR.getdate(expr, year, month)
        if dt.weekday() != widx:
            dt1 = CALENDAR.getdate('first {} before {}'.format(weekday, expr), year, month)
            dt2 = CALENDAR.getdate('first {} after {}'.format(weekday, expr), year, month)
            dt = dt1 if (dt-dt1) < (dt2-dt) else dt2
        return dt, {
            'following': lambda x: CALENDAR.following(x),
            'preceding': lambda x: CALENDAR.preceding(x),
            'modified-following': lambda x: CALENDAR.modified_following(x),
            'modified-preceding': lambda x: CALENDAR.modified_preceding(x),
        }[adjust](dt)
    return compute_maturity


def apply_maturity_rule(expr, adjust):
    def compute_maturity(year, month):
        dt = CALENDAR.getdate(expr, year, month)
        return dt, {
            'following': lambda x: CALENDAR.following(x),
            'preceding': lambda x: CALENDAR.preceding(x),
            'modified-following': lambda x: CALENDAR.modified_following(x),
            'modified-preceding': lambda x: CALENDAR.modified_preceding(x),
        }[adjust](dt)
    return compute_maturity


contract_maturity_rule = lambda x: {
    'AUD': apply_maturity_rule('first day', 'following'),
    'BGI': apply_maturity_rule('last day', 'modified-following'),
    'BRI': apply_maturity_rule('first day', 'following'),
    'CAD': apply_maturity_rule('first day', 'following'),
    'CCM': apply_maturity_rule('15th day', 'following'),
    'CHF': apply_maturity_rule('first day', 'following'),
    'CLP': apply_maturity_rule('first day', 'following'),
    'DAP': apply_maturity_rule('15th day', 'following'),
    'DDI': apply_maturity_rule('first day', 'following'),
    'DI1': apply_maturity_rule('first day', 'following'),
    'DOL': apply_maturity_rule('first day', 'following'),
    'ETH': apply_maturity_rule('last day', 'modified-following'),
    'EUR': apply_maturity_rule('first day', 'following'),
    'FRC': apply_maturity_rule('first day', 'following'),
    'GBP': apply_maturity_rule('first day', 'following'),
    'IAP': apply_maturity_rule('15th day', 'following'),
    'ICF': apply_maturity_rule('6th bizday before last day', 'following'),
    'IND': apply_close_to_rule('15th day', 'wed', 'following'),
    'ISP': apply_maturity_rule('third fri', 'following'),
    'JPY': apply_maturity_rule('first day', 'following'),
    'KFE': apply_maturity_rule('6th bizday before last day', 'following'),
    'MXN': apply_maturity_rule('first day', 'following'),
    'NZD': apply_maturity_rule('first day', 'following'),
    'OC1': apply_maturity_rule('first day', 'following'),
    'OZ1': apply_maturity_rule('last day', 'modified-following'),
    'SFI': apply_maturity_rule('second day before first day', 'following'),
    'SJC': apply_maturity_rule('second day before first day', 'following'),
    'T10': apply_maturity_rule('first day', 'following'),
    'TRY': apply_maturity_rule('first day', 'following'),
    'WDO': apply_maturity_rule('first day', 'following'),
    'WEU': apply_maturity_rule('first day', 'following'),
    'WIN': apply_close_to_rule('15th day', 'wed', 'following'),
    'ZAR': apply_maturity_rule('first day', 'following')
}[x]


maturity_month = lambda x: {
    'F': 1,
    'G': 2,
    'H': 3,
    'J': 4,
    'K': 5,
    'M': 6,
    'N': 7,
    'Q': 8,
    'U': 9,
    'V': 10,
    'X': 11,
    'Z': 12
}[x]


def parse_maturity_code(maturity_code):
    month = maturity_month(maturity_code[0])
    year = 2000 + int(maturity_code[1:])
    return (year, month)


def contract_to_maturity(contract):
    mat_code = contract[-3:]
    year, month = parse_maturity_code(mat_code)
    ctr_code = contract[:3]
    return contract_maturity_rule(ctr_code)(year, month)


# <select name="cboMercado" onChange="Busca(this.selectedIndex)" style="width: 150px;" class="comboAmarelo">
#   <option value="0">Selecione</option>
#   <option value="2" selected>Futuro</option>
#   <option value="3" >Opções
#   s/ disponível</option>
#   <option value="4" >Opções
#   s/ futuro</option>
#   <option value="5" >Swap</option>
#   <option value="6" >Volatilidade</option>
# </select>

# curl 'http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/SeriesAutorizadas1.asp?pagetype=pop&caminho='
# -H 'Cookie: ASPSESSIONIDQSRRRQAB=LIPGKJABACEEHILKACPCDKGN; ASPSESSIONIDSQTSRRBB=KLEJABABOBMKHCOIKIPOHHGC; ASPSESSIONIDCCRSASRQ=FLEHKHABLLONFHBELKOIBJIH; TS0178b35a=011d592ce1fe3c24ac6287091597da0ca7244757370bb78de3317bed7cd915fd1337740c15e299461487373132f9d233cdfc4f8930ba79e507cefe93a7ccd7e33eea1cc7c6'
# -H 'Origin: http://www2.bmf.com.br'
# -H 'Accept-Encoding: gzip, deflate'
# -H 'Accept-Language: en-US,en;q=0.8'
# -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.2 Safari/537.36'
# -H 'Content-Type: application/x-www-form-urlencoded' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8' -H 'Cache-Control: max-age=0' -H 'Referer: http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/SeriesAutorizadas1.asp?pagetype=pop&caminho=' -H 'Connection: keep-alive' --data
# 'cboMercado=2&cboMercadoria=2-ACF' --compressed

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
        ds.headers = ['Name', 'Currency', 'SpotPrice', 'Maturity', 'MaturityAdjusted', 'Notional', 'StrikePrice', 'Type']
        for row, cel0 in zip(data, col1):
            contract = cel0 + row[1]
            try:
                mat, mat_adj = contract_to_maturity(contract)
            except Exception as ex:
                logging.warn(ex)
                logging.warn(row)
                logging.warn('Error parsing contract code')
            else:
                _row = zip(ds.headers, (contract, 'BRL', tp.parse(row[3]), mat.isoformat(), mat_adj.isoformat(),
                    100000.0, tp.parse(row[3]), 'Future'))
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
