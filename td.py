
# from google.appengine.api import urlfetch
# from bs4 import BeautifulSoup
import requests
from lxml import html
import inspect
import pprint


class Scrap(object):
    """    Scrap class represents a bunch of data collected from information
        sources.
    """
    def __new__(cls, *args, **kwargs):
        obj = super(Scrap, cls).__new__(cls)
        pairs = [(k,v) for k,v in cls.__dict__.items() if isinstance(v, Attribute)]
        obj.xpaths = {}
        obj.attrs = {}
        for k,v in pairs:
            v.index = k
            obj.xpaths[k] = v.xpath
            obj.attrs[k] = None
        return obj
    
    def __init__(self, **kwargs):
        prop_names = [member[0] for member in inspect.getmembers(self)
            if not member[0].startswith('__')]
        if '_error_is_none' not in prop_names:
            self._error_is_none = False
        for prop_name, prop_value in kwargs.items():
            if prop_name not in prop_names:
                raise KeyError('Invalid attribute: ' + prop_name)
            try:
                setattr(self, prop_name, prop_value)
            except Exception, e:
                if not self._error_is_none:
                    raise e
                    
    def __repr__(self):
        d = {}
        for propname in self.attrs:
            d[propname] = getattr(self, propname)
        return pprint.pformat(d)
    
    __str__ = __repr__
    
    def lxml_parser(self, content):
        doc = html.document_fromstring(content)
        for k, xpath in self.xpaths.items():
            elms = doc.xpath(xpath)
            setattr(self, k, [r.text.strip() if r.text else '' for r in elms])


class Attribute(object):
    """    Attribute class is a descriptor which represents each chunk of
        data extracted from a source of information.
    """
    def __init__(self, xpath, repeat=False, transform=lambda x: x):
        self.xpath = xpath
        self.index = None
        self.repeat = repeat
        self.transform = transform
    
    def parse(self, value):
        return value
    
    def __set__(self, obj, value):
        """sets attribute's value"""
        try:
            iter(value)
        except:
            value = [value]
        value = [self.parse(v) for v in value]
        value = self.transform(value)
        obj.attrs[self.index] = value
    
    def __get__(self, obj, typo=None):
        """gets attribute's value"""
        try:
            return obj.attrs[self.index]
        except KeyError:
            return None
        
    def __delete__(self, obj):
        """resets attribute's initial state"""
        obj.attrs[self.index] = None


class FloatAttr(Attribute):
    """    FloatAttr class is an Attribute descriptor which tries to convert to 
        float every value set. It should convert mainly strings though numeric 
        types such as int and decimal could be set.
    """
    def __init__(self, thousandsep=None, decimalsep=None, percentage=False, **kwargs):
        super(FloatAttr, self).__init__(**kwargs)
        self.decimalsep = decimalsep
        self.percentage = percentage
        self.thousandsep = thousandsep
    
    def parse(self, value):
        if type(value) in (str, unicode):
            if self.thousandsep is not None:
                value = value.replace(self.thousandsep, '')
            if self.decimalsep is not None:
                value = value.replace(self.decimalsep, '.')
            if self.percentage:
                value = value.replace('%', '')
        if self.percentage:
            value = float(value)/100
        else:
            value = float(value)
        return value


def lxml_parser(content, scrap):
    doc = html.document_fromstring(content)
    for k, xpath in scrap.xpaths.items():
        elms = doc.xpath(xpath)
        setattr(scrap, k, [r.text.strip() if r.text else '' for r in elms])


# class MyScrap(Scrap):
#     a1 = FloatAttr(xpath='//td[@class="tabelaConteudo1"]|//td[@class="tabelaConteudo2"]', decimalsep=',')
#     b1 = Attribute(xpath='//*[@class="tabelaItem"]', transform=len)
#
#
# scrap = MyScrap()
# url = 'http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/TxRef1.asp?slcTaxa=PRE'
# r = requests.get(url)
# lxml_parser(r.text, scrap)
# print scrap
#
# pop = lambda x: x.pop()
# first = lambda x: x[0]
# last = lambda x: x[-1]
#
# class MyScrap(Scrap):
#     a1 = FloatAttr(xpath='//*[@id="ctl00_Banner_lblTaxDI"]', decimalsep=',', percentage=True, transform=first)
#
# scrap = MyScrap()
# url = 'http://www.cetip.com.br'
# r = requests.get(url)
# lxml_parser(r.text, scrap)
# print scrap
#
#
class MyScrap(Scrap):
    data = Attribute(xpath='//table[@id="tblDadosAjustes"]/tr[@class="tabelaConteudo1"]/td|//table[@id="tblDadosAjustes"]/tr[@class="tabelaConteudo2"]/td')
    header = Attribute(xpath='//table[@id="tblDadosAjustes"]/*/td[@class="tabelaTitulo"]')

scrap = MyScrap()
url = 'http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/Ajustes1.asp'
r = requests.get(url)
scrap.lxml_parser(r.text)

l = len(scrap.header)
data = [tuple(scrap.data[i:i+l]) for i in range(0, len(scrap.data), l)]

def fulfill(x, y):
    x.append(y if y else x[-1])
    return x

col1 = [x.split('-')[0].strip() for x in reduce(fulfill, [row[0] for row in data], [])]

data2 = [(cel0+row[1], row[1], row[3]) for row, cel0 in zip(data, col1)]

print data2