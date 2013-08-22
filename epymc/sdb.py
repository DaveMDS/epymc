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

import sys
import os
import shelve
import glob

try:
   from efl import ecore
except:
   import ecore

try:
   import queue as Queue
except:
   import Queue

from . import utils
from .gui import EmcDialog


def DBG(msg):
   # print('SDB: ' + msg)
   pass

_queue = None
_queue_timer = None

class EmcDatabase(object):
   """ TODO doc this """

   def __init__(self, name, version = None):
      self._name = name
      self._vers = version
      self._vkey = '__database__version__'

      # build the db name (different db for py2 and py3)
      dbname = os.path.join(utils.config_dir_get(),
                          'db_py%d_%s' %(sys.version_info[0], name))
      DBG('Open db: ' + name + ' from file: ' + dbname)

      # check if the db exist (or is the first time we use it)
      first_run = False if glob.glob(dbname + '*') else True

      # open the shelve
      self._sh = shelve.open(dbname)

      if (not first_run) and (version is not None) and (self.get_version() != version):
         # the db is outdated
         text = '<b>The database "%s" is outdated!</b><br><br>The old file has been renamed with a .backup extension and a new (empty) one has been created.<br><br>Sorry for the incovenience.'  % (name)
         EmcDialog(style = 'warning', title = 'EpyMC Database', text = text)

         # close the shelve
         self._sh.close()

         # rename db files to .backup
         for fname in glob.glob(dbname + '*'):
            os.rename(fname, fname + '.backup')

         # reopen a new (empty) shelve
         self._sh = shelve.open(dbname)

      if version is not None:
         # store the version inside the db
         self._sh[self._vkey] = version

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
      if key in self._sh:
         del self._sh[key]

   def id_exists(self, key):
      return key in self._sh

   def keys(self):
      if self._vers:
         return [k for k in self._sh.keys() if k != self._vkey]
      else:
         return self._sh.keys()

   def get_version(self):
      if self._vkey in self._sh:
         return self._sh[self._vkey]

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
