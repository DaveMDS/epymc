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

from __future__ import absolute_import, print_function

import sys
import os
import shelve
import glob

try:
   import queue as Queue
except:
   import Queue

from efl import ecore

from epymc import utils
from epymc.gui import EmcDialog


def DBG(msg):
   # print('SDB: %s' % msg)
   pass

_queue = None
_queue_timer = None
_instances = []

class EmcDatabase(object):
   """ TODO doc this """

   def __init__(self, name, version = None):
      self._name = name
      self._vers = version
      self._vkey = '__database__version__'
      self._outstanding_writes = False

      # build the db name (different db for py2 and py3)
      dbname = os.path.join(utils.user_conf_dir,
                          'db_py%d_%s' %(sys.version_info[0], name))
      DBG('Open db: ' + name + ' from file: ' + dbname)

      # check if the db exist (or is the first time we use it)
      first_run = False if glob.glob(dbname + '*') else True

      # open the shelve
      #self._sh = shelve.open(dbname)
      self._sh = EpyMCShelf(dbname)

      if (not first_run) and (version is not None) and (self.get_version() != version):
         # the db is outdated
         text = _('<b>The database %s is outdated!</b><br><br>The old file has been renamed with a .backup extension and a new (empty) one has been created.<br><br>Sorry for the incovenience.')  % (name)
         EmcDialog(style = 'warning', title = _('EpyMC Database'), text = text)

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

      self._sync_timer = ecore.Timer(10.0, self._sync_timer_cb)
      _instances.append(self)

   def _close(self):
      DBG('Closing database %s' % self._name)
      self._sync_timer.delete()
      self._sh.close()

   def __len__(self):
      return len(self._sh)

   def get_data(self, key):
      DBG('Get Data for db: %s, key: %s' % (self._name, key))
      return self._sh[key]

   def set_data(self, key, data, thread_safe=False):
      DBG('Set data for db: %s, id: %s' % (self._name, key))
      if thread_safe:
         # just put in the queue
         _queue.put((self, key, data))
      else:
         # update the db now
         self._sh[key] = data
         self._sync_timer.reset()
         self._outstanding_writes = True

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

   def _sync_timer_cb(self):
      if self._outstanding_writes:
         DBG("Syncing database %s" % self._name)
         self._sh.sync()
         self._outstanding_writes = False

      return True

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

   for db in _instances:
      db._close()

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
      db._sync_timer.reset()
      db._outstanding_writes = True
      #db._sh.sync() # TODO really sync at every write ??

   return True


class EpyMCShelf(shelve.Shelf):
    def __init__(self, filename, flag='c', protocol=None, writeback=False):
        import dbm.gnu
        shelve.Shelf.__init__(self, dbm.gnu.open(filename, 'cf'), protocol, writeback)
