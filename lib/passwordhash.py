import random
import string
import hashlib

# implement the function make_salt() that returns a string of 5 random
# letters use python's random module.
# Note: The string package might be useful here.

def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))


# implement the function make_pw_hash(name, pw) that returns a hashed password
# of the format:
# HASH(name + pw + salt),salt
# use sha256

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    return '%s,%s' % (hashlib.sha256(name + pw + salt).hexdigest(), salt)


def valid_pw(name, pw, h):
    salt = h.split(',')[1]
    return h == make_pw_hash(name, pw, salt)



