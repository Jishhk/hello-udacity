
import os, sys, webapp2, jinja2, re, markupsafe, json, logging, time, math
from markupsafe import Markup, escape
from google.appengine.ext import db
from google.appengine.api import memcache
from lib import markdown
from signup import Users
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)


def markup_text(text):
    content = text
    if '</textarea>' in content:
        content.replace('</textarea>', '')
    if '</div>' in content:
        content.replace('</div>', '')
    content.replace('\n', '<br>')
    return Markup(markdown.markdown(content))

def remove_html_tags(text):
    p = re.compile(r'<.*?>')
    return p.sub('', text)

#helper handler to simplify writing and rendering templates
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
        
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

#database model
class Blog(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    author = db.ReferenceProperty(Users)
    last_modified = db.DateTimeProperty(auto_now = True)
    
    def markdown(self):
        return markdown.markdown(self.content)

def front_cache(update = False):
    key = 'blog'
    posts = memcache.get(key)
    if posts is None or update:
        logging.error("DB QUERY")
        posts = db.GqlQuery("SELECT * FROM Blog ORDER BY created DESC")
        posts = list(posts)
        memcache.set_multi({key: posts, 'front_queried':time.time()})
    return posts
        
#main blog page found at /blog     
class MainPage(Handler):
    def get(self):
        posts = front_cache()
        queried = int((time.time() - memcache.get('front_queried')) + 0.5)
        
        id_cookie = self.request.cookies.get('user_id')
        if id_cookie:
            id = id_cookie.split('|')[0]
            username = Users.get_by_id(int(id)).user
            login = """Welcome %s! (<a href="/blog/logout">logout</a>)""" % username
        else:
            login = """<a href="/blog/login">login</a> | <a href="/blog/signup">signup</a>"""
        
        self.render("blog.html", posts=posts, login=login, queried=queried)


#handler for /blog/newpost
class NewPost(Handler):
    def render_front(self, subject="", content="", error=""):
        posts = front_cache()
        self.render("newpost.html", subject=subject, content=content, error=error, posts=posts)

    def get(self):
        self.render_front()
        
    def post(self):
        subject = self.request.get("subject")
        content = remove_html_tags(self.request.get("content"))
        password = self.request.get("password")
        
        
        if subject and content:
            c = Blog(subject=subject, content=content)
            c.put()
            front_cache(True)
            key = c.key()
            self.redirect("/blog/%d" % key.id())
        else:
            error = "enter a subject, content and a password please!"
            self.render_front(subject, content, error)

def perma_cache(id, update = False):
    post = memcache.get(id)
    if post is None or update:
        logging.error("DB QUERY")
        post = Blog.get_by_id(int(id))
        memcache.set_multi({id: post, 'perma_'+id:time.time()})
    return post
            
#handler for /blog/(permalink id for post)
class PermaLink(Handler):
    def get(self, page_number):
        post = perma_cache(page_number)
        queried = int((time.time() - memcache.get('perma_'+page_number)) + 0.5)
        if post:
            self.render("permalink.html", post=post, queried=queried)
        else:
            self.render("nopage.html")
            
    def post(self, page_number):
        password = self.request.get("password")
        if password == "sheisit13":
            post = Blog.get_by_id(int(page_number))
            post.delete()
            self.redirect("/blog?deleted=true")
        else:
            self.redirect("/blog/%(id)d?deleted=false&id=%(id)d" % {'id': post.key().id()})
            

#handler for editing pages            
class EditPage(Handler):
    def render_page(self, subject="", content="", error=""):
        self.render("editpage.html", subject=subject, content=content, error=error)

    def get(self, page_number):
        post = perma_cache(page_number)
        if post:
            self.render_page(subject=post.subject, content=post.content)
        else:
            self.render("nopage.html")

    def post(self, page_number):
        subject = self.request.get("subject")
        content = remove_html_tags(self.request.get("content"))
        password = self.request.get("password")
        c = perma_cache(page_number)
        
        if subject and content and len(password)>0:
            
            c.subject = subject
            c.content = content
            c.put()
            front_cache(True)
            perma_cache(page_number, True)
            key = c.key()
            self.redirect("/blog/%d/editsuccess" % key.id())
        else:
            error = "enter a subject, content and a password please!"
            self.render_page(subject=subject, content=content, error=error)

class EditSuccess(Handler):
    def get(self, page_number):
        post = perma_cache(page_number)
        self.render("editsuccess.html", post=post)


#json creation
class JsonFront(Handler):
    def get(self):
        posts = front_cache()
        d = []
        for post in posts:
            d.append({"content": post.content, 
                         "created": post.created.strftime('%c'),
                         "last_modified": post.last_modified.strftime('%c'),
                         "subject": post.subject
                      })
        self.response.headers['Content-Type'] = 'application/json'
        self.write(json.dumps(d))
        
class JsonPost(Handler):
    def get(self, post_id):
        post = perma_cache(page_number)
        self.response.headers['Content-Type'] = 'application/json'
        self.write(json.dumps({"content": post.content, 
                               "created": post.created.strftime('%c'),
                               "last_modified": post.last_modified.strftime('%c'),
                               "subject": post.subject}
                              )
                   )

class FlushHandler(Handler):
    def get(self):
        memcache.flush_all()
        self.redirect('/blog')
        
app = webapp2.WSGIApplication([('/blog', MainPage),
                               ('/blog/newpost', NewPost),
                               (r'/blog/(\d+)', PermaLink),
                               (r'/blog/(\d+)/edit', EditPage),
                               (r'/blog/(\d+)/editsuccess', EditSuccess),
                               (r'/blog/.json', JsonFront),
                               (r'/blog/(\d+)/.json', JsonPost),
                               (r'/blog/(\d+).json', JsonPost),
                               (r'/blog/flush', FlushHandler)
                              ], debug=True)
