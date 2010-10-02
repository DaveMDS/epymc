#!/usr/bin/env python

import ecore
import ecore.x

from modules import EmcModule
import input


def DBG(msg):
    #~ print('KEYB: ' + msg)
    pass


# map ecore keys to emc input events
_mapping = { 'Up': 'UP',
             'Down': 'DOWN',
             'Left': 'LEFT',
             'Right': 'RIGHT',
             'Return': 'OK',
             'KP_Enter': 'OK',
             'Escape': 'BACK',
             'BackSpace': 'BACK',
             'space': 'TOGGLE_PAUSE',
             'p': 'TOGGLE_PAUSE',
           }

class KeyboardModule(EmcModule):
    name = 'input_keyb'
    label = 'Keyboard Input'

    def __init__(self):
        DBG('Init module')
        ecore.x.on_key_down_add(self._cb_key_down)

    def __shutdown__(self):
        DBG('Shutdown module')
        # TODO How to detach the callback?

    def _cb_key_down(self, event):
        DBG('Key: ' + event.key)
        if _mapping.has_key(event.key):
            input.event_emit(_mapping[event.key])
        else:
            print "Unhandled key: " + event.key

        return True
