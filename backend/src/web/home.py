# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
# from web import my_form
from tekton import router
from bs4 import BeautifulSoup
from google.appengine.api import urlfetch
from web import dsh

def index(_write_tmpl):
    url = router.to_path(dsh)
    _write_tmpl('templates/index.html', {'form_url': url})


