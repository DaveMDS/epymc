#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2016 Davide Andreoli <dave@gurumeditation.it>
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

from efl import ecore

from epymc.modules import EmcModule
from epymc.browser import EmcItemClass
from epymc.gui import EmcDialog
import epymc.input_events as input_events
import epymc.config_gui as config_gui
import epymc.gui as gui
import epymc.ini as ini


def DBG(msg):
   # print('KEYB: %s' % msg)
   pass


# map ecore keys to emc input events
DEFAULTS = { 
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
   'F2': 'VIEW_POSTERGRID',
   'F3': 'VIEW_COVERGRID',
   'F5': 'SCALE_SMALLER',
   'F6': 'SCALE_BIGGER',
   'F7': 'SCALE_RESET',
   's': 'STOP',
   'z': 'FAST_BACKWARD',
   'x': 'BACKWARD',
   'c': 'FORWARD',
   'v': 'FAST_FORWARD',
   'b': 'PLAYLIST_PREV',
   'n': 'PLAYLIST_NEXT',
   'q': 'SUBS_DELAY_LESS',
   'w': 'SUBS_DELAY_MORE',
   'e': 'SUBS_DELAY_ZERO',
}

class KeyboardModule(EmcModule):
   name = 'input_keyb'
   label = _('Input - Keyboard')
   icon = 'icon/keyboard'
   info = _('The keyboard module lets you control the application using '
            'your keyboard, or any other device that act as a keyboard.')

   def __init__(self):
      DBG('Init module')

      self.grab_key_func = None

      # set up default bindings
      section = 'keyboard'
      if not ini.has_section(section):
         ini.add_section(section)
         for key, event in DEFAULTS.items():
            ini.set(section, key, event)

      # read mapping from config
      self.keys = dict()
      for key, event in ini.get_options(section):
         DBG('Map key "%s" to event %s' % (key, event))
         self.keys[key] = event
      
      # add an entry in the config gui section
      config_gui.root_item_add('keyb', 50, _('Keyboard'), icon='icon/keyboard',
                               callback=self.config_panel_cb)

      # ask the gui to forward key events to us
      gui.key_down_func = self._key_down_cb

   def __shutdown__(self):
      DBG('Shutdown module')
      config_gui.root_item_del('keyb')
      gui.key_down_func = None

   def _key_down_cb(self, event):
      key = event.key.lower()
      DBG('Key: %s (%s)' % (key, event.key))

      # if grabbed request call the grab function, else emit the signal
      if self.grab_key_func and callable(self.grab_key_func):
         self.grab_key_func(key)
      else:
         if key in self.keys:
            input_events.event_emit(self.keys[key])
         else:
            print('Unhandled key: ' + event.key)

      return ecore.ECORE_CALLBACK_DONE

   ### config panel stuff
   class KeyItemClass(EmcItemClass):
      def item_selected(self, url, data):
         key, event, mod = data
         txt = '%s<br><br>%s ⇾ %s' % (
               _('Are you sure you want to remove the mapping?'),
               key, event)
         EmcDialog(style='yesno', title=_('Remove key'), text=txt,
                   done_cb=self._remove_confirmed, user_data=data)

      def _remove_confirmed(self, dia):
         key, event, mod = dia.data_get()

         # remove key from mapping and from config
         mod.keys.pop(key, None)
         ini.remove_option('keyboard', key)

         # kill the dialog and refresh the browser
         bro = config_gui.browser_get()
         bro.refresh(hard=True)
         dia.delete()

      def label_get(self, url, data):
         key, event, mod = data
         return key

      def label_end_get(self, url, data):
         key, event, mod = data
         return event

      def icon_get(self, url, data):
         return 'icon/key'

   def config_panel_cb(self):
      bro = config_gui.browser_get()
      bro.page_add('config://keyb/', _('Keyboard'), None, self.populate_keyb)

   def populate_keyb(self, browser, url):
      config_gui.standard_item_action_add(_('Add a new key'), icon='icon/plus',
                                          cb=self._add_item_cb)
      for key, event in sorted(self.keys.items(), key=lambda x: x[1]):
         browser.item_add(self.KeyItemClass(), 'config://keyb/button', (key, event, self))
      

   def _add_item_cb(self):
      # grab the next pressed key and show the first dialog
      self.grab_key_func = self.grabbed_key_func
      self.dia = EmcDialog(title=_('Add a new key'), style='cancel',
                           text=_('Press a key on your keyboard'),
                           canc_cb=self.ungrab_key)

   def ungrab_key(self, dialog):
      self.grab_key_func = None
      dialog.delete()

   def grabbed_key_func(self, key):
      # ungrab remote keys & delete the first dialog
      self.grab_key_func = None
      self.pressed_key = key
      self.dia.delete()

      # create the dialog to choose the event to bind
      dia = EmcDialog(title=_('Choose an event to bind'), style='list',
                      done_cb=self.event_choosed_cb)
      for event in input_events.STANDARD_EVENTS.split():
         dia.list_item_append(event)
      dia.list_go()

   def event_choosed_cb(self, dia):
      event = str(dia.list_item_selected_get().text_get())
      key = str(self.pressed_key)

      # save the pressed key in mapping and config
      self.keys[key] = event
      ini.set('keyboard', key, event)

      # kill the dialog and refresh the browser
      dia.delete()
      bro = config_gui.browser_get()
      bro.refresh(hard=True)
