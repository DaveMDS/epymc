#!/usr/bin/env python

# Inspired from the work on:
# http://www.jezra.net/blog/Python_Joystick_Class_using_Gobject

import struct

import ecore

from epymc.modules import EmcModule
import epymc.input as input
import epymc.ini as ini
import epymc.config_gui as config_gui


def DBG(msg):
   print('JOY: ' + msg)
   pass


class JoystickModule(EmcModule):
   name = 'input_joy'
   label = 'Joytick Input'
   icon = 'icon/joystick'
   info = """Long info for the <b>Joystick</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>"""

   EVENT_BUTTON = 0x01 # button pressed/released 
   EVENT_AXIS = 0x02   # axis moved  
   EVENT_INIT = 0x80   # button/axis initialized  
   EVENT_FORMAT = "IhBB" 
   EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

   dev = None
   fdh = None

   def __init__(self):
      DBG('Init module')

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
         print ("Error: Joystick configuration value missed")
         # TODO spawn the configurator
         return

      # add an entry in the config gui
      config_gui.root_item_add("joystick", 50, "Joystick", icon = None,
                               callback = self.start_configurator)

      # open the joystick device
      try:
         self.dev = open(self.device)
         self.fdh = ecore.FdHandler(self.dev, ecore.ECORE_FD_READ,
                                    self.joy_event_cb)
      except:
         print ('Error: can not open joystick device: ' + self.device)

   def __shutdown__(self):
      DBG('Shutdown module: Joystick')
      config_gui.root_item_del("joystick")
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
        
      # axis event
      if event == self.EVENT_AXIS and not init: 
         if number == self.axis_h:
            if value > 0:
               signal = 'DOWN' if self.invert_v else 'UP'
            if value < 0:
               signal = 'UP' if self.invert_v else 'DOWN'
         elif number == self.axis_v:
            if value > 0:
               signal = 'LEFT' if self.invert_h else 'RIGHT'
            elif value < 0:
               signal = 'RIGHT' if self.invert_h else 'LEFT'
         else:
            print 'Unknow Joystick Axis: %s  Value: %s' % (number, value)

      # buttons event
      elif event == self.EVENT_BUTTON and not init and value > 0:
         if number == self.button_ok:
            signal = 'OK'
         elif number == self.button_back:
            signal = 'BACK'
         else:
            print 'Unknow Joystick Button: %s  Value: %s' % (number, value)

      # init event
      elif init:
         #~ print 'INIT %s %s %s' % (number,value,init)
         pass

      # emit the emc input event  
      if signal: input.event_emit(signal)
      
      return True # keep tha handler alive

   def start_configurator(self):
      print self.dev
