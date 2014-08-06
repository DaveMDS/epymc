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

# Inspired from the work on:
# http://www.jezra.net/blog/Python_Joystick_Class_using_Gobject

import struct

from efl import ecore

from epymc.modules import EmcModule
from epymc.gui import EmcDialog, EmcVKeyboard
from epymc.browser import EmcItemClass
import epymc.input_events as input_events
import epymc.ini as ini
import epymc.config_gui as config_gui


def DBG(msg):
   print('JOY: ' + msg)
   pass


class JoystickModule(EmcModule):
   name = 'input_joy'
   label = _('Input - Joystick')
   icon = 'icon/joystick'
   info = _("""Long info for the <b>Joystick</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>""")

   EVENT_BUTTON = 0x01 # button pressed/released 
   EVENT_AXIS = 0x02   # axis moved  
   EVENT_INIT = 0x80   # button/axis initialized  
   EVENT_FORMAT = 'IhBB'
   EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

   def __init__(self):
      DBG('Init module')

      self.grab_key_func = None
      self.axis_h = self.axis_v = self.button_ok = self.button_back = None
      self.invert_h = self.invert_v = False

      # get joystick device from config
      ini.add_section('joystick')
      self.device = ini.get('joystick', 'device', '/dev/input/js0')

      # get joystick mapping from config
      try:
         self.axis_h = ini.get_int('joystick', 'axis_h');
         self.axis_v = ini.get_int('joystick', 'axis_v');
         self.button_ok = ini.get_int('joystick', 'button_ok');
         self.button_back = ini.get_int('joystick', 'button_back');
         self.invert_h = ini.get_bool('joystick', 'invert_h');
         self.invert_v = ini.get_bool('joystick', 'invert_v');
      except:
         print('Error: Joystick configuration value missed')
         # TODO spawn the configurator

      # add an entry in the config gui
      config_gui.root_item_add('joystick', 52, _('Joystick'),
                               icon='icon/joystick',
                               callback=self.config_panel_cb)

      # open the joystick device
      try:
         self.dev = open(self.device, 'rb')
         self.fdh = ecore.FdHandler(self.dev, ecore.ECORE_FD_READ,
                                    self.joy_event_cb)
      except:
         self.dev = None
         self.fdh = None
         print('Error: can not open joystick device: ' + self.device)

   def __shutdown__(self):
      DBG('Shutdown module: Joystick')
      config_gui.root_item_del('joystick')
      if self.fdh: self.fdh.delete()
      if self.dev: self.dev.close()

   def joy_event_cb(self, handler):
      # read self.EVENT_SIZE bytes from the joystick 
      read_event = self.dev.read(self.EVENT_SIZE)

      # get the event structure values from  the read event 
      time, value, type, number = struct.unpack(self.EVENT_FORMAT, read_event)
      # get just the button/axis press event from the event type
      event = type & ~self.EVENT_INIT
      # get just the INIT event from the event type 
      init = type & ~event
      signal = None
      DBG("EVENT RECEIVED: %s %s %s %s" % (time, value, type, number))

      # if grabbed request call the grab function and return
      if self.grab_key_func and callable(self.grab_key_func):
         if not init and value != 0:
            self.grab_key_func(number, value)
            return ecore.ECORE_CALLBACK_RENEW # keep tha handler alive
      
      # axis event
      if event == self.EVENT_AXIS and not init: 
         if number == self.axis_v:
            if value > 0:
               signal = 'DOWN' if self.invert_v else 'UP'
            if value < 0:
               signal = 'UP' if self.invert_v else 'DOWN'
         elif number == self.axis_h:
            if value > 0:
               signal = 'LEFT' if self.invert_h else 'RIGHT'
            elif value < 0:
               signal = 'RIGHT' if self.invert_h else 'LEFT'
         else:
            DBG('Unknow Joystick Axis: %s  Value: %s' % (number, value))

      # buttons event
      elif event == self.EVENT_BUTTON and not init and value > 0:
         if number == self.button_ok:
            signal = 'OK'
         elif number == self.button_back:
            signal = 'BACK'
         else:
            DBG('Unknow Joystick Button: %s  Value: %s' % (number, value))

      # init event
      elif init:
         DBG('EVENT IS INIT %s %s %s' % (number,value,init))

      # emit the emc input event
      if signal:
         input_events.event_emit(signal)
      
      return ecore.ECORE_CALLBACK_RENEW # keep tha handler alive

### config panel stuff
   def config_panel_cb(self):
      bro = config_gui.browser_get()
      bro.page_add('config://joystick/', _('Joystick'), None, self.populate_joy)

   def populate_joy(self, browser, url):
      config_gui.standard_item_string_add('joystick', 'device', _('Device'),
                                 'icon/joystick', cb=self.device_changed_cb)
      config_gui.standard_item_action_add(_('Configure buttons'), cb=self.start_configurator)

   def device_changed_cb(self):
      self.__restart__()
      self.check_device()

   def check_device(self):
      if not self.dev or not self.fdh:
         EmcDialog(title=_('No joystick found'), style='error',
                   text=_('Try to adjust your joystick device'))
         return False
      return True

   def start_configurator(self):
      # retry device
      self.__restart__()
      if not self.check_device():
         return

      # wait for the first key
      self.grab_key_func = self.grabbed_key_func
      self.dia_state = 'vert'
      self.dia = EmcDialog(title=_('Configure joystick'), style='cancel',
                      text=_('Move the stick Up'), done_cb=self.end_configurator)

   def grabbed_key_func(self, number, value):
      # grab vertical axes
      if self.dia_state == 'vert':
         self.axis_v = number
         self.invert_v = value < 0
         self.dia.text_set(_('Move the stick Right'))
         self.dia_state = 'horiz'
      # grab horizontal axes
      elif self.dia_state == 'horiz':
         self.axis_h = number
         self.invert_h = value < 0
         self.dia.text_set(_('Press OK'))
         self.dia_state = 'ok'
      # grab button used as OK
      elif self.dia_state == 'ok':
         self.button_ok = number
         self.dia.text_set(_('Press BACK'))
         self.dia_state = 'back'
      # grab button used as BACK
      elif self.dia_state == 'back':
         self.button_back = number
         self.dia.text_set(_('Config done.'))
         self.dia_state = 'done'
         # end & save
         self.end_configurator(None)

   def end_configurator(self, dialog):
      self.grab_key_func = None
      self.dia.delete()
      if not dialog: # save config if called by hand
         ini.set('joystick', 'axis_h', self.axis_h)
         ini.set('joystick', 'axis_v', self.axis_v)
         ini.set('joystick', 'invert_h', self.invert_h)
         ini.set('joystick', 'invert_v', self.invert_v)
         ini.set('joystick', 'button_ok', self.button_ok)
         ini.set('joystick', 'button_back', self.button_back)
