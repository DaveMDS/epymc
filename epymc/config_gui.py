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

from operator import itemgetter, attrgetter

import evas
import elementary #REMOVEME

import gui
import mainmenu
import input_events

from browser import EmcBrowser

def DBG(msg):
   print('CONFIG_GUI: ' + msg)
   pass

### private globals
_browser = None # EmcBrowser instance
_root_items = [] # ordered list of root items.  tuple:(name, label, weight, icon, cb)
_root_items_dict = {} # also keep a dict of items, key = name, val = tuple (name,...,cb)


### public functions
def init():
   global _browser

   mainmenu.item_add('config', 100, 'Config', None, _mainmenu_cb)

   # create a browser instance
   _browser = EmcBrowser('Configuration', 'List', # TODO use a custom style for config ?
                               item_selected_cb = _item_selected_cb,
                               icon_get_cb = _item_icon_get_cb)
                               #~ poster_get_cb = self.cb_poster_get,
                               #~ info_get_cb = self.cb_info_get)

   root_item_add('config://modules/', 1, 'Modules', 'icon/module', _modules_list)
   root_item_add('config://scale/', 20, 'Scale', 'icon/scale', _change_scale)
   root_item_add('config://fs/', 30, 'Fullscreen',
                 None, _toggle_fullscreen)

def shutdown():
   _browser.delete()

def show():
   _browser.show()
   mainmenu.hide()

#~ def hide():
   #~ _browser.hide()
   #~ mainmenu.show()

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
   for (_name, _label, _weight, _ic, _cb) in _root_items:
      if _name == name:
         _root_items.remove((_name, _label, _weight, _ic, _cb))
      if _root_items_dict.has_key(_name):
         del _root_items_dict[_name]
   
   # TODO TEST THIS

def make_root():
   _browser.page_add('config://root', 'Configuration')
   for (name, label, weight, icon, cb) in _root_items:
      _browser.item_add(name, label)

def browser_get():
   return _browser

### private stuff
def _mainmenu_cb():
   make_root()
   show()

def _item_icon_get_cb(page, item):
   if _root_items_dict.has_key(item):
      return _root_items_dict[item][3]

def _item_selected_cb(page, item):
   if item == 'config://root':
      make_root()

   elif page == 'config://root':
      cb = _root_items_dict[item][4]
      if callable(cb):
         cb()
         # for (name, label, weight, icon, cb) in _root_items:
            # if item == name:
               # if callable(cb):
               # 
            # break

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

   d = gui.EmcDialog(title = 'set scale', style = 'minimal',
                     text = 'Current Value: %s' % (gui.scale_get()))
   d.button_add('Bigger', selected_cb = _bigger)
   d.button_add('Smaller', selected_cb = _smaller)
   d.button_add('Reset', selected_cb = _reset)
   

##############  MODULES  ######################################################
import modules

def _modules_list():
   _browser.page_add('config://modules/', 'Modules',
                     item_selected_cb = _module_selected_cb,
                     icon_get_cb = _module_icon_get,
                     icon_end_get_cb = _module_icon_end_get,
                     info_get_cb = _module_info_get,
                     poster_get_cb = _module_icon_get)

   for mod in sorted(modules.list_get(), key=attrgetter('name')):
      _browser.item_add(mod.name, mod.label)

def _module_icon_get(page, item):
   mod = modules.get_module_by_name(item)
   return mod.icon if mod else None

def _module_icon_end_get(page, item):
   if modules.is_enabled(item):
      return 'icon/check_on'
   else:
      return 'icon/check_off'

def _module_info_get(page, item):
   mod = modules.get_module_by_name(item)
   return mod.info if mod else None

def _module_selected_cb(page, item):
   if modules.is_enabled(item):
      modules.shutdown_by_name(item)
   else:
      modules.init_by_name(item)
   _browser.refresh()
