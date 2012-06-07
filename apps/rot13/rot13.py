import webapp2, cgi

rot13form = """
    <h1>Enter some text to ROT13:</h1>
    <form method="post">
        <textarea name="text" style="height: 100px; width: 400px;">%(data)s</textarea>
        <br>
        <br>
        <input type="submit">
    </form>
    """
    
# def rot13(s):
    # result = ''
    # for letter in s:
        # x = ord(letter)
        # if (97 <= x <= 109) or (65 <= x <= 77):
            # result += (chr(x+13))
        # elif 110 <= x <= 122 or (77 <= x <= 90):
            # result += (chr(x-13))
        # else:
            # result += letter
    # return result    
    
class RotThirteenHandler(webapp2.RequestHandler):
    def write_form(self, data=""):
        self.response.out.write(rot13form % {'data': escape_html(data)})
        
    def get(self):
        self.write_form()
        
    def post(self):
        user_data = self.request.get('text')
        self.write_form(user_data.encode('rot13'))
        
def escape_html(s):
    return cgi.escape(s, quote = True)
    
    
app = webapp2.WSGIApplication([('/rot13', RotThirteenHandler)
                              ], debug=True)      