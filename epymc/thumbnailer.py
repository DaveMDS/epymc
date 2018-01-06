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
   pass

def ERR(*args):
   print('THUMBNAILER ERROR:', *args)


class EmcThumbItem(object):
   id_counter = 1

   def __init__(self, url, dst, frame, func, **kargs):
      self.url = url
      self.dst = dst
      self.frame = frame
      self.func = func
      self.kargs = kargs
      self.req_id = EmcThumbItem.id_counter
      EmcThumbItem.id_counter += 1

   def __repr__(self):
      return "<ThumbItem req_id={0.req_id}, url='{0.url}'>".format(self)

   def __eq__(self, other):
      if isinstance(other, EmcThumbItem):
         return self.req_id == other.req_id
      elif isinstance(other, int):
         return self.req_id == other
      return False

   def __hash__(self):
      return self.req_id


class EmcThumbWorker_Base(object):
   """ Thumbnail Worker base class, all workers must be based on this class """
   can_do_image = False
   can_do_video = False
   response_timeout = 15  # TODO make this configurable
   _id_counter = 1

   def __init__(self, done_cb=None):
      self._done_cb = done_cb
      self._item = None
      self._response_timer = None
      self._id = EmcThumbWorker_Base._id_counter
      EmcThumbWorker_Base._id_counter += 1

   @property
   def id(self):
      """ only used for debug """
      return self._id

   @property
   def is_idle(self):
      """ True if the worker is not busy and can accept a new request """
      return self._item is None

   @property
   def item_in_process(self):
      """ the item currently being processed, or None if idle """
      return self._item

   def generate_item(self, item):
      """ called by the manager to request a new thumb """
      if self.is_idle:
         self._item = item
         if self._response_timer is not None:
            self._response_timer.reset()
         else:
            self._response_timer = ecore.Timer(self.response_timeout,
                                               self._timeout_cb)
         return True
      else:
         DBG('ERROR, another request already in progress')
         return False

   def item_completed(self, success):
      """ called by the workers to notify the manager """
      if self._response_timer is not None:
         self._response_timer.delete()
         self._response_timer = None

      item = self._item
      self._item = None
      if callable(self._done_cb):
         self._done_cb(self, item, success)

   def kill(self):
      """ called in sub-classes after the timeout occur """
      raise NotImplementedError("kill() must be implemented in sub-classes")

   def _timeout_cb(self):
      DBG("RESPONSE TIMEOUT EXPIRED !!!")
      self.kill()
      self.item_completed(False)
      return ecore.ECORE_CALLBACK_CANCEL


class EmcThumbWorker_EThumbInASubrocess(EmcThumbWorker_Base):
   """ EThumb Worker in a slave process (bin/epymc_thumbnailer)  """
   can_do_image = True
   can_do_video = True

   def __init__(self, *args):
      super().__init__(*args)
      self._exe = None
      self._starting = False

   def generate_item(self, item):
      if super().generate_item(item) is False:
         return False

      if not self._exe:
         self._slave_process_start()
         return True

      if not self._starting:
         self._send_request()

      return True

   def kill(self):
      if self._exe:
         self._exe.on_del_event_del(self._slave_died_cb)
         self._exe.kill()
         self._exe.delete()
         self._exe = None
         self._starting = False

   def _slave_process_start(self):
      DBG('starting slave')
      self._starting = True
      self._exe = ecore.Exe('epymc_thumbnailer "%s"' % utils.in_use_theme_file,
                            ecore.ECORE_EXE_PIPE_READ |
                            ecore.ECORE_EXE_PIPE_WRITE |
                            ecore.ECORE_EXE_PIPE_READ_LINE_BUFFERED |
                            ecore.ECORE_EXE_TERM_WITH_PARENT |
                            ecore.ECORE_EXE_USE_SH)
      self._exe.on_add_event_add(self._slave_started_cb)
      self._exe.on_del_event_add(self._slave_died_cb)
      self._exe.on_data_event_add(self._slave_stdout_cb)

   def _slave_started_cb(self, exe, event):
      DBG('slave started succesfully')
      self._starting = False
      if self._item is not None:
         self._send_request()

   def _slave_died_cb(self, exe, event):
      DBG('slave exited')
      self._exe = None
      self._starting = False

   def _slave_stdout_cb(self, exe, event):
      for line in event.lines:
         self._parse_response(line)

   def _send_request(self):
      item = self._item
      DBG('send request', item.req_id, item.url, item.dst)
      self._exe.send('GEN|{0.url}|{0.dst}|{0.frame}\n'.format(item))

   def _parse_response(self, msg):
      if msg == 'OK':
         success = True
      else:
         success = False
         ERR('error or unknown msg from slave "%s"' % msg)

      self.item_completed(success)


