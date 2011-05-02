import logging
import urllib
from google.appengine.api.urlfetch import fetch

# This lookup was too slow - took 15+ sec and often timed out.
# Probably better now after the apache wscgi fix:
#REMOTE_LOOKUP = 'http://hacktown.cs.dartmouth.edu/lastchances/lookup.php?names='

# So I set up lookup on my own server...
REMOTE_LOOKUP = 'http://ianww.com/dnd/lookup.php?names='

class DNDRemoteLookup:

    def lookup(self, names):
        less = [x for x in names if x != '']
        if len(less) > 0:
            l = fetch(REMOTE_LOOKUP + urllib.quote(','.join(less)), deadline=15).content
            results = l.split('#')
            ret = {}
            i = 0
            for result in results:
                lines = result.splitlines()
                ret[less[i]] = lines
                i += 1
            return ret
        return {}
