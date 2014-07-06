#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2014 Davide Andreoli <dave@gurumeditation.it>
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

from operator import itemgetter, attrgetter

from efl import evas

from epymc import gui, mainmenu, input_events, ini, modules, utils
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.gui import EmcDialog, EmcVKeyboard

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

   def icon_end_get(self, url, user_data):
      return 'icon/forward'

class StdConfigItemBool(object): 
   # this don't inherit from EmcItemClass to not be a Singleton
   # this class is used by the function standard_item_bool_add(...)

   def __init__(self, section, option, label, icon=None, info=None, cb=None):
      self._sec = section
      self._opt = option
      self._lbl = label
      self._ico = icon
      self._inf = info
      self._cb = cb

   def item_selected(self, url, user_data):
      if ini.get(self._sec, self._opt) == "True":
         ini.set(self._sec, self._opt, "False")
      else:
         ini.set(self._sec, self._opt, "True")
      _browser.refresh()
      if callable(self._cb):
         self._cb()

   def icon_end_get(self, url, user_data):
      if ini.get(self._sec, self._opt) == "True":
         return 'icon/check_on'
      return 'icon/check_off'

   def label_get(self, url, user_data): return self._lbl
   def icon_get(self, url, user_data): return self._ico
   def info_get(self, url, user_data): return self._inf
   def poster_get(self, url, user_data): return None
   def fanart_get(self, url, user_data): return None

class StdConfigItemString(object): 
   # this don't inherit from EmcItemClass to not be a Singleton
   # this class is used by the function standard_item_string_add(...)

   def __init__(self, section, option, label, icon=None, info=None, cb=None):
      self._sec = section
      self._opt = option
      self._lbl = label
      self._ico = icon
      self._inf = info
      self._cb = cb

   def _kbd_accept_cb(self, vkeyb, text):
      ini.set(self._sec, self._opt, text)
      _browser.refresh()
      if callable(self._cb):
         self._cb()

   def item_selected(self, url, user_data):
      EmcVKeyboard(title=self._lbl, text=ini.get(self._sec, self._opt),
                   accept_cb=self._kbd_accept_cb)

   def label_get(self, url, user_data):
      return '%s  ( %s )' % (self._lbl, ini.get(self._sec, self._opt))

   def icon_get(self, url, user_data): return self._ico
   def icon_end_get(self, url, user_data): return None
   def info_get(self, url, user_data): return self._inf
   def poster_get(self, url, user_data): return None
   def fanart_get(self, url, user_data): return None

class StdConfigItemStringFromList(object): 
   # this don't inherit from EmcItemClass to not be a Singleton
   # this class is used by the function standard_item_string_add(...)

   def __init__(self, section, option, label, strlist, icon=None, info=None, cb=None):
      self._sec = section
      self._opt = option
      self._lbl = label
      self._ico = icon
      self._inf = info
      self._sli = strlist
      self._cb = cb

   def _dia_list_selected_cb(self, dia):
      item = dia.list_item_selected_get()
      ini.set(self._sec, self._opt, item.text)
      _browser.refresh()
      dia.delete()
      if callable(self._cb):
         self._cb()

   def item_selected(self, url, user_data):
      dia = EmcDialog(self._lbl, style='list', done_cb=self._dia_list_selected_cb)
      for string in self._sli:
         if string == ini.get(self._sec, self._opt):
            it = dia.list_item_append(string, end='icon/check_on')
            it.selected = True
         else:
            dia.list_item_append(string)

   def label_get(self, url, user_data):
      return '%s  ( %s )' % (self._lbl, ini.get(self._sec, self._opt))

   def icon_get(self, url, user_data): return self._ico
   def icon_end_get(self, url, user_data): return None
   def info_get(self, url, user_data): return self._inf
   def poster_get(self, url, user_data): return None
   def fanart_get(self, url, user_data): return None

class StdConfigItemAction(object): 
   # this don't inherit from EmcItemClass to not be a Singleton
   # this class is used by the function standard_item_action_add(...)

   def __init__(self, label, icon=None, info=None, selected_cb=None):
      self._lbl = label
      self._ico = icon
      self._inf = info
      self._cb = selected_cb

   def item_selected(self, url, user_data):
      if callable(self._cb):
         self._cb()

   def label_get(self, url, user_data): return self._lbl
   def icon_get(self, url, user_data): return self._ico
   def icon_end_get(self, url, user_data): return None
   def info_get(self, url, user_data): return self._inf
   def poster_get(self, url, user_data): return None
   def fanart_get(self, url, user_data): return None

