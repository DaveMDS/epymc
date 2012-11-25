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

from operator import itemgetter, attrgetter

import evas

import gui
import mainmenu
import input_events

from browser import EmcBrowser, EmcItemClass
from widgets import EmcDialog

def DBG(msg):
   print('CONFIG_GUI: ' + msg)
   pass

### private globals
_browser = None # EmcBrowser instance
_root_items = [] # ordered list of root items.  tuple:(name, label, weight, icon, cb)
_root_items_dict = {} # also keep a dict of items, key = name, val = tuple (name,...,cb)


class RootItemClass(EmcItemClass):
   def item_selected(self, url, user_data):
      (name, label, weight, icon, callback) = user_data
      if callable(callback):
         callback()

   def label_get(self, url, user_data):
      (name, label, weight, icon, callback) = user_data
      return label

   def icon_get(self, url, user_data):
      (name, label, weight, icon, callback) = user_data
      return icon


### public functions
def init():
   global _browser

   mainmenu.item_add('config', 100, 'Config', None, _mainmenu_cb)

   # create a browser instance
   _browser = EmcBrowser('Configuration', 'List') # TODO use a custom style for config ?

   root_item_add('config://modules/', 1, 'Modules', 'icon/module', _modules_list)
   root_item_add('config://scale/', 20, 'Scale', 'icon/scale', _change_scale)
   root_item_add('config://fs/', 30, 'Fullscreen',
                 None, _toggle_fullscreen)

def shutdown():
   _browser.delete()

def root_item_add(name, weight, label, icon = None, callback = None):
   # search an item with an higer weight
   pos = 0
   for (_name, _label, _weight, _ic, _cb) in _root_items:
      if weight <= _weight: break
      pos += 1

   # place in the correct position
   _root_items.insert(pos, (name, label, weight, icon, callback))
   _root_items_dict[name] = (name, label, weight, icon, callback)

def root_item_del(name):
   # TODO TEST THIS
   for (_name, _label, _weight, _ic, _cb) in _root_items:
      if _name == name:
         _root_items.remove((_name, _label, _weight, _ic, _cb))
      if _root_items_dict.has_key(_name):
         del _root_items_dict[_name]

def browser_get():
   return _browser

### private stuff
def _mainmenu_cb():
   _browser.page_add('config://root', 'Configuration', None, _populate_root)
   _browser.show()
   mainmenu.hide()

def _populate_root(browser, url):
   for item in _root_items:
      browser.item_add(RootItemClass(), item[0], item)

##############  GUI  #########################################################
import ini

def _toggle_fullscreen():
   ini.set('general', 'fullscreen', not gui.win.fullscreen)
   input_events.event_emit('TOGGLE_FULLSCREEN')

def _change_scale():
   def _bigger(dialog): gui.scale_bigger(); _save()
   def _smaller(dialog): gui.scale_smaller(); _save()
   def _reset(dialog): gui.scale_set(1.0); _save()
   def _save():
      d.text_set('Current Value: %s' % (gui.scale_get()))
      ini.set('general', 'scale', str(gui.scale_get()))

   d = EmcDialog(title = 'set scale', style = 'minimal',
                 text = 'Current Value: %s' % (gui.scale_get()))
   d.button_add('Bigger', selected_cb = _bigger)
   d.button_add('Smaller', selected_cb = _smaller)
   d.button_add('Reset', selected_cb = _reset)
   

##############  MODULES  ######################################################
import modules

class ModulesItemClass(EmcItemClass):
   def item_selected(self, url, module):
      if modules.is_enabled(url):
         modules.shutdown_by_name(url)
      else:
         modules.init_by_name(url)
      _browser.refresh()


   def label_get(self, url, module):
      return module.label

   def icon_get(self, url, module):
      return module.icon

   def icon_end_get(self, url, module):
      if modules.is_enabled(url):
         return 'icon/check_on'
      else:
         return 'icon/check_off'

   def info_get(self, url, module):
      return module.info

def _modules_list():
   _browser.page_add('config://modules/', 'Modules', None, _modules_populate)

def _modules_populate(browser, url):
   for mod in sorted(modules.list_get(), key=attrgetter('name')):
      browser.item_add(ModulesItemClass(), mod.name, mod)


