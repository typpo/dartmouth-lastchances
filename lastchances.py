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


# TODO abstract all session tracking to base handler

class MainHandler(webapp.RequestHandler):
    def get(self):
        # Login if necessary
        c = CASClient(CAS_URL, SERVICE_URL)
        id = c.Authenticate(self.request.get('ticket', None))

        sess = sessions.Session()
        sess['id'] = id

        self.redirect('/entry')

class EntryHandler(webapp.RequestHandler):
    def get(self): 
        sess = sessions.Session()
        if not 'id' in sess:
            self.response.out.write('You must be logged in')
            return

        id = sess['id']
        u = User.get_by_key_name(id)
        if not u:
            u = User(key_name=id, id=id)
            u.save()

        # Generate response
        args = dict(id=u.id)
        self.response.out.write(template.render('entry.html', args))


def main():
    # TODO replace get started with real home page with intro and link to main
    util.run_wsgi_app(webapp.WSGIApplication([
        (r"/", MainHandler),
        (r"/entry", EntryHandler),
    ]))


if __name__ == "__main__":
    main()
