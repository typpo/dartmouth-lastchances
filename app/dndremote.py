import logging
import urllib
from google.appengine.api.urlfetch import fetch
from google.appengine.api import memcache as mc

# This lookup was too slow - took 15+ sec and often timed out.
# Probably better now after the apache wscgi fix:
#REMOTE_LOOKUP = 'http://hacktown.cs.dartmouth.edu/lastchances/lookup.php?names='

# So I set up lookup on my own server...
REMOTE_LOOKUP = 'http://ianww.com/dnd/lookup.php?names=%s&year=%s'

class DNDRemoteLookup:

    def lookup(self, names, year):
        ret = {}


        # Only query the names we don't have memcached
        # TODO could be made even better by caching all blitz nicks, but it's not really a big deal
        less = []
        for x in names:
            if x == '':
                continue
            cached = mc.get(x, namespace='dnd')
            if cached:
                logging.info('DND got %s from cache' % (x))
                ret[x] = cached
            else:
                logging.info('DND need to look up %s' % (x))
                less.append(x)

        #less = [x for x in names if x != '']
        if len(less) > 0:
            l = fetch(REMOTE_LOOKUP % (urllib.quote(','.join(less)), year), deadline=15).content
            results = l.split('#')
            i = 0
            for result in results:
                lines = result.splitlines()
                ret[less[i]] = lines
                # set cache
                # TODO maybe set_multi
                mc.set(less[i], lines, namespace='dnd')
                i += 1
        return ret
