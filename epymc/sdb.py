#!/usr/bin/env python
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

import ecore
import Queue

import utils

def DBG(msg):
   #~ print('SDB: ' + msg)
   pass

class EmcDatabase(object):
   """ TODO doc this """

   def __init__(self, name):
      file = os.path.join(utils.config_dir_get(), 'db_' + name)
      DBG('Open db: ' + name + ' from file: ' + file)
      self.__sh = shelve.open(file)
      self.__name = name

   def __del__(self):
      self.__sh.close()

   def get_data(self, id):
      DBG('Get Data on db ' + self.__name + ', id: ' + id)
      return self.__sh[id]

   def set_data(self, id, data, thread_safe = False):
      DBG('Set data for db ' + self.__name + ', id: ' + id)
      if thread_safe:
         # just put in queue
         pass
      else:
         self.__sh[id] = data
         self.__sh.sync() # TODO really sync at every vrite ??

   def del_data(self, db, id):
      if self.__sh.has_key(id):
         del self.__sh[id]

   def id_exists(self, id):
      return self.__sh.has_key(id)

   def keys(self):
      return self.__sh.keys()

##################


def init():
   global __queue
   global __queue_timer

   __queue = Queue.Queue()
   __queue_timer = ecore.Timer(2.0, __process_queue)

def shutdown():
   global __queue
   global __queue_timer

   __queue_timer.delete()
   del __queue

def __process_queue():
   global __queue

   #~ print 'Queue processing...'
   return True
