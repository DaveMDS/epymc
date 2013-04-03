#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2012 Davide Andreoli <dave@gurumeditation.it>
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

import os
import shelve

try:
   from efl import ecore
except:
   import ecore

try:
   import queue as Queue
except:
   import Queue

from . import utils

def DBG(msg):
   # print('SDB: ' + msg)
   pass

_queue = None
_queue_timer = None

class EmcDatabase(object):
   """ TODO doc this """

   def __init__(self, name):
      file = os.path.join(utils.config_dir_get(), 'db_' + name)
      DBG('Open db: ' + name + ' from file: ' + file)
      self._sh = shelve.open(file)
      self._name = name

   def __del__(self):
      self._sh.close()

   def __len__(self):
      return len(self._sh)

   def get_data(self, key):
      DBG('Get Data on db ' + self._name + ', key: ' + key)
      return self._sh[key]

   def set_data(self, key, data, thread_safe=False):
      DBG('Set data for db ' + self._name + ', id: ' + key)
      if thread_safe:
         # just put in the queue
         _queue.put((self, key, data))
      else:
         # update the db now
         self._sh[key] = data
         self._sh.sync() # TODO really sync at every vrite ??

   def del_data(self, key):
      if self._sh.has_key(key):
         del self._sh[key]

   def id_exists(self, key):
      return self._sh.has_key(key)

   def keys(self):
      return self._sh.keys()

##################


def init():
   global _queue
   global _queue_timer

   _queue = Queue.Queue()
   _queue_timer = ecore.Timer(0.2, _process_queue)

def shutdown():
   global _queue
   global _queue_timer

   _queue_timer.delete()
   del _queue

def _process_queue():
   global _queue

   if _queue.empty():
      return True

   count = 10
   # DBG("Queue size: " + str(_queue.qsize()))
   while not _queue.empty() and count > 0:
      # DBG('Queue processing...count:%d  len:%d' % (count, _queue.qsize()))
      count -= 1
      (db, key, data) = _queue.get_nowait()
      db._sh[key] = data
      self._sh.sync() # TODO really sync at every vrite ??

   return True