class EmcThumbnailer(utils.Singleton):
   """ Thumbnailer Workers Manager

   Never instantiate this class directly !!

   Instead use the module level emc_thumbnailer instance.

   """

   known_workers = [EmcThumbWorker_EThumbInASubrocess, ]
   NUM_WORKERS = 3  # TODO make this configurable

   def __init__(self):
      DBG('manager init')
      self._workers_pool = []
      self._queue = OrderedDict() # key: req_id  val: ThumbItem instance

      for w in self.known_workers * self.NUM_WORKERS:
         self._workers_pool.append(w(self._worker_done_cb))

      print("POOL", self._workers_pool)

   ### public api
   def thumb_path_get(self, url):
      """ Generate and return the thumbnail path for the given uri """
      fname = utils.md5(url) + '.jpg'
      return os.path.join(utils.user_cache_dir, 'thumbs', fname[:2], fname)

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

      # thumb already exists? (and is updated)
      thumb = self.thumb_path_get(url)
      if os.path.exists(thumb) and os.path.getmtime(thumb) > os.path.getmtime(url):
         return thumb

      # url is already in queue ?   TODO optimize ? NEED TO CALL 2 DONE CB ?
      for item in self._queue.values():
         if item.url == url:
            return item.req_id

      # url is already in process ?   TODO optimize ? NEED TO CALL 2 DONE CB ?
      for worker in self._workers_pool:
         item = worker.item_in_process
         if item and item.url == url:
            return item.req_id

      # generate a new item, put it on queue and process the queue
      item = EmcThumbItem(url, thumb, frame, func, **kargs)
      self._queue[item.req_id] = item
      self._process_queue()

      return item.req_id

   def cancel_request(self, req_id):
      """ Cancel a previous request.

      Params:
         req_id (int): the id as returned by generate()

      """
      try:
         # remove from the waiting queue
         self._queue.pop(req_id)
         DBG('cancelled request', req_id)
      except KeyError: # not in queue, currently generating ?
         for w in self._workers_pool:
            if w.item_in_process == req_id:
               # in progress, finish it but do not call the user func
               w.item_in_process.func = None
               w.item_in_process.kargs = None

   def _process_queue(self):
      for worker in self._workers_pool:
         if worker.is_idle:
            # do we have an item in the queue to process ?
            try:
               item = next(iter(self._queue.values()))  # take the first item
            except StopIteration:  # no items in queue
               return

            if worker.generate_item(item):
               # ok, successfully started, remove item from the waiting queue
               DBG('sent request (to worker {}) {}'.format(worker.id, item))
               self._queue.pop(item)

   def _worker_done_cb(self, worker, item, success):
      DBG('WORKER {} DONE {} {}'.format(worker.id, success, item))
      # call user callback
      if item and callable(item.func):
         item.func(success, item.url, item.dst, **item.kargs)

      # this should never happend
      if item.req_id in self._queue:
         ERR('Completed item still in queue!!')
         del self._queue[item.req_id]

      # process another item (if available)
      self._process_queue()


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
