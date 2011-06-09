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
from google.appengine.api import memcache as mc
from google.appengine.api import taskqueue
from google.appengine.runtime import DeadlineExceededError

from settings import DEBUG, CLASS_YEAR, RELEASE_MATCHES

CAS_URL = 'https://login.dartmouth.edu/cas/'
if DEBUG:
    SERVICE_URL = 'http://localhost:8080/login'
else:
    #SERVICE_URL = 'http://dartmouthlastchances.appspot.com/login'
    SERVICE_URL = 'http://www.dartmouthlastchances.com/login'

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
    id = db.StringProperty(required=True)
    name1 = db.StringProperty(required=True)
    name2 = db.StringProperty(required=True)
    email = db.StringProperty(required=False)


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
                id = sess['id']

                # Try to find user info in memcache
                cache = mc.get(id, namespace='users')
                if cache:
                    logging.info('Found user %s in cache' % (id))
                    u = User(id=id,email=cache['email'])
                else:
                    logging.info('Looking for user %s in store' % (id))
                    u = User.get_by_key_name(id)

                    if u:
                        # Memcache already existing user
                        logging.info('Setting user %s in cache' % (id))
                        mc.set(id, dict(id=u.id, email=u.email), namespace='users')
                    else:
                        # We have a new user
                        logging.info('Creating new user %s' % (id))

                        # Make sure it's the correct class year
                        d = DNDRemoteLookup()
                        dndnames = d.lookup([id], CLASS_YEAR)
                        if id not in dndnames or len(dndnames[id])==0:
                            logging.info('Reject new user %s' % (id))
                            self.response.out.write("Sorry, only the senior class can enter last chances.  If you think there's been a mistake, please contact people running this.")
                            self._current_user = None
                            sess.delete()
                            return None

                        # Add new user
                        email = id.replace(' ','.').replace('..', '.') + '@dartmouth.edu'
                        u = User(key_name=id, id=id, email=email)
                        u.save()

                        # memcache the user
                        mc.set(id, dict(id=id, email=email), namespace='users')

                self._current_user = u
            else:
                self._current_user = None
        return self._current_user


    def render_main(self, crushes=None, comments=['']*11):
        # Display entry page, with errors, etc.

        if not crushes:
            # Get default entries
            query = db.Query(Crush)
            query.filter('id =', self.current_user.id)
            query.order('created')

            results = query.fetch(11)
            crushes = [x.crush for x in results]

        # Pad lists
        crushes += ['']*(11-len(crushes))
        comments += ['']*(11-len(comments))

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
            self.response.out.write('You are not logged in.  <a href="/">Home</a>')
            return

        if RELEASE_MATCHES:
            q = db.Query(Match)
            q.filter('name1 =', self.current_user.id)

            matches = []
            for match in q:
                matches.append(match.name2)

            if len(matches) > 0:
                match = 'Your match(es): %s' % (', '.join(matches))
            else:
                match = 'Sorry, no matches :('

            args = dict(id=self.current_user.id, logout_url=LOGOUT_URL, email=self.current_user.email, match=match)
            self.response.out.write(template.render('templates/match.html', args))
        else:
            # Generate entry response
            self.render_main()


    def post(self):
        if not self.current_user:
            args = dict(user=self.current_user, logout_url=LOGOUT_URL)
            self.response.out.write(template.render('templates/index.html', args))
            return

        try:
            query = db.Query(Crush)
            query.filter('id =', self.current_user.id)
            query.order('created')

            results = query.fetch(11)
            orig_crushes = [x.crush for x in results]

            names = self.request.POST.getall('c')
            orig = self.request.POST.getall('o')

            # First handle deletion
            for crush in orig_crushes:
                if crush not in names:
                    crushkey = self.current_user.id+':'+crush
                    c = Crush.get_by_key_name(crushkey)
                    if c:
                        logging.info('deleting crush %s from cache and store' % (crushkey))
                        c.delete()
                        mc.delete(crushkey, namespace='crushes')

            # Now add anything new
            d = DNDRemoteLookup()
            # TODO not necessary to lookup names that were already in there (even though we memcache lookups)
            dndnames = d.lookup(names, CLASS_YEAR)
            new_crushes = []
            comments = []
            i = 0
            for name in names:
                if name == '':
                    i+=1
                    continue

                # Check if it's already there
                crushkeyname = self.current_user.id+':'+name
                c = mc.get(crushkeyname, namespace='crushes')

                if c != None or Crush.get_by_key_name(crushkeyname):
                    # We also checked that it's in db in case it got evicted from cache
                    if c:
                        logging.info('Found preexisting crush in cache')
                    else:
                        logging.info('Found preexisting crush in store')

                    # Was already validated, so no need to check in dndnames
                    comments.append('')
                    new_crushes.append(name)
                else:
                    # Crush doesn't already exist
                    if len(dndnames[name]) == 0:
                        # No good
                        comments.append('DND couldn\'t find anyone named "%s" in your year' % (cgi.escape(name)))
                        new_crushes.append('')
                    elif len(dndnames[name]) == 1:
                        # New crush
                        resolved_name = dndnames[name][0]
                        crushkeyname = self.current_user.id+':'+resolved_name
                        c = Crush(key_name=crushkeyname, id=self.current_user.id, crush=resolved_name)
                        c.put()
                        mc.set(crushkeyname, True, namespace='crushes')
                        comments.append('Saved')
                        new_crushes.append(resolved_name)
                    else:
                        # Unspecific - let them choose
                        links = ['<a href="#" onClick="document.getElementById(\'c%d\').value=\'%s\';return false;">%s</a>' \
                                 % (i,x,x) for x in dndnames[name]]
                        comments.append('Did you mean: ' + ', '.join(links))
                        new_crushes.append('')
                i += 1

            self.render_main(crushes=new_crushes, comments=comments)

        except DeadlineExceededError:
            self.response.clear()
            self.response.set_status(500)
            self.response.out.write('The operation could not be completed in time.  Try again or contact technical assistance.')


