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
from dnd import DNDLookup

from django.utils import simplejson as json
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import mail

CAS_URL = 'https://login.dartmouth.edu/cas/'
SERVICE_URL = 'http://localhost:8080/login'

class User(db.Model):
    id = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)


class Crush(db.Model):
    id = db.StringProperty(required=True)
    crush = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)


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
                sess['id'] = id[:id.find('@')]
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
        if u:
            # Get default entries
            results = db.GqlQuery("SELECT * FROM Crush WHERE id='%s'" % (sess['id']))
            crushes = [x.crush for x in results]

            # Pad list
            crushes += ['']*(10-len(crushes))
        else:
            # TODO new user - lookup name and check against list of allowed people
            crushes = ['']*10
            u = User(key_name=id, id=id)
            u.save()

        # Generate response
        errs = ['']*10
        args = dict(id=sess['id'], v=crushes, errs=errs)
        self.response.out.write(template.render('entry.html', args))


    def post(self):
        sess = sessions.Session()
        if not 'id' in sess:
            self.response.out.write('You must be logged in')
            return

        errs = ['']*10
        d = DNDLookup()
        names = self.request.POST.getall('c')
        dndnames = d.remote_lookup(names)
        logging.warning(dndnames)
        i = 0
        for name in names:
            if names[i] == '':
                # TODO deletion
                i += 1
                continue

            logging.warning('processing ' + name)

            # Check if it's already there
            if name in dndnames and len(dndnames[name])==1:
                c = Crush.get_by_key_name(sess['id']+dndnames[name][0]) 
            else:
                c = None

            if not c:
                # New crush
                logging.warning('new crush!')
                if len(dndnames[name]) == 0:
                    errs[i] = 'Could not find this name in the DND'
                elif len(dndnames[name]) == 1:
                    # TODO memcache dnd lookup?
                    c = Crush(key_name=sess['id']+dndnames[name][0], id=sess['id'], crush=dndnames[name][0])
                    c.put()
                else:
                    links = ['<a href="#" onClick="document.getElementById(\'c%d\').value=\'%s\';return False;">%s</a>' % (i,x,x) for x in dndnames[name]]
                    errs[i] = 'Too many names, did you mean: ' + ', '.join(links)

            i += 1

        # Display entry page, with errors, etc.

        # Get default entries
        results = db.GqlQuery("SELECT * FROM Crush WHERE id='%s' ORDER BY created" % (sess['id']))
        crushes = [x.crush for x in results]

        # Pad list
        crushes += ['']*(10-len(crushes))

        args = dict(id=sess['id'], v=crushes, errs=errs)
        self.response.out.write(template.render('entry.html', args))

            
def main():
    util.run_wsgi_app(webapp.WSGIApplication([
        (r"/", HomeHandler),
        (r"/login", LoginHandler),
        (r"/entry", EntryHandler),
    ]))


if __name__ == "__main__":
    main()
