##
# Python CAS client
# Based on https://sp.princeton.edu/oit/sdp/CAS/Wiki%20Pages/Python.aspx
# Modified by Ian Webster 4/2/11
##

import urllib
import re


class CASClient:
    
    def __init__(self, cas_url, service_url):
        self.cas_url = cas_url
        self.service_url = service_url


    def Authenticate(self, ticket=None):
        # If the request contains a login ticket, try to validate it
        if ticket:
            id = self.Validate(ticket)
            if id:
                return id

        # No valid ticket; redirect the browser to the login page to get one
        login_url = self.cas_url + 'login' \
            + '?service=' + urllib.quote(self.service_url)
        print 'Location: ' + login_url
        print 'Status-line: HTTP/1.1 307 Temporary Redirect'
        print ""


    def Validate(self, ticket):
        # TODO handle downloaderror
        val_url = self.cas_url + "validate" + \
            '?service=' + urllib.quote(self.service_url) + \
            '&ticket=' + urllib.quote(ticket)
        r = urllib.urlopen(val_url).readlines()    # returns 2 lines
        if len(r) == 2 and re.match("yes", r[0]) != None:
            return r[1].strip()
        return None