class EmailHandler(BaseHandler):
    def post(self): 
        if self.current_user:
            # Update in actual store
            # (remember self.current_user isn't real datastore user for performance issues)
            logging.info('email change lookup for user %s' % (self.current_user.id))
            u = User.get_by_key_name(self.current_user.id)
            if u:
                newemail = self.request.get('email')     # empty string by default
                u.email = newemail
                u.put()

                # Keep cache up to date
                mc.set(self.current_user.id, dict(id=u.id, email=u.email), namespace='users')

                # Update return
                self.current_user.email = newemail

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

        for key in d:
            if d[key].crush == d[key].id:
                # self-crush
                continue

            matchkey = d[key].crush + ':' + d[key].id
            # If there's a match, we expect to see this key
            if matchkey in d:
                logging.warning('%s matches %s!\n' % (d[key].id, d[key].crush))
                # look up crusher's preferred email
                user = User.get_by_key_name(d[key].id)
                if not user:
                    logging.critical("Couldn't find user for matching %s" % (d[key].id))
                    continue
                m = Match(key_name=key, id=key, name1=d[key].id, name2=d[key].crush, email=user.email)
                m.put()

        self.response.out.write('Done')


class MatchMailHandler(webapp.RequestHandler):
    def get(self):
        us = User.all()
        for u in us:
            q = db.Query(Match)
            q.filter('name1 =', u.id)

            matches = []
            for match in q:
                matches.append(match.name2)

            if len(matches) > 0:
                # send email
                try:
                    taskqueue.add(url='/mailuser', params=dict(key=u.id, to=u.id, about=', '.join(matches), email=u.email))
                except taskqueue.TransientError:
                    logging.critical("Couldn't add task to mail %s for %s" % (u.id))

                self.response.out.write('%s matched %s<br>' % (u.id, ','.join(matches)))
        self.response.out.write('Done')

class MailUserWorker(webapp.RequestHandler):
    def post(self):
        key  = self.request.get('key')
        to = self.request.get('to')
        about = self.request.get('about')
        email = self.request.get('email')

        try:
            #email = to.replace(' ','.').replace('..','.') + '@dartmouth.edu'

            logging.info('ACTUALLY Mailing %s for %s' % (email, about))

            mail.send_mail(
                sender='Last Chances <no-reply@dartmouthlastchances.appspotmail.com>',
                to=email,
                subject='Last Chances Results',
                body='Your last chances match(es) are: %s.' % (about))

            #Match.get_by_key_name(key).delete()
        except:
            logging.critical('Email failed for %s' % (to))



class TestHandler(webapp.RequestHandler):
    def get(self):
        name = self.request.get('name')
        crush = self.request.get('crush')
        key = name+':'+crush
        c = Crush(key_name=key, id=name, crush=crush)
        mc.set(key, True, namespace='crushes')
        c.put()


class ClearMemcacheHandler(webapp.RequestHandler):
    def get(self):
        if mc.flush_all():
            self.response.out.write('ok')
        else:
            self.response.out.write('error')


class ClearAllHandler(webapp.RequestHandler):
    def get(self):
        try:
            if mc.flush_all():
                self.response.out.write('cleared memcache...<br>')
            else:
                self.response.out.write('error clearing memcache')
                return


            us = User.all()
            for u in us:
                u.delete()
            self.response.out.write('cleared users...<br>')

            cs = Crush.all()
            for c in cs:
                c.delete()
            self.response.out.write('cleared crushes...<br>')

            ms = Match.all()
            for m in ms:
                m.delete()
            self.response.out.write('cleared matches...<br>')

            self.response.out.write('Done.  Clear all sessions in app engine admin to be safe')
        except:
            self.response.out.write('error')

class CrushedOnHandler(webapp.RequestHandler):
    def get(self):
        cs = Crush.all()
        d = {}
        for c in cs:
            if c.crush in d:
                d[c.crush] += 1
            else:
                d[c.crush] = 1

        for key, value in sorted(d.iteritems(), key=lambda (k,v): (v,k), reverse=True):
            self.response.out.write('%s: %s<br>' % (key, value))
        self.response.out.write('Done')


class StatsHandler(webapp.RequestHandler):
    def get(self):
        us = User.all()
        c = 0
        for x in us:
            c +=1

        self.response.out.write(str(c) + ' users<br>')

        cs = Crush.all()
        c = 0
        for x in cs:
            c += 1
        self.response.out.write(str(c) + ' crushes<br>')

        ms = Match.all()
        c = 0
        for x in ms:
            c += 1

        self.response.out.write(str(c) + ' matches<br>')
        

            
def main():
    util.run_wsgi_app(webapp.WSGIApplication([
        (r"/", HomeHandler),
        (r"/login", LoginHandler),
        (r"/logout", LogoutHandler),
        (r"/entry", EntryHandler),
        (r"/match", MatchHandler),
        #(r"/mail", MatchMailHandler),
        #(r"/mailuser", MailUserWorker),
        (r"/email", EmailHandler),
        #(r"/clearmemcache", ClearMemcacheHandler),
        #(r"/clearall", ClearAllHandler),
        (r"/crushedon", CrushedOnHandler),
        (r"/stats", StatsHandler),
        #(r"/addtestcrush", TestHandler),
    ]))


if __name__ == "__main__":
    main()
