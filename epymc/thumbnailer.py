#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2016 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of EpyMC, an EFL based Media Center written in Python.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from collections import OrderedDict

from efl import ecore

import epymc.utils as utils


def DBG(*args):
   print('THUMBNAILER:', *args)

def ERR(*args):
   print('THUMBNAILER:', *args)


class ThumbItem(object):
   def __init__(self, req_id, url, dst, frame, func, **kargs):
      self.req_id = req_id
      self.url = url
      self.dst = dst
      self.frame = frame
      self.func = func
      self.kargs = kargs


class EmcThumbnailer(utils.Singleton):
   """ Thumbnailer that use epymc_thumbnailer bin in a separate process

   Do not instantiate this class directly,
   instead use the module level emc_thumbnailer instance.

   """

   def __init__(self):
      DBG('init')
      self._slave = None # EcoreExe instance
      self._slave_starting = False
      self._id = 0       # incremental requests ids
      self._item = None  # ThumbItem currently in process (None if slave is ready)
      self._requests = OrderedDict() # key: req_id  val: ThumbItem instance

   ### public api
   def generate(self, url, func, frame=None, **kargs):
      """ Ask the thumbnailer to generate a thumbnail

      Params:
         url: full path of the file to thumbnail
         func: function to call when the thumb is ready
         frame: style for an optional frame to draw around the thumb
                available styles: 'vthumb'
         kargs: any other keyword args will be passed back in func call

      Return:
         thumb path (str) if the thumb already exists
         request id (int) if the thumb has been queued

      """
      if url.startswith('file://'):
         url = url[7:]

      # thumb already exists?
      thumb = self.thumb_path_get(url)
      if os.path.exists(thumb):
         # TODO check file mod time ??
         return thumb

      # start the slave process if necessary
      if self._slave is None and not self._slave_starting:
         self._start_slave()

      # generate a new request id + item
      self._id += 1
      self._requests[self._id] = ThumbItem(self._id, url, thumb, frame, func, **kargs)

      # TODO url is already in queue ?

      # process next item in the queue (if not busy)
      if self._item is None:
         self._send_next_request()

      return self._id

   def cancel_request(self, req_id):
      """ Cancel a previous request.

      Params:
         req_id (int): the id as returned by generate()

      """
      if self._item is not None and self._item.req_id == req_id:
         # currently in progress, finish it but do not call the user func
         self._item.func = None
         self._item.kargs = None
         DBG('cancelled request', req_id)
      else:
         # or just remove from the queue (if there)
         try:
            self._requests.pop(req_id)
            DBG('cancelled request', req_id)
         except KeyError:
            pass

   def thumb_path_get(self, url):
      """ Generate the path thumb for the give url (internally used) """
      fname = utils.md5(url) + '.jpg'
      return os.path.join(utils.user_cache_dir, 'thumbs', fname[:2], fname)

   ### slave communication management
   def _send_next_request(self):
      if not self._slave or self._slave_starting:
         return

      try:
         req_id, item = self._requests.popitem(last=False)
      except KeyError:
         return

      DBG('send request', item.req_id, item.url, item.dst)
      self._slave.send('GEN|%s|%s|%s\n' % (item.url, item.dst, item.frame))
      self._item = item

   def _process_slave_msg(self, msg):
      if msg == 'OK':
         success = True
      elif msg == 'ERR':
         success = False
      else:
         ERR('unknown msg from slave "%s"' % msg)
         return

      # call user callback
      item = self._item
      self._item = None
      if item and callable(item.func):
         item.func(success, item.url, item.dst, **item.kargs)

      # process next item (if available)
      self._send_next_request()

   ### slave process management
   def _start_slave(self):
      DBG('starting slave')
      self._slave_starting = True
      exe = ecore.Exe('epymc_thumbnailer "%s"' % utils.in_use_theme_file,
                      ecore.ECORE_EXE_PIPE_READ |
                      ecore.ECORE_EXE_PIPE_READ_LINE_BUFFERED |
                      ecore.ECORE_EXE_PIPE_WRITE |
                      ecore.ECORE_EXE_TERM_WITH_PARENT)
      exe.on_add_event_add(self._slave_started_cb)
      exe.on_del_event_add(self._slave_died_cb)
      exe.on_data_event_add(self._slave_stdout_cb)

   def _slave_started_cb(self, exe, event):
      DBG('slave started succesfully')
      self._slave = exe
      self._slave_starting = False
      self._send_next_request()

   def _slave_died_cb(self, exe, event):
      ERR('slave exited')
      self._slave = None
      self._slave_starting = False

   def _slave_stdout_cb(self, exe, event):
      for line in event.lines:
         self._process_slave_msg(line)


emc_thumbnailer = EmcThumbnailer()


"""

Another EmcThumbnailer implementation use EthumbClient instead of the
custom epymc_thumbnailer, is A LOT simpler but EthumbClient is highly
unreliable atm :(

Maybe we can use this in a better future...


class EmcThumbnailer(object):
   def __init__(self):
      self._connected = False
      self._connecting = False
      self._client = None
      self._queue = []
      self._timer = ecore.Timer(1.0, self._queue_eval)

   def generate(self, src, dst, cb):
      if self._connected:
         DBG("Request Thumb 1 (src='%s', dst='%s')" % (src, dst))
         self._client.file = src
         self._client.thumb_path = dst
         self._client.generate(self._generate_cb, cb)
      else:
         self._queue.append((src,dst, cb))
         self._connect()

   def _queue_eval(self):
      if len(self._queue) > 0:
         self._connect()
         while self._connected and len(self._queue) > 0:
            src, dst, cb = self._queue.pop(0)
            DBG("Request Thumb 1 (src='%s', dst='%s')" % (src, dst))
            self._client.file = src
            self._client.thumb_path = dst
            self._client.generate(self._generate_cb, cb)
      return ecore.ECORE_CALLBACK_RENEW

   def _generate_cb(self, client, id, file, key, tfile, tkey, status, cb):
      if callable(cb):
         cb(status, file, tfile)

   def _connect(self):
      if not self._connected and not self._connecting:
         DBG("Connecting to Ethumb...")
         self._connecting = True
         self._client = EthumbClient(self._connection_done_cb)
         self._client.on_server_die_callback_set(self._connection_die_cb)

   def _connection_done_cb(self, client, status):
      self._connecting = False
      self._connected = status
      if status is True:
         DBG("Ethumb connection OK")
         self._client.format = ETHUMB_THUMB_JPEG
         self._client.quality = 90
         self._client.size = 384, 384
         self._queue_eval()
      else:
         DBG("Ethumb Connection FAIL !!!!!")
         self._client = None

   def _connection_die_cb(self, client):
      DBG("Ethumb server DIED !!!!!")
      self._connected = False
      self._connecting = False
      self._client = None

try: # EthumbClient only in recent python-efl
   from efl.ethumb_client import EthumbClient, ETHUMB_THUMB_JPEG
except:
   emc_thumbnailer = None
else:
   emc_thumbnailer = EmcThumbnailer()

"""
