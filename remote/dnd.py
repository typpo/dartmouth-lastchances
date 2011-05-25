#!/usr/bin/env python
#
# DND lookup script restricted to class year
#

import socket
import urllib
import sys

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


    def lookup(self, name, year=''):
        if not self.connect():
            print 'DND: Not connected to server'
            return False

        name = name.decode('string-escape')
        year = year.decode('string-escape')
        if self.s.send("LOOKUP %s %s, name deptclass\r\n" % (name, year)) == 0:
            print 'DND: Lookup failed'
            return False

        resp = ''
        while True:
            chunk = self.s.recv(512)
            resp += chunk
            if chunk == '' or chunk.endswith('200 Ok.\r\n') \
               or chunk.endswith('201 Additional matching records not returned.\r\n') \
               or chunk.endswith('520 No match for that name.\r\n'):
                break

        lines  = resp.splitlines()

        # skip every other because it's a deptclass entry
        lines = [lines[i] for i in range(1, len(lines), 2)]

        return [l[4:] for l in lines if l.startswith('110 ')]

    def close(self):
        self.s.close()


def main():
    d = DNDLookup()
    if len(sys.argv) == 2:
        print '\n'.join(d.lookup(sys.argv[1]))
    else:
        print '\n'.join(d.lookup(sys.argv[1], sys.argv[2]))
    d.close()


if __name__ == '__main__':
    if len(sys.argv) == 2 or len(sys.argv) == 3:
        main()
