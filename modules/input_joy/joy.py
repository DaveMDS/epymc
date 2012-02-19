#!/usr/bin/env python
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

# Inspired from the work on:
# http://www.jezra.net/blog/Python_Joystick_Class_using_Gobject

import struct

import ecore

from epymc.modules import EmcModule
from epymc.gui import EmcDialog
from epymc.gui import EmcVKeyboard
import epymc.input_events as input_events
import epymc.ini as ini
import epymc.config_gui as config_gui


def DBG(msg):
   #~ print('JOY: ' + msg)
   pass


class JoystickModule(EmcModule):
   name = 'input_joy'
   label = 'Input - Joytick'
   icon = 'icon/joystick'
   info = """Long info for the <b>Joystick</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>"""

   EVENT_BUTTON = 0x01 # button pressed/released 
   EVENT_AXIS = 0x02   # axis moved  
   EVENT_INIT = 0x80   # button/axis initialized  
   EVENT_FORMAT = 'IhBB'
   EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

   def __init__(self):
      DBG('Init module')

      self.grab_key_func = None

      # get joystick device from config
      ini.add_section('joystick')
      if not ini.has_option('joystick', 'device'):
         # TODO inspect for joystick devices
         ini.set('joystick', 'device', '/dev/input/js0')
      self.device = ini.get('joystick', 'device')

      # get joystick mapping from config
      try:
         self.axis_h = ini.get_int('joystick', 'axis_h');
         self.axis_v = ini.get_int('joystick', 'axis_v');
         self.button_ok = ini.get_int('joystick', 'button_ok');
         self.button_back = ini.get_int('joystick', 'button_back');
         self.invert_h = ini.get_bool('joystick', 'invert_h');
         self.invert_v = ini.get_bool('joystick', 'invert_v');
      except:
         print ('Error: Joystick configuration value missed')
         # TODO spawn the configurator

      # add an entry in the config gui
      config_gui.root_item_add('joystick', 50, 'Joystick', icon = None,
                               callback = self.config_panel_cb)

      # open the joystick device
      try:
         self.dev = open(self.device)
         self.fdh = ecore.FdHandler(self.dev, ecore.ECORE_FD_READ,
                                    self.joy_event_cb)
      except:
         self.dev = None
         self.fdh = None
         print ('Error: can not open joystick device: ' + self.device)

   def __shutdown__(self):
      DBG('Shutdown module: Joystick')
      config_gui.root_item_del('joystick')
      if self.fdh: self.fdh.delete()
      if self.dev: self.dev.close()

   def restart(self):
      self.__shutdown__()
      self.__init__()

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

      # if grabbed request call the grab function and return
      if self.grab_key_func and callable(self.grab_key_func):
         if not init and value != 0:
            self.grab_key_func(number, value)
            return True # keep tha handler alive
      
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
         DBG('INIT %s %s %s' % (number,value,init))
         pass

      # emit the emc input event
      if signal:
         input_events.event_emit(signal)
      
      return True # keep tha handler alive

### config panel stuff
   def config_panel_cb(self):
      bro = config_gui.browser_get()
      bro.page_add('config://joystick/', 'Joystick',
                   item_selected_cb = self.config_selected_cb)
      bro.item_add('config://joystick/device', 'Device (%s)' % (self.device))
      bro.item_add('config://joystick/configurator', 'Configure buttons')
      
   def config_selected_cb(self, page, item):
      if item.endswith('/device'):
         EmcVKeyboard(accept_cb = self.device_changed_cb,
                      title = 'Insert joystick device', text = self.device)
      elif item.endswith('/configurator'):
         self.start_configurator()

   def device_changed_cb(self, vkbd, new_device):
      ini.set('joystick', 'device', new_device)
      self.restart()

   def start_configurator(self):
      # recheck device
      self.restart()
      if not self.dev or not self.fdh:
         EmcDialog(title = 'No joystick found', style = 'error',
                   text = 'Try to adjust your joystick device')
         return

      # wait for the first key
      self.grab_key_func = self.grabbed_key_func
      self.dia_state = 'vert'
      self.dia = EmcDialog(title = 'Configure joystick', style = 'cancel',
                      text = 'Press UP', done_cb = self.end_configurator)

   def grabbed_key_func(self, number, value):
      # grab vertical axes
      if self.dia_state == 'vert':
         self.axis_v = number
         self.invert_v = value < 0
         self.dia.text_set('Press RIGHT')
         self.dia_state = 'horiz'
      # grab horizontal axes
      elif self.dia_state == 'horiz':
         self.axis_h = number
         self.invert_h = value < 0
         self.dia.text_set('Press OK')
         self.dia_state = 'ok'
      # grab button used as OK
      elif self.dia_state == 'ok':
         self.button_ok = number
         self.dia.text_set('Press BACK')
         self.dia_state = 'back'
      # grab button used as BACK
      elif self.dia_state == 'back':
         self.button_back = number
         self.dia.text_set('Config done.')
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
