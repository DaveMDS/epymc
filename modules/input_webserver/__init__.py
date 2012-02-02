#!/usr/bin/env python
#
# Copyright (C) 2010 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of EpyMC.
#
# EpyMC is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# EpyMC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with EpyMC. If not, see <http://www.gnu.org/licenses/>.


import os, Queue, threading, ecore

from epymc.modules import EmcModule
import epymc.input_events as input_events
import epymc.utils as utils

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

def DBG(msg):
   print('WEBSERVER: ' + msg)
   pass

# msgs from thread to core, item is the input_event (ex. 'UP')
input_queue = Queue.Queue()

class WebserverModule(EmcModule):
   name = 'input_webserver'
   label = 'Input - Webserver'
   icon = 'icon/keyboard'
   info = """Long info for the <b>Webserver</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>"""

   def __init__(self):
      DBG('Init module')
      port = 8080 # TODO make this configurable
      self._thread = threading.Thread(target=self.http_server_in_a_thread,
                                      args=(port,))
      self._thread.start()
      self._queue_timer = ecore.Timer(0.1, self.queue_timer)

   def http_server_in_a_thread(self, port):
      DBG("starting httpd on port " + str(port))
      try:
         self._httpd = HTTPServer(('', port), RequestHandler)
         self._httpd.serve_forever(poll_interval=0.3)
      except:
         DBG("Error starting server on port")
      finally:
         DBG("httpd stopped")

   def __shutdown__(self):
      DBG('Shutdown module')
      self._httpd.shutdown() # is this thread-safe ??
      self._httpd.socket.close() # is this thread-safe ??

   def queue_timer(self):
      if not input_queue.empty():
         input_events.event_emit(input_queue.get())
      return 1 # renew


class RequestHandler(BaseHTTPRequestHandler):

   def do_GET(self):
      (host, port) = self.client_address
      DBG("GET from client: %s:%d [%s]" % (host, port, self.path))

      if self.path == '/':
         self.serve_ui()
      elif self.path.startswith('/input/'):
         input_queue.put(self.path[7:])
         self.send_response(200)

   def serve_ui(self):
      fname = os.path.join(os.path.dirname(__file__),'skin.html')
      f = open(fname)
      self.send_response(200)
      self.send_header('Content-type', 'text/html')
      self.end_headers()
      self.wfile.write(f.read())
      f.close()
