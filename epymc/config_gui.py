#!/usr/bin/env python

import evas
import elementary #REMOVEME


import gui
import mainmenu
import input

from browser import EmcBrowser

def DBG(msg):
   print('CONFIG_GUI: ' + msg)
   pass

### private globals
_browser = None # EmcBrowser instance
_root_items = [] # list of root items.  tuple:(name, label, weight, icon, cb)


### public functions
def init():
   global _browser

   mainmenu.item_add("config", 100, "Config", None, _mainmenu_cb)

   # create a browser instance
   _browser = EmcBrowser('Configuration', 'List', # TODO use a custom style for config ?
                               item_selected_cb = _item_selected_cb)
                               #~ icon_get_cb = self.cb_icon_get,
                               #~ poster_get_cb = self.cb_poster_get,
                               #~ info_get_cb = self.cb_info_get)

   root_item_add("modules", 1, "Modules", None, _modules_list)
   root_item_add("fs", 30, "Toggle Fullscreen / Windowed mode",
                 None, _toggle_fullscreen)
   root_item_add("emc://back", 999, "Close", None, None)

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

def root_item_del(name):
   for (_name, _label, _weight, _ic, _cb) in _root_items:
      if _name == name:
         _root_items.remove((_name, _label, _weight, _ic, _cb))
   # TODO TEST THIS

def make_root():
   _browser.page_add('config://root', 'Configuration')
   for (name, label, weight, icon, cb) in _root_items:
      _browser.item_add(name, label)

### private stuff
def _mainmenu_cb():
   make_root()
   show()

def _item_selected_cb(page, item):
   if item == 'config://root':
      make_root()

   elif page == 'config://root':
      for (name, label, weight, icon, cb) in _root_items:
         if item == name:
            if callable(cb):
               cb()
            break

##############  FULLSCREEN  ###################################################
import ini

def _toggle_fullscreen():
   ini.set('general', 'fullscreen', not gui.win.fullscreen)
   input.event_emit('TOGGLE_FULLSCREEN')

##############  MODULES  ######################################################
import modules

def _modules_list():
   _browser.page_add('config://modules/', 'Modules',
                     item_selected_cb = _module_selected_cb,
                     icon_get_cb = _module_icon_get,
                     icon_end_get_cb = _module_icon_end_get,
                     info_get_cb = _module_info_get,
                     poster_get_cb = _module_icon_get)

   for mod in modules.list_get():
      _browser.item_add(mod.name, mod.label)

   _browser.item_add('emc://back', 'Back')

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
