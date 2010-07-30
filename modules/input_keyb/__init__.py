#!/usr/bin/env python

import evas
import ecore
import ecore.x

import gui
import input
from modules import EpymcModule

# map evas keys to emc input events
_mapping = { 'Up': 'up',
             'Down': 'down',
             'Left': 'left',
             'Right': 'right',
             'Return': 'ok',
             'KP_Enter': 'ok',
             'Escape': 'back',
           }

class KeyboardModule(EpymcModule):
    name = 'input_keyb'
    label = 'Keyboard Input'

    def __init__(self):
        print 'Init module: Keyboard'
        ecore.x.on_key_down_add(self._cb_key_down)

    def __del__(self):
        print "Shutdown module: Keyboard"
        # TODO How to detach the callback?

    def _cb_key_down(self, event):
        #~ print event
        if _mapping.has_key(event.key):
            input.event_emit(_mapping[event.key])
        else:
            print "Unhandled key: " + event.key

        return True
