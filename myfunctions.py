from decimal import Decimal, InvalidOperation
from functools import reduce
from collections import namedtuple
from itertools import izip
from re import sub


def each_cons(xs, n):
    return izip(*(xs[i:] for i in xrange(n)))


def validtag(tag):
    try:
        tag['colspan']
        return False
    except KeyError:
        return True


def parse_int(field, thousands_sep=','):
    field = field.strip()
    try:
        return int(field)
    except ValueError:
        try:
            return int(field.replace(thousands_sep, ''))
        except ValueError:
            return None


def parse_float(field, decimal_sep='.', thousands_sep=','):
    field = field.strip()
    try:
        return float(field)
    except ValueError:
        try:
            return float(field.replace(thousands_sep, '').replace(decimal_sep, '.'))
        except ValueError:
            try:
                return float(field.replace(thousands_sep, '').replace(decimal_sep, '.').replace(' ', '').replace('%', ''))/100
            except ValueError:
                return None


def parse_decimal(field, decimal_sep='.', thousands_sep=','):
    field = field.strip()
    try:
        return Decimal(field)
    except InvalidOperation:
        try:
            return Decimal(field.replace(thousands_sep, '').replace(decimal_sep, '.'))
        except InvalidOperation:
            try:
                return Decimal(field.replace(thousands_sep, '').replace(decimal_sep, '.').replace(' ', '').replace('%', ''))/100
            except InvalidOperation:
                return None


def parse_field(field, decimal_sep='.', thousands_sep=','):
    value = parse_int(field, thousands_sep)
    if value:
        return value
    value = parse_decimal(field, decimal_sep, thousands_sep)
    if value:
        return value
    return field


def pprinttable(rows):
    output = ''
    if len(rows) > 1:
        headers = rows[0]._fields
        lens = []
        for i in range(len(rows[0])):
            _col = [x[i] for x in rows] + [headers[i]]
            _max_str = unicode(max( _col, key=lambda x:len(unicode(x)) ))
            lens.append(len(_max_str))
        formats = []
        hformats = []
        for i in range(len(rows[0])):
            # if isinstance(rows[0][i], int):
            #     formats.append("%%%dd" % lens[i])
            # else:
            formats.append("%%-%ds" % lens[i])
            hformats.append("%%-%ds" % lens[i])
        pattern = " | ".join(formats)
        hpattern = " | ".join(hformats)
        separator = "-+-".join(['-' * n for n in lens])
        output += (hpattern % tuple(headers)) + '\n'
        output += separator + '\n'
        for line in rows:
            output += (pattern % tuple(line)) + '\n'
    elif len(rows) == 1:
        row = rows[0]
        hwidth = len(max(row._fields,key=lambda x: len(x)))
        for i in range(len(row)):
            output += ("%*s = %s" % (hwidth,row._fields[i],row[i])) + '\n'
    return output


def compose(*functions):
    def compose2(f, g):
        return lambda x: f(g(x))
    return reduce(compose2, functions)


def parse_table(table, d_sep, t_sep):
    table_rows = table('tr')
    # header = table_rows[0]
    tbody = table_rows[1:]
    
    # parse header -- 1st row
    cols = sum(map(lambda x: int(validtag(x)), table('th')))
    Row = namedtuple('Row', ['V{0}'.format(i) for i in range(1, cols+1)])
    
    # parse table body -- the rest
    _parse_field = compose(lambda x: parse_field(x, d_sep, t_sep),
        lambda x: sub('\s+', ' ', x),
        lambda x: x.strip(),
        lambda x: x.get_text())
    def _process_row(row, cols):
        tds = row('td')
        def _process_cell(x):
            try:
                return _parse_field(tds[x])
            except:
                return None
        return [_process_cell(i) for i in range(cols)]
    rows = [_process_row(row, cols) for row in tbody]
    # values = [_parse_field(tag) for tag in table('td')]
    # rows = len(values)/cols
    
    # return [Row(*values[(i*cols):(i*cols+cols)]) for i in range(rows)]
    return [Row(*row) for row in rows if any(map(lambda x: x is not None, row))]
    