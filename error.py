
import os, webapp2, jinja2, re

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

#helper handler to simplify writing and rendering templates
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
        
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

     
class Error(Handler):
    def get(self, _):
        self.render("nopage.html")
        

                        
app = webapp2.WSGIApplication([('/(.*?)', Error)
                              ], debug=True)
