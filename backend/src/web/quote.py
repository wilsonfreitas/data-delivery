# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from bs4 import BeautifulSoup
from google.appengine.api import urlfetch

to_float = lambda x: float(x.replace('%', '').replace(',', '.'))

def cetip(content):
    soup = BeautifulSoup(content)
    # <span id="ctl00_Banner_lblTaxDI">10,80%</span>
    # <span id="ctl00_Banner_lblTaxDateDI">(17/04/2014)</span>
    # rate = soup.find_all(id='ctl00_Banner_lblTaxDI')[0].string
    rate = soup.find('span', id='ctl00_Banner_lblTaxDI').get_text(strip=True)
    return to_float(rate)

def bmf(content):
    soup = BeautifulSoup(content)
    c = [to_float(el.string) for el in soup.find_all(attrs={"class": "tabelaConteudo1"})]
    c = [tuple(c[i*3:(i+1)*3]) for i in range(len(c)//3)]
    return c

def selic(content):
    soup = BeautifulSoup(content)
    # print soup.find_all(attrs={"class": "tabelaTaxaSelic"})[0].find_all('td')[1]
    # print soup.find(attrs={"class": "tabelaTaxaSelic"}).find_all('td')[1]
    return soup.select("table.tabelaTaxaSelic td")[1].get_text(strip=True)

tickers = {
    'bmf': {
        'url': 'http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/TxRef1.asp?slcTaxa=PRE',
        'parse': bmf
    },
    'cdi': {
        'url': 'http://www.cetip.com.br/',
        'parse': cetip
    },
    'selic': {
        'url': 'http://www3.bcb.gov.br/selic/consulta/taxaSelic.do?method=listarTaxaDiaria&idioma=P',
        'parse': selic
    }
}

def index(_json, ticker):
    result = urlfetch.fetch(tickers[ticker]['url'])
    if result.status_code == 200:
        data = (ticker, tickers[ticker]['parse'](result.content))
    _json({'data': data})