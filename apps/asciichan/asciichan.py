#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os, webapp2, jinja2, urllib2, logging
from xml.dom import minidom
from google.appengine.ext import db
from google.appengine.api import memcache

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)


def get_coords(ip):
    ip = '4.2.2.2'
    ip = '23.24.209.141'
    url = "http://api.hostip.info/?ip=" + ip
    content = None
    try:
        content = urllib2.urlopen(url).read()
    except URLError:
        return

    if content:
        x = minidom.parseString(content)
        coords = x.getElementsByTagName("gml:coordinates")
        if coords and coords[0].childNodes[0].nodeValue:
            lon, lat = coords[0].childNodes[0].nodeValue.split(',')
            return db.GeoPt(lat, lon)
        
GMAPS_URL = "http://maps.googleapis.com/maps/api/staticmap?size=380x263&sensor=false&"

def gmaps_img(points):
    markers = '&'.join('markers=%s,%s' % (p.lat, p.lon) for p in points)
    return GMAPS_URL + markers
    
        
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
        
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))


class Art(db.Model):
    title = db.StringProperty(required = True)
    art = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    coords = db.GeoPtProperty()

    
def top_arts(update = False):
    key = 'top'
    arts = memcache.get(key)
    if arts is None or update:
        logging.error("DB QUERY")
        arts = db.GqlQuery("SELECT * FROM Art ORDER BY created DESC")
        
        arts = list(arts)
        memcache.set(key, arts)
    return arts
        
class MainPage(Handler):
    def render_front(self, title="", art="", error=""):
        arts = top_arts()

        #find which arts have coords
        points = filter(None, (a.coords for a in arts))
        
        #if we have any arts coords, make an image urllib
        img_url = None
        if points:
            img_url = gmaps_img(points)
        
        self.render("ascii.html", title=title, art=art, error=error, arts=arts, img_url = img_url)

    def get(self):
        
        self.render_front()
        
    def post(self):
        title = self.request.get("title")
        art = self.request.get("art")
        
        if title and art:
            a = Art(title=title, art=art)
            coords = get_coords(self.request.remote_addr)
            if coords:
                a.coords = coords
            a.put()
            top_arts(True) #rerun query and update cache
            
            self.redirect("/asciichan")
        else:
            error = "we need both a title and some artwork!"
            self.render_front(title, art, error)

                             
app = webapp2.WSGIApplication([('/asciichan', MainPage)
                              ], debug=True)
