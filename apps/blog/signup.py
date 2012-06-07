import os, sys, webapp2, jinja2, re, markupsafe, cgi
from markupsafe import Markup, escape
from google.appengine.ext import db
from lib import passwordhash

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
        
#form validation       
def valid_user_test(username):
    USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    return USER_RE.match(username)

def duplicate_user(username):
    q = Users.all().filter('user', username)
    entity = q.get()
    return (True, entity) if entity else (False, None)
      
def valid_pass_test(password):
    PASS_RE = re.compile(r"^.{3,20}$")
    return PASS_RE.match(password)
    
def valid_email_test(email):
    EMAIL_RE = re.compile("^[\S]+@[\S]+\.[\S]+$")
    return EMAIL_RE.match(email)

def escape_html(s):
    return cgi.escape(s, quote = True)       
  
  
#db model for user/pass
class Users(db.Model):
    user = db.StringProperty(required=True)
    password = db.StringProperty(required=True)
    email = db.EmailProperty()
  
class SignupHandler(Handler):
    def write_form(self, user_error='', pass_error='', valid_error='', email_error='', username='', email=''):
        self.render("signup.html", user_error=user_error,
                                   pass_error=pass_error,
                                   valid_error=valid_error,
                                   email_error=email_error,
                                   username=username,
                                   email=email)
                                   
    
    def get(self):
        self.write_form()
        
    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        verify = self.request.get('verify')
        email = self.request.get('email')
        
        #error checking
        user_error = ''
        if not valid_user_test(username):
            user_error = "That's not a valid username."
        if duplicate_user(username)[0]:
            user_error = "That username is taken." 
        pass_error = "That wasn't a valid password." if not valid_pass_test(password) else ''
        valid_error = "Your passwords didn't match." if password != verify else ''
        email_error = "That's not a valid email." if (len(email) > 0 and not valid_email_test(email)) else ''
  
        if len(user_error) > 0 or len(pass_error) > 0 or len(valid_error) > 0 or len(email_error) > 0:
            self.write_form(user_error, pass_error, valid_error, email_error, username, email)    
        #if no errors:
        else:
            #hash password
            pw_hash = passwordhash.make_pw_hash(username, password) #returns hash,salt
            
            #add user and hashed pass+salt to db
            c = Users(user=username, password=pw_hash)
            if len(email)>0:
                c.email = email
            c.put()
            
            #get user_id
            user_id = c.key().id()
            
            #set cookie in form 'user_id=id#|pw_hash-salt
            self.response.headers.add_header('Set-Cookie', 'user_id=%s|%s; Path=/' % 
                                                (user_id, pw_hash.split(',')[0]))
            self.redirect('/blog/welcome')


class LoginHandler(Handler):
    def write_form(self, error=''):
        self.render("login.html", error=error)
    
    def get(self):
        id_cookie = self.request.cookies.get('user_id')
        if id_cookie:
            self.redirect('/blog/welcome')
        else:
            self.write_form()
            
    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        
        user_persist = self.request.get('persist')
        expires = ''
        if user_persist == 'on':
            expires = "Wed, 01-Jan-3000 23:59:59 GMT"
        
        user_check, entity = duplicate_user(username)
        if user_check and passwordhash.valid_pw(username, password, entity.password):
            user_id = entity.key().id()
            self.response.headers.add_header('Set-Cookie', 'user_id=%s|%s; Path=/; Expires=%s; ' % 
                                             (user_id, str(entity.password.split(',')[0]), expires)
                                             )
            self.redirect('/blog')
        else:
            self.write_form(error="invalid login")

class LogoutHandler(Handler):
    def get(self):
        id_cookie = self.request.cookies.get('user_id')
        if id_cookie:
            self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')
        self.redirect('/blog')
        
        
class WelcomeHandler(webapp2.RequestHandler):
    def get(self):
        id_cookie = self.request.cookies.get('user_id')
        if id_cookie:
            id = id_cookie.split('|')[0]
            username = Users.get_by_id(int(id)).user
            self.response.out.write("""<h1>Welcome, %s!</h1>
                                        <a href="/blog">Blog Homepage</a>
                                    """ % username)
        else:
            self.redirect('/blog/signup')
        
            
app = webapp2.WSGIApplication([('/blog/signup', SignupHandler),
                               ('/blog/welcome', WelcomeHandler),
                               ('/blog/login', LoginHandler),
                               ('/blog/logout', LogoutHandler)
                              ], debug=True)            