### public functions
def init():
   global _browser

   mainmenu.item_add('config', 100, 'Config', 'icon/config', _mainmenu_cb)

   # create a browser instance
   _browser = EmcBrowser('Configuration', 'List') # TODO use a custom style for config ?

   root_item_add('config://general/', 1, 'General', 'icon/emc', _general_list)
   root_item_add('config://themes/', 2, 'Themes', 'icon/theme', _themes_list)
   root_item_add('config://modules/', 3, 'Modules', 'icon/module', _modules_list)

def shutdown():
   _browser.delete()

def root_item_add(name, weight, label, icon=None, callback=None):
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
      if _name in _root_items_dict:
         del _root_items_dict[_name]

def standard_item_bool_add(section, option, label, icon = None, info = None, cb = None):
   """ TODO doc """
   _browser.item_add(StdConfigItemBool(section, option, label, icon, info, cb),
                     'config://%s/%s' % (section, option), None)

def standard_item_string_add(section, option, label, icon = None, info = None, cb = None):
   """ TODO doc """
   _browser.item_add(StdConfigItemString(section, option, label, icon, info, cb),
                     'config://%s/%s' % (section, option), None)

def standard_item_string_from_list(section, option, label, strlist, icon = None, info = None, cb = None):
   """ TODO doc """
   _browser.item_add(StdConfigItemStringFromList(section, option, label, strlist, icon, info, cb),
                     'config://%s/%s' % (section, option), None)

def standard_item_action_add(label, icon = None, info = None, cb = None):
   """ TODO doc """
   _browser.item_add(StdConfigItemAction(label, icon, info, cb),
                     'config://useraction', None)

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

##############  GENERAL  ######################################################
def _general_list():
   _browser.page_add('config://general/', 'General', None, _general_populate)

def _general_populate(browser, url):
   standard_item_bool_add('general', 'fullscreen', 'Start in fullscreen')
   standard_item_action_add('Adjust interface scale', 'icon/scale', cb=_change_scale)
   standard_item_bool_add('general', 'back_in_lists', 'Show Back item in lists', 'icon/back')
   standard_item_string_add('general', 'download_folder', 'Download folder', 'icon/download')
   standard_item_string_add('general', 'max_concurrent_download', 'Max concurrent download', 'icon/download')

   L = evas.render_method_list()
   if 'buffer' in L: L.remove('buffer')
   if 'software_generic' in L: L.remove('software_generic')
   if 'gl_x11' in L:
      L.remove('gl_x11')
      L.append('opengl_x11')
   standard_item_string_from_list('general', 'evas_engine', 'Rendering engine',
                                  L, 'icon/evas')
   L = ['vlc', 'gstreamer1', 'gstreamer', 'xine', 'generic']
   standard_item_string_from_list('mediaplayer', 'backend', 'Multimedia engine',
                                  L, 'icon/evas')

   L = ['10', '20', '30', '60', '120']
   standard_item_string_from_list('general', 'fps', 'Frames per second',
                                  L, 'icon/evas', cb = _change_fps)

def _change_fps():
   gui.fps_set(ini.get_int('general', 'fps'))

def _change_scale():
   def _bigger(dialog): gui.scale_bigger(); _save()
   def _smaller(dialog): gui.scale_smaller(); _save()
   def _reset(dialog): gui.scale_set(1.0); _save()
   def _save():
      d.text_set('Current Value: %s' % (gui.scale_get()))
      ini.set('general', 'scale', str(gui.scale_get()))

   d = EmcDialog(title='set scale', style='minimal',
                 text='Current Value: %s' % (gui.scale_get()))
   d.button_add('Bigger', selected_cb=_bigger)
   d.button_add('Smaller', selected_cb=_smaller)
   d.button_add('Reset', selected_cb=_reset)
   
##############  THEMES  #######################################################

class ThemesItemClass(EmcItemClass):
   def item_selected(self, url, module):
      ini.set('general', 'theme', url)
      gui.set_theme_file(url)
      _browser.refresh()

   def label_get(self, url, theme_info):
      return theme_info['name']

   def icon_end_get(self, url, theme_info):
      if gui.theme_file == url:
         return 'icon/check_on'

   def info_get(self, url, theme_info):
      return '<title>%s</><br>' \
             '<hilight>author: </>%s<br>' \
             '<hilight>version: </>%s<br>' \
             '%s' % (
             theme_info['name'],
             theme_info['author'],
             theme_info['version'],
             theme_info['info'])

def _themes_list():
   _browser.page_add('config://themes/', 'Themes', None, _themes_populate)

def _themes_populate(browser, url):
   for theme in utils.get_available_themes():
      info = gui.get_theme_info(theme)
      if info:
         browser.item_add(ThemesItemClass(), theme, info)

##############  MODULES  ######################################################

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

