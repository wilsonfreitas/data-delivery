import requests

# f = open('ipca.html')
# content = f.read()
# content = content.decode('utf-8')
# f.write(g.text.encode('utf-8'))
# f.close()

from lxml import etree
from cssselect import HTMLTranslator

g = requests.get('http://www.cetip.com.br')
# #ctl00_Banner_lblTaxDI
# //*[@id="ctl00_Banner_lblTaxDI"]
tree = etree.HTML(g.text)
res = etree.tostring(tree, pretty_print=True, method="html")
res = tree.xpath('//*[@id="ctl00_Banner_lblTaxDI"]')
print res[0].text

# body > div:nth-child(1) > div:nth-child(17) > table > tbody > tr > td > div > table
# /html/body/div[1]/div[6]/table/tbody/tr/td/div/table

g = requests.get('http://www.portalbrasil.net/ipca.htm')
tree = etree.HTML(g.text)
res = etree.tostring(tree, pretty_print=True, method="html")
xpath = HTMLTranslator().css_to_xpath('table:nth-last-child(1)')
print xpath
res = tree.xpath(xpath)
print etree.tostring(res[0], pretty_print=True, method="html")
# print res


g = requests.get('http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/TxRef1.asp')
tree = etree.HTML(g.text)
res = etree.tostring(tree, pretty_print=True, method="html")
# tit <- xpathSApply(doc, "//td[contains(@class, 'tabelaTitulo')]", xmlValue)
# tit <- str_replace_all(tit, '\\s+', ' ')
# bases <- xpathSApply(doc, "//td[contains(@class, 'tabelaItem')]", xmlValue)
# bases <- str_replace_all(bases, '\\s+', '')
# bases <- str_replace_all(bases, '^(\\d+)[^\\d].*', '\\1')
# bases <- as.numeric(bases)
# num <- xpathSApply(doc, "//td[contains(@class, 'tabelaConteudo')]", xmlValue)
res = tree.xpath("//td[contains(@class, 'tabelaTitulo')]")
print [etree.tostring(e) for e in res]
res = tree.xpath("//td[contains(@class, 'tabelaItem')]")
print [etree.tostring(e) for e in res]
res = tree.xpath("//td[contains(@class, 'tabelaConteudo')]")
print [etree.tostring(e) for e in res]
