"""
Copyright (C)  2009  twitter.com/rcb

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""
import random
from wsgiref.handlers import CGIHandler
from google.appengine.api.labs import taskqueue
from google.appengine.api import memcache
from google.appengine.api.capabilities import CapabilitySet
memcache_service = CapabilitySet('memcache', methods=['set','get'])
hot_handler_queue = taskqueue.Queue(name='hothandler')
HOT_HANDLER_PREFIX = '/_ah/queue/hothandler/'
def wsgi_app(env, res):
    """ visit '/_ah/queue/hothandler/start' as admin to start a task """
    token = env['PATH_INFO'].replace(HOT_HANDLER_PREFIX,'')
    cur_token = memcache.get(HOT_HANDLER_PREFIX)
    if cur_token is None:
        if not memcache_service.is_enabled():
            cur_token = token
    if token in [cur_token, 'start']:
        next_token = str(random.random())
        url = '%s%s'%(HOT_HANDLER_PREFIX, next_token)
        next_task = taskqueue.Task(countdown=10, url=url)
        hot_handler_queue.add(next_task)
        memcache.set(HOT_HANDLER_PREFIX, next_token)
    res('200 OK',[('Content-Type','text/plain')])
    return ['ok']
def main():
    CGIHandler().run(wsgi_app)
    
if __name__ == '__main__':
    main()
