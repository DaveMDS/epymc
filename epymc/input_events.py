#!/usr/bin/env python

"""
Standard input events:

UP
DOWN
LEFT
RIGHT
OK
BACK
EXIT

TOGGLE_PAUSE

TOGGLE_FULLSCREEN

VIEW_LIST
VIEW_GRID

"""

import gui

def DBG(msg):
   #~ print('INPUT_EVENTS: ' + msg)
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
