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

"""
Standard input events:

UP
DOWN
LEFT
RIGHT
OK
BACK
EXIT

VOLUME_UP
VOLUME_DOWN
VOLUME_MUTE

TOGGLE_PAUSE
TOGGLE_FULLSCREEN

VIEW_LIST
VIEW_GRID

"""

import gui

def DBG(msg):
   # print('INPUT_EVENTS: ' + msg)
   pass


EVENT_CONTINUE = True
EVENT_BLOCK = False

_listeners = []

def listener_add(name, event_cb, cb_data = None):
   global _listeners

   _listeners.append((name, event_cb, cb_data))

   DBG('Add Listener: ' + name)
   for lis in _listeners:
      (name, cb, data) = lis
      DBG('  * ' + name)

def listener_del(name):
   global _listeners

   DBG('Listener Del: ' + name)
   for lis in _listeners:
      (n, cb, data) = lis
      if n == name:
         _listeners.remove(lis)
         return

def event_emit(event):
   global _listeners

   DBG("Emit Event: " + event + "  listeners: " + str(len(_listeners)))

   gui.mouse_hide()

   for lis in reversed(_listeners):
      (name, cb, data) = lis

      if data:
         res = cb(event, data)
      else:
         res = cb(event)

      #~ print "  ->  '%s' (%s)" %  (name, ('continue' if res else 'block'))

      if res == EVENT_BLOCK:
         return
