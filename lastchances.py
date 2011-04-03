#!/usr/bin/env python
#
# Google App Engine app for Dartmouth last chances
#


import logging
import wsgiref.handlers
import os
import cgi

from cas import CASClient
from appengine_utilities import sessions

from django.utils import simplejson as json
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import mail

CAS_URL = 'https://login.dartmouth.edu/cas/'
SERVICE_URL = 'http://localhost:8080'

class User(db.Model):
    id = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)


class Crush(db.Model):
    id = db.StringProperty(required=True)
    crush = db.StringProperty(required=True)


# TODO abstract all session handling to base handler

class HomeHandler(webapp.RequestHandler):
    def get(self):
        sess = sessions.Session()
        # TODO show matches so far or other interesting statistics
        args = dict(logged_in=True if 'id' in sess else False)
        self.response.out.write(template.render('index.html', args))


class LoginHandler(webapp.RequestHandler):
    def get(self):
        # Login if necessary
        c = CASClient(CAS_URL, SERVICE_URL)
        id = c.Authenticate(self.request.get('ticket', None))

        if id:
            sess = sessions.Session()
            try:
                sess['id'] = id[:id.find('@')].lower()
                self.redirect('/entry')
                return
            except:
                pass
        self.response.out.write('Login failed')
        

class EntryHandler(webapp.RequestHandler):
    def get(self): 
        sess = sessions.Session()
        if not 'id' in sess:
            self.response.out.write('You must be logged in')
            return

        id = sess['id']
        u = User.get_by_key_name(id)
        if not u:
            # TODO lookup name and check against list of allowed people
            u = User(key_name=id, id=id)
            u.save()

        # Generate response
        args = dict(id=u.id)
        self.response.out.write(template.render('entry.html', args))

    def post(self):
        sess = sessions.Session()
        if not 'id' in sess:
            self.response.out.write('You must be logged in')
            return

        # TODO resolve dnd entries

        c1 = self.request.get('c1')
        c2 = self.request.get('c2')
        c3 = self.request.get('c3')
        c4 = self.request.get('c4')
        c5 = self.request.get('c5')
        c6 = self.request.get('c6')
        c7 = self.request.get('c7')
        c8 = self.request.get('c8')
        c9 = self.request.get('c9')
        c10 = self.request.get('c10')


def main():
    util.run_wsgi_app(webapp.WSGIApplication([
        (r"/", HomeHandler),
        (r"/login", LoginHandler),
        (r"/entry", EntryHandler),
    ]))


if __name__ == "__main__":
    main()
