import webapp2
import jinja2
import os

__all__ = ['WelHandler', 'welapp', 'render_template', 'route', 'route_to']

class WelHandler(webapp2.RequestHandler):
    def get(self):
        self.render_template()
    
    def default_template(self):
        return type(self).__name__.replace('Handler', '').lower()
    
    def render_template(self, *args, **variables):
        if len(args) > 0:
            template = args[0]
        else:
            template = self.default_template()
        self.response.write(render_template(template, **variables))


def custom_dispatcher(router, request, response):
    rv = router.default_dispatcher(request, response)
    if isinstance(rv, basestring):
        rv = webapp2.Response(rv)
    elif isinstance(rv, tuple):
        rv = webapp2.Response(*rv)
    return rv

app = webapp2.WSGIApplication(debug=True)
app.router.set_dispatcher(custom_dispatcher)
welapp = app

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
        'templates')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

def render_template(template, **variables):
    jj = JINJA_ENVIRONMENT.get_template('%s.html' % template)
    return jj.render(variables)

def set_app(app):
    def wrapper(func):
        return lambda *args, **kwargs: func(*( (app,) + args ), **kwargs)
    return wrapper

@set_app(app)
def route(*args, **kwargs):
    def wrapper(handler):
        _route = webapp2.Route(handler=handler, name=handler.__name__,
                               *args[1:], **kwargs)
        args[0].router.add(_route)
        return handler
    return wrapper

def route_to(handler, *args, **kwargs):
    return webapp2.uri_for(handler.__name__, *args, **kwargs)

