#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2013 Davide Andreoli <dave@gurumeditation.it>
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


import os, threading

try:
   import queue as Queue
except:
   import Queue

try:
   from efl import ecore
except:
   import ecore

from epymc.modules import EmcModule
import epymc.input_events as input_events
import epymc.utils as utils
import epymc.ini as ini

try:
   from http.server import BaseHTTPRequestHandler, HTTPServer
except:
   from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

def DBG(msg):
   # print('WEBSERVER: ' + msg)
   pass


# msgs from thread to core, items are the input_event (ex. 'UP')
input_queue = Queue.Queue()


class WebserverModule(EmcModule):
   name = 'input_webserver'
   label = 'Input - Webserver'
   icon = 'icon/keyboard'
   info = 'This module provide a way to control the application from ' \
   'your web browser.<br>' \
   'The server (by default) listen on port 8080, to connect just point ' \
   'to: <br>http://your_ip:8080<br>' \
   'You can change listening port and the theme from the configurtion file.'


   def __init__(self):
      DBG('Init module')

      # default config values
      ini.add_section('webserver')
      if not ini.has_option('webserver', 'listening_port'):
         ini.set('webserver', 'listening_port', '8080')
      if not ini.has_option('webserver', 'skin'):
         ini.set('webserver', 'skin', 'mobile')

      # run an http server in a separate thread
      port = ini.get('webserver', 'listening_port')
      self._thread = threading.Thread(target=self.http_server_in_a_thread,
                                      args=(port,))
      self._thread.start()

      # listen messagges from the thread using a queue
      self._queue_timer = ecore.Timer(0.1, self.queue_timer)

   def http_server_in_a_thread(self, port):
      DBG('starting httpd on port ' + port)
      try:
         self._httpd = HTTPServer(('', int(port)), RequestHandler)
         self._httpd.serve_forever(poll_interval=0.3)
      except:
         DBG('Error starting server on port')
      else:
         DBG('httpd stopped')

   def __shutdown__(self):
      DBG('Shutdown module')
      self._httpd.shutdown() # is this thread-safe ??
      self._httpd.socket.close() # is this thread-safe ??

   def queue_timer(self):
      if not input_queue.empty():
         input_events.event_emit(input_queue.get())
      return True # renew


class RequestHandler(BaseHTTPRequestHandler):

   def log_message(self, format, *args):
      pass

   def do_GET(self):
      (host, port) = self.client_address
      DBG('GET from client: %s:%d [%s]' % (host, port, self.path))

      if self.path == '/':
         self.serve_file('main.html')
      elif self.path.startswith('/input/'):
         input_queue.put(self.path[7:])
         self.send_response(200) # HTTP status code: OK
      else:
         self.serve_file(self.path[1:])

   def serve_file(self, path):
      try:
         skin = ini.get('webserver', 'skin')
         fname = os.path.join(os.path.dirname(__file__), skin, path)
         f = open(fname)
      except:
         DBG('Cannot open file: ' + fname)
         self.send_response(404) # HTTP status code: Not Found
      else:
         self.send_response(200) # HTTP status code: OK
         if   path.endswith('.html'): cont_type = 'text/html'
         elif path.endswith('.css'):  cont_type = 'text/css'
         elif path.endswith('.png'):  cont_type = 'image/png'
         else: cont_type = 'text/plain'
         self.send_header('Content-type', cont_type)
         self.end_headers()
         self.wfile.write(f.read())
         f.close()
