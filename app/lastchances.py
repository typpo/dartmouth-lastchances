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
from dndremote import DNDRemoteLookup

from django.utils import simplejson as json
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import mail

from settings import DEBUG

CAS_URL = 'https://login.dartmouth.edu/cas/'
if DEBUG:
    SERVICE_URL = 'http://localhost:8080/login'
else:
    SERVICE_URL = 'http://dartmouthlastchances.appspot.com/login'
LOGOUT_URL = 'https://login.dartmouth.edu/cas/logout?service='+SERVICE_URL

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
        args = dict(user=self.current_user, logout_url=LOGOUT_URL)
        self.response.out.write(template.render('templates/index.html', args))


class LoginHandler(BaseHandler):
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
        

class EntryHandler(BaseHandler):
    def get(self): 
        if not self.current_user:
            # TODO redirect
            self.response.out.write('You must be logged in')
            return

        id = self.current_user
        u = User.get_by_key_name(id)
        if not u:
            # We have a new user
            # TODO check name against list of allowed people
            u = User(key_name=id, id=id)
            u.save()

        # Generate response
        self.render_main()


    def post(self):
        if not self.current_user:
            args = dict(user=self.current_user, logout_url=LOGOUT_URL)
            self.response.out.write(template.render('templates/index.html', args))
            return

        results = db.GqlQuery("SELECT * FROM Crush WHERE id='%s' ORDER BY created" % (self.current_user))
        orig_crushes = [x.crush for x in results]

        names = self.request.POST.getall('c')
        orig = self.request.POST.getall('o')

        # First handle deletion
        for crush in orig_crushes:
            if crush not in names:
                c = Crush.get_by_key_name(self.current_user+crush)
                if c:
                    c.delete()

        # Now add anything new
        d = DNDRemoteLookup()
        dndnames = d.lookup(names)
        new_crushes = []
        comments = []
        i = 0
        for name in names:
            if name == '':
                i+=1
                continue

            # Check if it's already there
            if name in dndnames and len(dndnames[name])==1:
                c = Crush.get_by_key_name(self.current_user+':'+dndnames[name][0]) 
            else:
                c = None

            if c:
                comments.append('')
                new_crushes.append(dndnames[name][0])
            else:
                # New crush
                if len(dndnames[name]) == 0:
                    # No good
                    comments.append('Couldn\'t find name in DND')
                    new_crushes.append('')
                elif len(dndnames[name]) == 1:
                    # Add crush
                    resolved_name = dndnames[name][0]
                    c = Crush(key_name=self.current_user+':'+resolved_name, id=self.current_user, crush=resolved_name)
                    c.put()
                    comments.append('Saved')
                    new_crushes.append(resolved_name)
                else:
                    # Unspecific - let them choose
                    links = ['<a href="#" onClick="document.getElementById(\'c%d\').value=\'%s\';return False;">%s</a>' \
                             % (i,x,x) for x in dndnames[name]]
                    comments.append('Did you mean: ' + ', '.join(links))
                    new_crushes.append('')
            i += 1

        self.render_main(crushes=new_crushes, comments=comments)


    def render_main(self, crushes=None, comments=['']*10):
        # Display entry page, with errors, etc.

        if not crushes:
            # Get default entries
            results = db.GqlQuery("SELECT * FROM Crush WHERE id='%s' ORDER BY created" % (self.current_user))
            crushes = [x.crush for x in results]

        # Pad lists
        crushes += ['']*(10-len(crushes))
        comments += ['']*(10-len(comments))

        args = dict(id=self.current_user, v=crushes, comments=comments, logout_url=LOGOUT_URL)
        self.response.out.write(template.render('templates/entry.html', args))


class MatchHandler(webapp.RequestHandler):
    def get(self):
        crushes = Crush.all()
        # Create dict, keyed by crusher, value crushee
        d = {}
        for entry in crushes:
            key = entry.id + ':' + entry.crush
            d[key] = entry

        for key in d:
            matchkey = d[key].crush+ ':' + d[key].id
            # If there's a match, we expect to see this key
            if matchkey in d:
                self.response.out.write('%s matches %s!<br>\n' % (d[key].id, d[key].crush))

        self.response.out.write('Done')


class TestHandler(webapp.RequestHandler):
    def get(self):
        name = self.request.get('name')
        crush = self.request.get('crush')
        c = Crush(key_name=name+':'+crush, id=name, crush=crush)
        c.put()


            
def main():
    util.run_wsgi_app(webapp.WSGIApplication([
        (r"/", HomeHandler),
        (r"/login", LoginHandler),
        (r"/entry", EntryHandler),
        (r"/match", MatchHandler),
        (r"/addtestcrush", TestHandler),
    ]))


if __name__ == "__main__":
    main()
