#!/usr/bin/env python
#
# Google App Engine app for Dartmouth last chances
#


import logging
import wsgiref.handlers
import os
import cgi
from cas import CASClient

from django.utils import simplejson as json
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import mail

CAS_URL = 'https://login.dartmouth.edu/cas/'
SERVICE_URL = 'http://localhost:8080'

class User(db.Model):
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)


class Crush(db.Model):
    id = db.StringProperty(required=True)
    crush = db.StringProperty(required=True)


class HomeHandler(webapp.RequestHandler):
    def get(self):
        c = CASClient(CAS_URL, SERVICE_URL)
        id = c.Authenticate(self.request.get('ticket', None))
        # TODO lookup, etc.
        u = User(key_name=id)
        u.save()
        args = dict(id=id)
        self.response.out.write(template.render('index.html', args))


def main():
    util.run_wsgi_app(webapp.WSGIApplication([
        (r"/", HomeHandler),
    ]))


if __name__ == "__main__":
    main()
