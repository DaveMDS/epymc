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

from __future__ import absolute_import, print_function

import os

from efl.elementary.image import Image

from epymc.modules import EmcModule
from epymc.gui import EXPAND_BOTH, EXPAND_HORIZ, FILL_BOTH, FILL_HORIZ
import epymc.config_gui as config_gui
import epymc.input_events as input_events
import epymc.gui as gui



sheets = [
'97VkS.png',
'EBU_3325_1080_7_video.png',
'Overscan-2.jpg',
'AVStest-black.png',
'AVStest-black_white.png',
'greyscale-ramp.png',
'bars601.jpg',
'Slide01.jpg',
'6291.png',
]
# http://gonedigital.net/2010/04/19/

class CalibratorModule(EmcModule):
   name = 'calibrator'
   label = _('Screen calibrator')
   icon = 'icon/calib'
   info = _('Use this module to calibrate your screen parameters.')
   path = os.path.dirname(__file__)

   def __init__(self):
      config_gui.root_item_add('calibrator', 100, _('Screen calibrator'),
                               icon='icon/calib', callback=self.startup)

   def __shutdown__(self):
      config_gui.root_item_del('calibrator')

   def startup(self):
      self.i = Image(gui.win, aspect_fixed=False,
                     size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
      gui.win.resize_object_add(self.i)
      self.i.show()

      input_events.listener_add(self.name, self.input_event_cb)

      self.current = -1
      self.next_sheet()

   def next_sheet(self):
      self.current = self.current + 1 if self.current < len(sheets) - 1 else 0
      self.i.file = os.path.join(self.path, sheets[self.current])
      print('Loaded: ' + sheets[self.current])

   def prev_sheet(self):
      self.current = self.current - 1 if self.current > 0 else len(sheets) - 1
      self.i.file = os.path.join(self.path, sheets[self.current])

   def close(self):
      self.i.delete()
      input_events.listener_del(self.name)

   def input_event_cb(self, event):
      if event in ('RIGHT', 'DOWN', 'OK'):
         self.next_sheet()
         return input_events.EVENT_BLOCK

      elif event in ('LEFT', 'UP'):
         self.prev_sheet()
         return input_events.EVENT_BLOCK

      elif event in ('BACK', 'EXIT'):
         self.close()
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE
