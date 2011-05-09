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
from settings import CLASS_YEAR

CAS_URL = 'https://login.dartmouth.edu/cas/'
if DEBUG:
    SERVICE_URL = 'http://localhost:8080/login'
else:
    SERVICE_URL = 'http://dartmouthlastchances.appspot.com/login'

LOGOUT_URL = '/logout'
CAS_LOGOUT_URL = 'https://login.dartmouth.edu/cas/logout?service='+SERVICE_URL


class User(db.Model):
    id = db.StringProperty(required=True)
    email = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)


class Crush(db.Model):
    id = db.StringProperty(required=True)
    crush = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)


class Match(db.Model):
    name1 = db.StringProperty(required=True)
    name2 = db.StringProperty(required=True)
    email1 = db.StringProperty(required=True)
    email2 = db.StringProperty(required=True)


class Stats(db.Model):
    num_matches = db.IntegerProperty(required=True)
    num_participants = db.IntegerProperty(required=True)
    num_entries = db.IntegerProperty(required=True)


# Handles sessions
class BaseHandler(webapp.RequestHandler):
    @property
    def current_user(self):
        if not hasattr(self, '_current_user'):
            sess = sessions.Session()
            if 'id' in sess:
                u = User.get_by_key_name(sess['id'])
                if not u:
                    # We have a new user
                    id = sess['id']

                    # Make sure it's the correct class year
                    d = DNDRemoteLookup()
                    dndnames = d.lookup([id], CLASS_YEAR)
                    if id not in dndnames:
                        # TODO fix this
                        self.response.out.write("Sorry, only the senior class can enter last chances.  If you think there's been a mistake, please contact people running this.")
                        self._current_user = None
                        return None

                    # Add new user
                    email = id.replace(' ','.').replace('..', '.') + '@dartmouth.edu'
                    u = User(key_name=id, id=id, email=email)
                    u.save()

                self._current_user = u
            else:
                self._current_user = None
        return self._current_user


    def render_main(self, crushes=None, comments=['']*10):
        # Display entry page, with errors, etc.

        if not crushes:
            # Get default entries
            query = db.Query(Crush)
            query.filter('id =', self.current_user.id)
            query.order('created')

            results = query.fetch(10)
            crushes = [x.crush for x in results]

        # Pad lists
        crushes += ['']*(10-len(crushes))
        comments += ['']*(10-len(comments))

        args = dict(id=self.current_user.id, v=crushes, comments=comments, logout_url=LOGOUT_URL, email=self.current_user.email)
        self.response.out.write(template.render('templates/entry.html', args))


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
            self.response.out.write('You are not logged in.  <a href="/">Home</a>')
            return

        id = self.current_user.id
        u = User.get_by_key_name(id)
        if not u:
            self.response.out.write('Something went wrong, please try again.  <a href="/">Home</a>')
            return

        # Generate response
        self.render_main()


    def post(self):
        if not self.current_user:
            args = dict(user=self.current_user, logout_url=LOGOUT_URL)
            self.response.out.write(template.render('templates/index.html', args))
            return

        query = db.Query(Crush)
        query.filter('id =', self.current_user.id)
        query.order('created')

        results = query.fetch(10)
        orig_crushes = [x.crush for x in results]

        names = self.request.POST.getall('c')
        orig = self.request.POST.getall('o')

        # First handle deletion
        for crush in orig_crushes:
            if crush not in names:
                c = Crush.get_by_key_name(self.current_user.id+':'+crush)
                if c:
                    c.delete()

        # Now add anything new
        d = DNDRemoteLookup()
        dndnames = d.lookup(names, CLASS_YEAR)
        new_crushes = []
        comments = []
        i = 0
        for name in names:
            if name == '':
                i+=1
                continue

            # Check if it's already there
            if name in dndnames and len(dndnames[name])==1:
                c = Crush.get_by_key_name(self.current_user.id+':'+dndnames[name][0]) 
            else:
                c = None

            if c:
                comments.append('')
                new_crushes.append(dndnames[name][0])
            else:
                # New crush
                if len(dndnames[name]) == 0:
                    # No good
                    comments.append('DND couldn\'t find anyone named "%s" in your year' % (cgi.escape(name)))
                    new_crushes.append('')
                elif len(dndnames[name]) == 1:
                    # Add crush
                    resolved_name = dndnames[name][0]
                    c = Crush(key_name=self.current_user.id+':'+resolved_name, id=self.current_user.id, crush=resolved_name)
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


class EmailHandler(BaseHandler):
    def post(self): 
        if self.current_user:
            self.current_user.email = self.request.get('email')     # empty string by default
            self.current_user.put()
            self.render_main()


class LogoutHandler(BaseHandler):
    def get(self):
        sessions.Session().delete()
        self.redirect(CAS_LOGOUT_URL)


class MatchHandler(webapp.RequestHandler):
    def get(self):
        crushes = Crush.all()

        # Create dict, keyed by crusher, value crushee
        d = {}
        for entry in crushes:
            key = entry.id + ':' + entry.crush
            d[key] = entry

        num = 0
        for key in d:
            matchkey = d[key].crush+ ':' + d[key].id
            # If there's a match, we expect to see this key
            if matchkey in d:
                self.response.out.write('%s matches %s!<br>\n' % (d[key].id, d[key].crush))
                num += 1

        users = User.all()
        s = Stats(key_name='default', num_matches=num, num_entries=len(d), num_participants=len(users))
        s.put()

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
        (r"/logout", LogoutHandler),
        (r"/entry", EntryHandler),
        (r"/match", MatchHandler),
        (r"/email", EmailHandler),
        (r"/addtestcrush", TestHandler),
    ]))


if __name__ == "__main__":
    main()
