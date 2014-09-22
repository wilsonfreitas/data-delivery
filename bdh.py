# coding: utf-8

import logging
from itertools import izip
from datetime import datetime

from bizdays import Calendar

from welgae import *
import ANBIMA

@route(r'/bizdays')
@route(r'/bizdays/')
class IndexHandler(WelHandler):
    def get(self):
        nwd = self.request.get("nwd", ('Saturday', 'Sunday'))
        holidays = self.request.get('holidays', [d.isoformat() for d in ANBIMA.holidays])
        context = {'nwd': nwd, 'holidays': holidays, 'weekdays': Calendar._weekdays}
        self.render_template('bizdays/index', **context)
    
    
    def post(self):
        nwd = self.request.get("nwd", ('Saturday', 'Sunday'))
        holidays = self.request.get('holidays', '\n'.join([d.isoformat() for d in ANBIMA.holidays]))
        holidays = holidays.split()
        cal = Calendar([datetime.strptime(d, '%Y-%m-%d').date() for d in holidays], weekdays=nwd)
        dates_from = self.request.get('from')
        dates_from = dates_from.split() if dates_from else None
        dates_to = self.request.get('to')
        dates_to = dates_to.split() if dates_to else None
        if dates_to and dates_to:
            bd = [unicode(cal.bizdays(t)) for t in izip(dates_from, dates_to)]
            logging.info(bd)
        else:
            bd = None
        context = {
            'nwd': nwd,
            'holidays': holidays, 
            'weekdays': Calendar._weekdays,
            'from': dates_from,
            'to': dates_to,
            'bd': bd
        }
        self.render_template('bizdays/index', **context)

# Declaring app -- instantiated in welgae

app = welapp