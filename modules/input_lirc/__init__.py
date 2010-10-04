#!/usr/bin/env python

from socket import *

import ecore

from modules import EmcModule
import input
import ini


def DBG(msg):
   #~ print('LIRC: ' + msg)
   pass


class LircModule(EmcModule):
   name = 'input_lirc'
   label = 'Remote Control Input'

   DEFAULT_LIRC_SOCKET = '/dev/lircd'

   sok = None
   fdh = None

   def __init__(self):
      DBG('Init module')

      # get lirc device from config
      ini.add_section('lirc')
      if not ini.has_option('lirc', 'device'):
         ini.set('lirc', 'device', DEFAULT_LIRC_SOCKET)
      self.device = ini.get('lirc', 'device')

      # get joystick mapping from config
      #~ try:
         #~ self.axis_h = ini.get_int('joystick', 'axis_h');
         #~ self.axis_v = ini.get_int('joystick', 'axis_v');
         #~ self.button_ok = ini.get_int('joystick', 'button_ok');
         #~ self.button_back = ini.get_int('joystick', 'button_back');
         #~ self.invert_h = ini.get_bool('joystick', 'invert_h');
         #~ self.invert_v = ini.get_bool('joystick', 'invert_v');
      #~ except:
         #~ print "Error: Joystick configuration value missed"
         # TODO spawn the configurator
         #~ return

      try:
         self.sok = socket(AF_UNIX, OCK_STREAM)
         self.sok.connect(self.device)
         self.fdh = ecore.FdHandler(self.sok.fileno(), ecore.ECORE_FD_READ,
                                    self.lirc_socket_cb)
      except:
         print 'Error: can not connect to lirc using socket: ' + self.device

   def __shutdown__(self):
      DBG('Shutdown module: Lirc')
      if self.fdh: self.fdh.delete()
      if self.sok: self.sok.close()

   def lirc_socket_cb(self, handler):
      data = self.sok.recv(128)
      print data

      return True
