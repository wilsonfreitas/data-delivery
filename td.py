
from google.appengine.api import urlfetch
from bs4 import BeautifulSoup

def cetip(content):
    soup = BeautifulSoup(content)
    # <span id="ctl00_Banner_lblTaxDI">10,80%</span>
    # <span id="ctl00_Banner_lblTaxDateDI">(17/04/2014)</span>
    # soup.find_all(id='ctl00_Banner_lblTaxDI')
    rate = soup.find_all(id='ctl00_Banner_lblTaxDI')[0].string
    return float(rate.replace('%', '').replace(',', '.'))

def bmf(content):
    soup = BeautifulSoup(content)
    # <span id="ctl00_Banner_lblTaxDI">10,80%</span>
    # <span id="ctl00_Banner_lblTaxDateDI">(17/04/2014)</span>
    # soup.find_all(id='ctl00_Banner_lblTaxDI')
    return soup.find_all(id='tb_principal1')
    # return float(rate.replace('%', '').replace(',', '.'))


tickers = {
    'bmf': {
        'url': 'http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/TxRef1.asp?slcTaxa=PRE',
        'parse': bmf
    },
    'cetip': {
        'url': 'http://www.cetip.com.br/',
        'parse': cetip
    }
}

result = urlfetch.fetch(tickers['bmf']['url'])
if result.status_code == 200:
    value = tickers['bmf']['parse'](result.content)
    print(value)

