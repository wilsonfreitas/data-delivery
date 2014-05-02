# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from bs4 import BeautifulSoup
from google.appengine.api import urlfetch

def index(_write_tmpl, _req, url, css, gettext):
    error = ''
    result = ''
    fetch_result = urlfetch.fetch(url)
    if fetch_result.status_code == 200:
        soup = BeautifulSoup(fetch_result.content)
        result = soup.select(css)
    else:
        error = 'status_code = %d' % fetch_result.status_code
    _write_tmpl('templates/index.html', {
        'url': url,
        'css': css,
        'error': error,
        'result': result,
        'gettext': 'checked'
    })
