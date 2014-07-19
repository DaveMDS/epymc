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


from efl import ecore

from epymc.modules import EmcModule
import epymc.input_events as input_events
import epymc.gui as gui


def DBG(msg):
   # print('KEYB: ' + msg)
   pass


# map ecore keys to emc input events
_mapping = { 
   'Up': 'UP',
   'Down': 'DOWN',
   'Left': 'LEFT',
   'Right': 'RIGHT',
   'Return': 'OK',
   'KP_Enter': 'OK',
   'Escape': 'EXIT',
   'BackSpace': 'BACK',
   'space': 'TOGGLE_PAUSE',
   'Pause': 'TOGGLE_PAUSE',
   'XF86AudioPlay': 'TOGGLE_PAUSE',
   'plus': 'VOLUME_UP',
   'minus': 'VOLUME_DOWN',
   'KP_Add': 'VOLUME_UP',
   'KP_Subtract': 'VOLUME_DOWN',
   'm': 'VOLUME_MUTE',
   'p': 'TOGGLE_PAUSE',
   'f': 'TOGGLE_FULLSCREEN',
   'F1': 'VIEW_LIST',
   'F2': 'VIEW_GRID',
   'F5': 'SCALE_SMALLER',
   'F6': 'SCALE_BIGGER',
   'F7': 'SCALE_RESET',
   's': 'STOP',
   'z': 'FAST_BACKWARD',
   'x': 'BACKWARD',
   'c': 'FORWARD',
   'v': 'FAST_FORWARD',
}

class KeyboardModule(EmcModule):
   name = 'input_keyb'
   label = _('Input - Keyboard')
   icon = 'icon/keyboard'
   info = _("""Long info for the <b>Keyboard</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>""")


   def __init__(self):
      DBG('Init module')
      gui.win.on_key_down_add(self._cb_key_down)

   def __shutdown__(self):
      DBG('Shutdown module')
      gui.win.on_key_down_del(self._cb_key_down)

   def _cb_key_down(self, win, event):
      DBG('Key: ' + event.key)
      if event.key in _mapping:
         input_events.event_emit(_mapping[event.key])
      else:
         print('Unhandled key: ' + event.key)

      return True
