#!/usr/bin/env python

"""
Standard input events:

UP
DOWN
LEFT
RIGHT
OK
BACK

"""

EVENT_CONTINUE = True
EVENT_BLOCK = False

_listeners = []

def listener_add(name, event_cb, cb_data = None):
    global _listeners

    _listeners.append((name, event_cb, cb_data))
    
    print 'ADD LISTENER: ' + name
    for lis in _listeners:
        (name, cb, data) = lis
        print "  * " + name

def listener_del(name):
    global _listeners

    for lis in _listeners:
        (n, cb, data) = lis
        if n == name:
            _listeners.remove(lis)
            return

def event_emit(event):
    global _listeners

    #~ print "Emit Event: " + event + "  listeners: " + str(len(_listeners))

    for lis in _listeners:
        (name, cb, data) = lis

        if data:
            res = cb(event, data)
        else:
            res = cb(event)

        #~ print "  ->  '%s' (%s)" %  (name, ('continue' if res else 'block'))
        
        if res == EVENT_BLOCK:
            return
