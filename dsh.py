# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from bs4 import BeautifulSoup
from google.appengine.api import urlfetch
from myfunctions import parse_table as pt
from myfunctions import pprinttable


def index(_write_tmpl, **kwargs):
    error = ''
    result = ''
    occurrences = 0
    occurrence = int(kwargs.get('occurrence', 0))
    url = kwargs.get('url')
    fetch_result = urlfetch.fetch(url)
    gettext = kwargs.get('gettext', '')
    css = kwargs.get('css')
    col_number = kwargs.get('col_number')
    parse_table = kwargs.get('parse_table', '')
    decimal_sep = kwargs.get('decimal_sep', '.')
    thousands_sep = kwargs.get('thousands_sep', ',')
    if fetch_result.status_code == 200:
        soup = BeautifulSoup(fetch_result.content)
        result = soup.select(css)
        occurrences = len(result)
        if parse_table:
            if occurrence:
                _rows = pt(result[occurrence-1], decimal_sep, thousands_sep)
            else:
                _rows = pt(result[0], decimal_sep, thousands_sep)
            result = [pprinttable(_rows)]
        else:
            if gettext:
                result = [text.get_text() for text in result]
            else:
                result = [text.prettify() for text in result]
            if occurrence:
                result = [result[occurrence-1]]
            else:
                result = [tok.strip() for tok in result if tok.strip()]
    else:
        error = 'status_code = %d' % fetch_result.status_code
    _write_tmpl('templates/index.html', {
        'url': url,
        'css': css,
        'error': error,
        'result': result,
        'gettext': gettext,
        'col_number': col_number,
        'occurrence': occurrence,
        'occurrences': occurrences,
        'parse_table': parse_table,
        'decimal_sep': decimal_sep,
        'thousands_sep': thousands_sep
    })


html = '''
<table align="center" cellpadding="1" cellspacing="1" class="tabelaTaxaSelic">
 <tr>
  <th rowspan="2">
   Data
  </th>
  <th rowspan="2">
   Taxa (%a.a.)
  </th>
  <th rowspan="2">
   Fator diário
  </th>
  <th rowspan="2">
   Base de cálculo (R$)
  </th>
  <th colspan="5">
   Estatísticas
  </th>
 </tr>
 <tr>
  <th>
   Média
  </th>
  <th>
   Mediana
  </th>
  <th>
   Moda
  </th>
  <th>
   Desvio padrão
  </th>
  <th>
   Índice de curtose
  </th>
 </tr>
 <tr>
  <td>
   02/05/2014
  </td>
  <td>
   10,90
  </td>
  <td>
   1,00041063
  </td>
  <td>
   266.004.322.181,56
  </td>
  <td>
   10,90
  </td>
  <td>
   10,89
  </td>
  <td>
   10,90
  </td>
  <td>
   0,03
  </td>
  <td>
   292,49
  </td>
 </tr>
</table>
'''
