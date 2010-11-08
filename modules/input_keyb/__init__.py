#!/usr/bin/env python

import ecore
import ecore.x

from epymc.modules import EmcModule
import epymc.input as input


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
             'Escape': 'EXIT',
             'BackSpace': 'BACK',
             'space': 'TOGGLE_PAUSE',
             'p': 'TOGGLE_PAUSE',
             'f': 'TOGGLE_FULLSCREEN',
           }

class KeyboardModule(EmcModule):
   name = 'input_keyb'
   label = 'Keyboard Input'
   icon = 'icon/keyboard'
   info = """Long info for the <b>Keyboard</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>"""


   def __init__(self):
      DBG('Init module')
      self.handler = ecore.x.on_key_down_add(self._cb_key_down)

   def __shutdown__(self):
      DBG('Shutdown module')
      if self.handler: self.handler.delete()

   def _cb_key_down(self, event):
      DBG('Key: ' + event.key)
      if _mapping.has_key(event.key):
         input.event_emit(_mapping[event.key])
      else:
         print "Unhandled key: " + event.key

      return True
