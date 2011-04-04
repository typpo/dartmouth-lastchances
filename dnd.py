import socket
import logging
import urllib
from google.appengine.api.urlfetch import fetch

DND_SERVER = 'dnd.dartmouth.edu'
DND_PORT = 902
REMOTE_LOOKUP = 'http://hacktown.cs.dartmouth.edu/lastchances/lookup.php?names='

class DNDLookup:
    
    def __init__(self, server=DND_SERVER, port=DND_PORT):
        self.server = server
        self.port = port

    def connect(self):
        if hasattr(self, 's'):
            return True

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.server, self.port))

        chunk = self.s.recv(512)
        if chunk == '':
            print 'DND: Connect to server failed'
            return False

        return True


    def remote_lookup(self, names):
        less = [x for x in names if x != '']
        l = fetch(REMOTE_LOOKUP + urllib.quote(','.join(less)), deadline=15).content
        results = l.split('#')
        ret = {}
        i = 0
        for result in results:
            lines = result.splitlines()
            ret[less[i]] = lines
            i += 1
        return ret


    def lookup(self, name):
        if not self.connect():
            print 'DND: Not connected to server'
            return False

        if self.s.send('LOOKUP %s, email\r\n' % (name)) == 0:
            print 'DND: Lookup failed'
            return False

        resp = ''
        while True:
            chunk = self.s.recv(512)
            resp += chunk
            if chunk == '' or chunk.endswith('200 Ok.\r\n') \
               or chunk.endswith('201 Additional matching records not returned.\r\n'):
                break

        lines  = resp.splitlines()
        return [l[4:] for l in lines if l.startswith('110 ')]

    def close(self):
        self.s.close()
