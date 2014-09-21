# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from bs4 import BeautifulSoup
from google.appengine.api import urlfetch

from myfunctions import parse_table as pt
from myfunctions import pprinttable

from welgae import *
import webapp2

@route(r'/')
class IndexHandler(WelHandler):
    def get(self):
        self.render_template()

# Declaring app -- instantiated in welgae

app = welapp