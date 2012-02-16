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

from socket import *

import ecore

from epymc.modules import EmcModule
import epymc.input_events as input_events
import epymc.ini as ini


def DBG(msg):
   #~ print('LIRC: ' + msg)
   pass


class LircModule(EmcModule):
   name = 'input_lirc'
   label = 'Input - Remote Control'
   icon = 'icon/remote'
   info = """Long info for the <b>LIRC</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>"""


   DEFAULT_LIRC_SOCKET = '/dev/lircd'

   sok = None
   fdh = None

   def __init__(self):
      DBG('Init module')

      # get lirc device from config
      ini.add_section('lirc')
      if not ini.has_option('lirc', 'device'):
         ini.set('lirc', 'device', self.DEFAULT_LIRC_SOCKET)
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
