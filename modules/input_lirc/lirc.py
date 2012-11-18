#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
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
from epymc.gui import EmcVKeyboard, EmcDialog
from epymc.browser import EmcItemClass
import epymc.ini as ini
import epymc.config_gui as config_gui


def DBG(msg):
   print('LIRC: ' + msg)
   pass


class LircModule(EmcModule):
   name = 'input_lirc'
   label = 'Input - Remote Control'
   icon = 'icon/remote'
   info = """Long info for the <b>LIRC</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>"""


   DEFAULT_LIRC_SOCKET = '/var/run/lirc/lircd'

   sok = None
   fdh = None
   
   key_up = None
   key_down = None
   key_left = None
   key_right = None
   key_ok = None
   key_back = None
   
   def __init__(self):
      DBG('Init module')

      self.grab_key_func = None
      
      # get lirc device from config
      ini.add_section('lirc')
      if not ini.has_option('lirc', 'device'):
         ini.set('lirc', 'device', self.DEFAULT_LIRC_SOCKET)
      self.device = ini.get('lirc', 'device')
      
      # add an entry in the config section
      config_gui.root_item_add('lirc', 51, 'Remote', icon = 'icon/remote',
                               callback = self.config_panel_cb)

      # get lirc mapping from config
      try:
         self.key_up = ini.get_string('lirc', 'key_up');
         self.key_down = ini.get_string('lirc', 'key_down');
         self.key_left = ini.get_string('lirc', 'key_left');
         self.key_right = ini.get_string('lirc', 'key_right');
         self.key_ok = ini.get_string('lirc', 'key_ok');
         self.key_back = ini.get_string('lirc', 'key_back');
      except:
         print 'Error: lirc configuration value missed'
         # TODO spawn the configurator

      try:
         # try to open the lircd socket
         self.sok = socket(AF_UNIX, SOCK_STREAM)
         self.sok.connect(self.device)
         self.fdh = ecore.FdHandler(self.sok.fileno(), ecore.ECORE_FD_READ,
                                    self.lirc_socket_cb) 
      except:
         self.sok = None
         self.fdh = None 
         print('Error: can not connect to lirc using socket: ' + self.device)

   def __shutdown__(self):
      DBG('Shutdown module: Lirc')
      config_gui.root_item_del('lirc')
      if self.fdh: self.fdh.delete()
      if self.sok: self.sok.close()

   def lirc_socket_cb(self, handler):
      signal = ''
      try:
         data = self.sok.recv(128)
         code, repeat, key, remote = data.strip().split()
         DBG('code:%s repeat:%s key:%s remote:%s' % (code, repeat, key, remote))

         # if grabbed request call the grab function and return
         if self.grab_key_func and callable(self.grab_key_func):
            if repeat == '00':
               self.grab_key_func(key)
         else:
            if   key == self.key_up:    signal = 'UP'
            elif key == self.key_down:  signal = 'DOWN'
            elif key == self.key_left:  signal = 'LEFT'
            elif key == self.key_right: signal = 'RIGHT'
            elif repeat == '00':
               if   key == self.key_ok   and repeat == '00':  signal = 'OK'
               elif key == self.key_back and repeat == '00':  signal = 'BACK'
            input_events.event_emit(signal)
      except:
         pass

      return True

   ### config panel stuff
   class DeviceItemClass(EmcItemClass):
      def label_get(self, url, mod):
         return 'Device (%s)' % (mod.device)

      def item_selected(self, url, mod):
         EmcVKeyboard(accept_cb = mod.device_changed_cb,
                      title = 'Insert lirc device', text = mod.device)

   class WizardItemClass(EmcItemClass):
      def label_get(self, url, mod):
         return 'Configure buttons'

      def item_selected(self, url, mod):
         mod.start_configurator()
   
   def config_panel_cb(self):
      bro = config_gui.browser_get()
      bro.page_add('config://lirc/', 'Remote', None, self.populate_lirc)

   def populate_lirc(self, browser, url):
      browser.item_add(self.DeviceItemClass(), 'config://lirc/device', self)
      browser.item_add(self.WizardItemClass(), 'config://lirc/configurator', self)

   def device_changed_cb(self, vkbd, new_device):
      ini.set('lirc', 'device', new_device)
      self.__restart__()
      bro = config_gui.browser_get()
      bro.refresh()
      
   def start_configurator(self):
      # recheck device
      self.__restart__()
      if not self.sok or not self.fdh:
         EmcDialog(title = 'No remote found', style = 'error',
                   text = 'Try to adjust your lirc socket address')
         return

      # wait for the first key
      self.grab_key_func = self.grabbed_key_func
      self.dia_state = 'up'
      self.dia = EmcDialog(title = 'Configure remote', style = 'cancel',
                      text = 'Press Up', done_cb = self.end_configurator)

   def grabbed_key_func(self, key):
      print key
      if self.dia_state == 'up':
         self.key_up = key
         self.dia.text_set('Press Down')
         self.dia_state = 'down'
      elif self.dia_state == 'down':
         self.key_down = key
         self.dia.text_set('Press Left')
         self.dia_state = 'left'
      elif self.dia_state == 'left':
         self.key_left = key
         self.dia.text_set('Press Right')
         self.dia_state = 'right'
      elif self.dia_state == 'right':
         self.key_right = key
         self.dia.text_set('Press Ok')
         self.dia_state = 'ok'
      elif self.dia_state == 'ok':
         self.key_ok = key
         self.dia.text_set('Press Back')
         self.dia_state = 'back'
      elif self.dia_state == 'back':
         self.key_back = key
         self.dia.text_set('config done.')
         self.dia_state = 'done'
         # end & save
         self.end_configurator()

   def end_configurator(self):
      self.grab_key_func = None
      self.dia.delete()
      ini.set('lirc', 'key_up', self.key_up)
      ini.set('lirc', 'key_down', self.key_down)
      ini.set('lirc', 'key_left', self.key_left)
      ini.set('lirc', 'key_right', self.key_right)
      ini.set('lirc', 'key_ok', self.key_ok)
      ini.set('lirc', 'key_back', self.key_back)

   
