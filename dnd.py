import socket

DND_SERVER = 'dnd.dartmouth.edu'
DND_PORT = 902

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
        ret = []
        for l in lines:
            if l.startswith('110 '):
                ret.append(l[4:])
        return ret

    def close(self):
        self.s.close()
