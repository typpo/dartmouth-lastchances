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


# Handles sessions
class BaseHandler(webapp.RequestHandler):
    @property
    def current_user(self):
        if not hasattr(self, '_current_user'):
            sess = sessions.Session()
            if 'id' in sess:
                self._current_user = sess['id']
            else:
                self._current_user = None
        return self._current_user

class HomeHandler(BaseHandler):
    def get(self):
        # TODO show matches so far or other interesting statistics
        args = dict(logged_in=True if self.current_user else False)
        self.response.out.write(template.render('index.html', args))


class LoginHandler(BaseHandler):
    def get(self):
        # Login if necessary
        c = CASClient(CAS_URL, SERVICE_URL)
        id = c.Authenticate(self.request.get('ticket', None))

        if id:
            sess = sessions.Session()
            try:
                sess['id'] = id[:id.find('@')]
                sess['id'].put()
                self.redirect('/entry')
                return
            except:
                pass
        self.response.out.write('Login failed')
        

class EntryHandler(BaseHandler):
    def get(self): 
        if not self.current_user:
            self.response.out.write('You must be logged in')
            return

        id = self.current_user
        u = User.get_by_key_name(id)
        if not u:
            # new user
            # TODO lookup name and check against list of allowed people
            u = User(key_name=id, id=id)
            u.save()

        # Generate response
        self.show_page()


    def post(self):
        if not self.current_user:
            self.response.out.write('You must be logged in')
            return

        results = db.GqlQuery("SELECT * FROM Crush WHERE id='%s' ORDER BY created" % (self.current_user))
        orig_crushes = [x.crush for x in results]

        errs = ['']*10
        d = DNDLookup()
        names = self.request.POST.getall('c')
        dndnames = d.remote_lookup(names)
        i = 0
        for name in names:
            if names[i] == '':
                # possible deletion
                if i < len(orig_crushes):
                    c = Crush.get_by_key_name(self.current_user+orig_crushes[i])
                    if c:
                        c.delete()
            else:
                # Check if it's already there
                if name in dndnames and len(dndnames[name])==1:
                    c = Crush.get_by_key_name(self.current_user+dndnames[name][0]) 
                else:
                    c = None

                if not c:
                    # New crush
                    if len(dndnames[name]) == 0:
                        errs[i] = 'Could not find this name in the DND'
                    elif len(dndnames[name]) == 1:
                        # TODO split keyname by non-dnd character
                        c = Crush(key_name=self.current_user+dndnames[name][0], id=self.current_user, crush=dndnames[name][0])
                        c.put()
                    else:
                        links = ['<a href="#" onClick="document.getElementById(\'c%d\').value=\'%s\';return False;">%s</a>' % (i,x,x) for x in dndnames[name]]
                        errs[i] = 'Too many names, did you mean: ' + ', '.join(links)
            i += 1

        self.show_page(errs=errs)


    def show_page(self, errs=['']*10):
        # Display entry page, with errors, etc.

        # Get default entries
        results = db.GqlQuery("SELECT * FROM Crush WHERE id='%s' ORDER BY created" % (self.current_user))
        crushes = [x.crush for x in results]

        # Pad list
        crushes += ['']*(10-len(crushes))

        args = dict(id=self.current_user, v=crushes, errs=errs)
        self.response.out.write(template.render('entry.html', args))

            
def main():
    util.run_wsgi_app(webapp.WSGIApplication([
        (r"/", HomeHandler),
        (r"/login", LoginHandler),
        (r"/entry", EntryHandler),
    ]))


if __name__ == "__main__":
    main()
