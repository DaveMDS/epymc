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

"""
Standard events:

PLAYBACK_STARTED
PLAYBACK_FINISHED
PLAYBACK_PAUSED ??
PLAYBACK_UNPAUSED ??

VOLUME_CHANGED

BROWSER_PAGE_CHANGED ??
BROWSER_VIEW_CHANGED ??
MAINMENU_SHOWED ??
MAINMENU_HIDDEN ??

"""


def DBG(msg):
   # print('EVENTS: ' + msg)
   pass


_listeners = []


def listener_add(name, func, *a, **ka):
   """ Add a new listener to the events chain """
   _listeners.append((name, func, a, ka))

   DBG('Listener Add: ' + name)
   for (name, cb, a, ka) in _listeners:
      DBG('  * ' + name)

def listener_del(name):
   """ Remove a listener by name """

   DBG('Listener Del: ' + name)

   for lis in _listeners:
      (n, cb, a, ka) = lis
      if n == name:
         _listeners.remove(lis)
         return

def event_emit(event):
   """ Emit the given event to all listeners, event is just a string """

   DBG('Emit Event: ' + event + '  listeners: ' + str(len(_listeners)))

   for lis in _listeners:
      (name, cb, a, ka) = lis
      cb(event, *a, **ka)

