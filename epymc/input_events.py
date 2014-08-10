#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2014 Davide Andreoli <dave@gurumeditation.it>
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


from epymc import events

def DBG(msg):
   # print('INPUT_EVENTS: ' + msg)
   pass

STANDARD_EVENTS = """
UP DOWN LEFT RIGHT OK BACK EXIT
PLAY STOP PAUSE TOGGLE_PAUSE
FORWARD BACKWARD FAST_FORWARD FAST_BACKWARD PLAYLIST_NEXT PLAYLIST_PREV
VOLUME_UP VOLUME_DOWN VOLUME_MUTE
SUBS_DELAY_MORE SUBS_DELAY_LESS SUBS_DELAY_ZERO
TOGGLE_FULLSCREEN
VIEW_LIST VIEW_GRID
BIGGER SMALLER
"""

EVENT_CONTINUE = True
EVENT_BLOCK = False

_listeners = []

def listener_add(name, event_cb, cb_data = None):
   global _listeners

   _listeners.append((name, event_cb, cb_data))

   DBG('Listener Add: ' + name)
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

def listener_promote(name):
   global _listeners

   DBG('Listener Promote: ' + name)
   for lis in _listeners:
      (n, cb, data) = lis
      if n == name:
         _listeners.remove(lis)
         _listeners.append(lis)
         return

def event_emit(event):
   DBG('Emit Event: ' + event + '  listeners: ' + str(len(_listeners)))

   events.event_emit('KEEP_ALIVE')

   for lis in reversed(_listeners):
      (name, cb, data) = lis

      if data:
         res = cb(event, data)
      else:
         res = cb(event)

      # print("  ->  '%s' (%s)" %  (name, ('continue' if res else 'block')))

      if res == EVENT_BLOCK:
         return
