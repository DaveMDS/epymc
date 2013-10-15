#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2013 Davide Andreoli <dave@gurumeditation.it>
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

from socket import *

from efl import ecore, elementary
from efl.elementary.list import List

from epymc.modules import EmcModule
import epymc.input_events as input_events
from epymc.gui import EmcVKeyboard, EmcDialog
from epymc.browser import EmcItemClass
import epymc.ini as ini
import epymc.gui as gui
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

   def __init__(self):
      DBG('Init module')

      self.grab_key_func = None
      
      # get lirc socket from config
      ini.add_section('lirc')
      if not ini.has_option('lirc', 'device'):
         ini.set('lirc', 'device', self.DEFAULT_LIRC_SOCKET)
      self.device = ini.get('lirc', 'device')
      
      # add an entry in the config section
      config_gui.root_item_add('lirc', 51, 'Remote', icon = 'icon/remote',
                               callback = self.config_panel_cb)

      # build the lirc_key => emc_input_event mapping from config
      # self.keys => { 'lirc_key': 'emc_event', 'lirc_key': 'emc_event', ... }
      self.keys = dict()
      for name, lirc_key in ini.get_options('lirc'):
         if name.startswith('key_'):
            event = name[4:].upper()
            for key in lirc_key.split('|'):
               self.keys[key] = event
      DBG(str(self.keys))

      # try to open the lircd socket
      try:
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
      # try to decode the lirc messagge
      # ex: CODE REPEAT KEY_NAME REMOTE_NAME
      #     000000ab 00 KEY_UP MyRemoteName
      try:
         data = self.sok.recv(128)
         code, repeat, key, remote = data.strip().split()
         DBG('code:%s repeat:%s key:%s remote:%s' % (code, repeat, key, remote))
      except:
         print('Error: cannot decode lirc messagge')
         return True

      # if grabbed request call the grab function, else emit the signal
      if self.grab_key_func and callable(self.grab_key_func):
         if repeat == '00':
            self.grab_key_func(key)
      else:
         if key in self.keys:
            signal = self.keys[key]
            if signal in ['OK', 'BACK', 'VOLUME_MUTE', 'TOGGLE_PAUSE']:
               # dont repeat this signals
               if repeat == '00':
                  input_events.event_emit(signal)
            else:
               # repeatable signals
               input_events.event_emit(signal)

      return True

   ### config panel stuff
   class KeyItemClass(EmcItemClass):
      def label_get(self, url, data):
         key, event = data
         return 'Button: %s  Event: %s' % (key, event)

   class AddKeyItemClass(EmcItemClass):
      def label_get(self, url, mod):
         return 'Add a new key'

      def icon_get(self, url, mod):
         return 'icon/plus'

      def item_selected(self, url, mod):
         mod.ask_a_single_key()


   def config_panel_cb(self):
      bro = config_gui.browser_get()
      bro.page_add('config://lirc/', 'Remote', None, self.populate_lirc)

   def populate_lirc(self, browser, url):
      config_gui.standard_item_string_add('lirc', 'device', 'Lirc socket',
                                 'icon/remote', cb = self.device_changed_cb)
         
      for key, event in self.keys.items():
         browser.item_add(self.KeyItemClass(), 'config://lirc/button', (key, event))
      browser.item_add(self.AddKeyItemClass(), 'config://lirc/addkey', self)
      self.check_lirc()

   def device_changed_cb(self):
      self.__restart__()
      self.check_lirc()

   def check_lirc(self):
      if not self.sok or not self.fdh:
         EmcDialog(style = 'error',
            text = 'Cannot connect to lirc using socket:<br>' + self.device)
         return False
      return True

   def ask_a_single_key(self):
      self.grab_key_func = self.grabbed_key_func
      self.dia = EmcDialog(title = 'Configure remote', style = 'cancel',
                           text = 'Press a key on your remote',
                           canc_cb = self.ungrab_key)
   
   def ungrab_key(self, dialog):
      self.grab_key_func = None
      dialog.delete()

   def grabbed_key_func(self, key):
      # ungrab remote keys & delete the first dialog
      self.grab_key_func = None
      self.dia.delete()
      
      # create the events list
      li = List(gui.win)
      li.focus_allow_set(False)
      for event in input_events.STANDARD_EVENTS.split():
         li.item_append(event, None, None, None, None)
      li.items_get()[0].selected_set(1)
      li.show()
      li.go()

      # put the list in a new dialog
      dialog = EmcDialog(title = 'Choose an event to bind', style = 'minimal',
                         content = li, done_cb = self.event_choosed_cb)
      li.callback_clicked_double_add((lambda l,i: self.event_choosed_cb(dialog)))
      self.pressed_key = key

   def event_choosed_cb(self, dialog):
      li = dialog.content_get()
      item = li.selected_item_get()
      event = item.text_get()
      key = self.pressed_key

      # update the keys mapping
      self.keys[key] = event

      # update ini
      for key, event in self.keys.items():
         ini.set('lirc', 'key_'+event.lower(), key)
      dialog.delete()

      # redraw the browser
      config_gui.browser_get().refresh(hard=True)

