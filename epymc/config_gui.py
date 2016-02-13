#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2015 Davide Andreoli <dave@gurumeditation.it>
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

import os
import sys
from operator import itemgetter, attrgetter

from efl import evas, ecore

from epymc import gui, mainmenu, input_events, ini, modules, utils
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.gui import EmcDialog, EmcVKeyboard

def DBG(msg):
   print('CONFIG_GUI: %s' % msg)
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

class StdConfigItemBase(object):
   """ Base class for all the other StdConfigItem* classes.

   Do not inherit from EmcItemClass to not be a Singleton.

   """

   def __init__(self, section, option, label, icon=None, info=None, cb=None):
      self._sec = section
      self._opt = option
      self._lbl = label
      self._ico = icon
      self._inf = info
      self._cb = cb

   def __done__(self):
      _browser.refresh()
      if callable(self._cb):
         self._cb()

   def item_selected(self, url, user_data):
      self.__done__()

   def label_get(self, url, user_data):
      return self._lbl

   def label_end_get(self, url, user_data):
      return None

   def icon_get(self, url, user_data):
      return self._ico

   def icon_end_get(self, url, user_data):
      return None

   def info_get(self, url, user_data):
      return self._inf

   def poster_get(self, url, user_data):
      return None

   def cover_get(self, url, user_data):
      return None

   def fanart_get(self, url, user_data):
      return None

class StdConfigItemBool(StdConfigItemBase): 
   """ This class is used by the function standard_item_bool_add(...) """

   def __init__(self, *args):
      StdConfigItemBase.__init__(self, *args)

   def item_selected(self, url, user_data):
      if ini.get(self._sec, self._opt) == 'True':
         ini.set(self._sec, self._opt, 'False')
      else:
         ini.set(self._sec, self._opt, 'True')
      StdConfigItemBase.__done__(self)

   def icon_end_get(self, url, user_data):
      if ini.get_bool(self._sec, self._opt) is True:
         return 'icon/check_on'
      return 'icon/check_off'

class StdConfigItemString(StdConfigItemBase): 
   """ This class is used by the function standard_item_string_add(...) """

   def __init__(self, pwd=False, *args):
      self._pwd = pwd
      StdConfigItemBase.__init__(self, *args)

   def _kbd_accept_cb(self, vkeyb, text):
      ini.set(self._sec, self._opt, text)
      StdConfigItemBase.__done__(self)

   def item_selected(self, url, user_data):
      EmcVKeyboard(title=self._lbl, accept_cb=self._kbd_accept_cb,
                   text=ini.get(self._sec, self._opt) if not self._pwd else '')

   def label_end_get(self, url, user_data):
      val = ini.get(self._sec, self._opt)
      return '●●●●●' if self._pwd and val else val

class StdConfigItemStringFromList(StdConfigItemBase): 
   """ Used by the function standard_item_string_from_list_add(...) """

   def __init__(self, strlist, *args):
      self._sli = strlist
      StdConfigItemBase.__init__(self, *args)

   def _dia_list_selected_cb(self, dia):
      item = dia.list_item_selected_get()
      ini.set(self._sec, self._opt, item.text)
      dia.delete()
      StdConfigItemBase.__done__(self)

   def item_selected(self, url, user_data):
      dia = EmcDialog(self._lbl, style='list',
                      done_cb=self._dia_list_selected_cb)
      for string in self._sli:
         if string == ini.get(self._sec, self._opt):
            it = dia.list_item_append(string, end='icon/check_on')
            it.selected = True
         else:
            dia.list_item_append(string)
      dia.list_go()

   def label_end_get(self, url, user_data):
      return ini.get(self._sec, self._opt)

class StdConfigItemLang(StdConfigItemBase): 
   """ this class is used by the function standard_item_lang_add(...) """

   def __init__(self, multi=False, *args):
      self._mul = multi
      StdConfigItemBase.__init__(self, *args)

   def _dia_list_selected_cb(self, dia):
      item = dia.list_item_selected_get()
      lang = item.data['code2']

      if self._mul:
         L = ini.get_string_list(self._sec, self._opt)
         L.remove(lang) if lang in L else L.append(lang)
         if len(L) < 1: L.append('en')
         ini.set_string_list(self._sec, self._opt, L)
      else:
         ini.set(self._sec, self._opt, lang)

      dia.delete()
      StdConfigItemBase.__done__(self)

   def item_selected(self, url, user_data):
      dia = EmcDialog(self._lbl, style='list', done_cb=self._dia_list_selected_cb)

      if self._mul:
         choosed = ini.get_string_list(self._sec, self._opt)
      else:
         choosed = [ ini.get(self._sec, self._opt) ]

      item = None
      for code2, (code3, code5, name) in sorted(utils.iso639_table.items(),
                                                key=lambda x: x[1][2]):
         if name is not None:
            if code2 in choosed:
               item = dia.list_item_append(name, end='icon/check_on')
               item.data['code2'] = code2
            else:
               it = dia.list_item_append(name)
               it.data['code2'] = code2
      dia.list_go()

      if item:
         item.show()
         item.selected = True

   def label_end_get(self, url, user_data):
      return ini.get(self._sec, self._opt)

class StdConfigItemIntMeaning(StdConfigItemBase): 
   """ this class is used by the function standard_item_int_meaning_add(...) """

   def __init__(self, values, *args):
      self._vals = values
      StdConfigItemBase.__init__(self, *args)

   def item_selected(self, url, user_data):
      dia = EmcDialog(self._lbl, style='list',
                      done_cb=self._dia_list_selected_cb)
      i = 0
      for string in self._vals:
         if i == ini.get_int(self._sec, self._opt):
            it = dia.list_item_append(string, end='icon/check_on')
            it.selected = True
         else:
            it = dia.list_item_append(string)
         it.data['i'] = i
         i += 1
      dia.list_go()

   def _dia_list_selected_cb(self, dia):
      item = dia.list_item_selected_get()
      ini.set(self._sec, self._opt, item.data['i'])
      dia.delete()
      StdConfigItemBase.__done__(self)

   def label_end_get(self, url, user_data):
      i = ini.get_int(self._sec, self._opt)
      return self._vals[i]

class StdConfigItemAction(StdConfigItemBase): 
   """ This class is used by the function standard_item_action_add(...) """

   def __init__(self, label, icon=None, info=None, selected_cb=None):
      self._lbl = label
      self._ico = icon
      self._inf = info
      self._cb = selected_cb

   def item_selected(self, url, user_data):
      if callable(self._cb):
         self._cb()

class StdConfigItemNumber(StdConfigItemBase):
   def __init__(self, fmt, udm, min, max, step, *args):
      self._fmt = fmt
      self._udm = udm
      self._min = min
      self._max = max
      self._step = step
      self._val = None
      self._dia = None
      StdConfigItemBase.__init__(self, *args)

   def label_end_get(self, url, user_data):
      if self._udm:
         return ini.get(self._sec, self._opt) + ' ' + self._udm
      else:
         return ini.get(self._sec, self._opt)

   def item_selected(self, url, user_data):
      self._val = ini.get_float(self._sec, self._opt)
      self._dia = EmcDialog(style='minimal', title=self._lbl, text='')
      self._dia.button_add(_('Ok'), self._btn_ok_cb)
      self._dia.button_add(None, self._btn_plus_cb, icon='icon/plus')
      self._dia.button_add(None, self._btn_minus_cb, icon='icon/minus')
      self._dia.button_add(_('Cancel'), self._btn_canc_cb)
      self._dia_text_update()

   def _dia_text_update(self):
      val = (self._fmt % self._val) + ' ' + self._udm
      self._dia.text_set('<br><br><br><center><bigger>%s</bigger></center>' % val)

   def _btn_plus_cb(self, btn):
      self._val += self._step
      self._val = min(self._val, self._max)
      self._dia_text_update()

   def _btn_minus_cb(self, btn):
      self._val -= self._step
      self._val = max(self._val, self._min)
      self._dia_text_update()

   def _btn_canc_cb(self, btn):
      self._dia.delete()

   def _btn_ok_cb(self, btn):
      val = self._fmt % self._val
      ini.set(self._sec, self._opt, val)
      self._dia.delete()
      StdConfigItemBase.__done__(self)

### public functions
def init():
   global _browser

   mainmenu.item_add('config', 100, _('Configuration'), 'icon/config', _mainmenu_cb)

   # create a browser instance
   _browser = EmcBrowser(_('Configuration'), 'List', 'icon/config')

   root_item_add('config://general/', 1, _('General'), 'icon/emc', _general_list)
   root_item_add('config://modules/', 2, _('Modules'), 'icon/module', _modules_list)
   root_item_add('config://themes/', 3, _('Themes'), 'icon/theme', _themes_list)
   root_item_add('config://views/', 4, _('Views'), 'icon/views', _views_list)
   root_item_add('config://subtitles/', 5, _('Subtitles'), 'icon/subs', _subtitles_list)
   root_item_add('config://sysinfo/', 90, _('System info'), 'icon/info', _sys_info)

def shutdown():
   _browser.delete()

def root_item_add(name, weight, label, icon=None, callback=None):
   """
      weight used:
         1, 2, 3: General, Themes, Modules
         10, 11: movies, tvshows
         15: subtitles
         20: screensaver
         50, 51, 52, 53: keyboard, lirc, joy, webserver
         100: screen calibrator
   """
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

def standard_item_bool_add(section, option, label, icon=None, info=None, cb=None):
   """ TODO doc """
   _browser.item_add(StdConfigItemBool(section, option, label, icon, info, cb),
                     'config://%s/%s' % (section, option), None)

def standard_item_string_add(section, option, label, icon=None, info=None, cb=None, pwd=False):
   """ TODO doc """
   _browser.item_add(StdConfigItemString(pwd, section, option, label, icon, info, cb),
                     'config://%s/%s' % (section, option), None)

def standard_item_string_from_list_add(section, option, label, strlist, icon=None, info=None, cb=None):
   """ TODO doc """
   _browser.item_add(StdConfigItemStringFromList(strlist, section, option, label, icon, info, cb),
                     'config://%s/%s' % (section, option), None)

def standard_item_lang_add(section, option, label, multi=False, icon=None, info=None, cb=None):
   """ TODO doc """
   _browser.item_add(StdConfigItemLang(multi, section, option, label, icon, info, cb),
                     'config://%s/%s' % (section, option), None)

def standard_item_int_meaning_add(section, option, label, values, icon=None, info=None, cb=None):
   """ TODO doc """
   _browser.item_add(StdConfigItemIntMeaning(values, section, option, label, icon, info, cb),
                     'config://%s/%s' % (section, option), None)

def standard_item_action_add(label, icon=None, info=None, cb=None):
   """ TODO doc """
   _browser.item_add(StdConfigItemAction(label, icon, info, cb),
                     'config://useraction', None)

def standard_item_number_add(section, option, label, icon=None, info=None, cb=None, fmt='%.0f', udm='', min=0, max=100, step=1):
   """ TODO doc """
   _browser.item_add(StdConfigItemNumber(fmt, udm, min, max, step, section, option, label, icon, info, cb),
                     'config://%s/%s' % (section, option), None)

def browser_get():
   return _browser

### private stuff
def _mainmenu_cb():
   _browser.page_add('config://root', _('Configuration'), None, _populate_root)
   _browser.show()
   mainmenu.hide()

def _populate_root(browser, url):
   for item in _root_items:
      browser.item_add(RootItemClass(), item[0], item)

##############  GENERAL  ######################################################

def _general_list():
   _browser.page_add('config://general/', _('General'), None, _general_populate)

def _general_populate(browser, url):
   standard_item_bool_add('general', 'fullscreen', _('Start in fullscreen'))
   standard_item_bool_add('general', 'hide_mouse', _('Hide mouse cursor when not needed'))

   vals = (_('Ask'), _('Always'), _('Never'))
   standard_item_int_meaning_add('mediaplayer', 'resume_from_last_pos',
                                _('Resume playback'), values=vals)   
   standard_item_number_add('general', 'scale',
                            _('Interface scale'), 'icon/scale',
                            fmt='%.1f', udm='x', min=0.5, max=2.0, step=0.1,
                            cb=_change_scale)
   standard_item_action_add(_('Virtual keyboard layouts'), 'icon/key',
                            cb=_vkeyb_layouts_list)
   standard_item_string_add('general', 'download_folder',
                            _('Download folder'), 'icon/download')
   standard_item_number_add('general', 'max_concurrent_download',
                            _('Max concurrent download'), 'icon/download',
                            fmt='%.0f', min=1, max=10, step=1)
   standard_item_string_add('general', 'time_format', _('Time format'))
   standard_item_string_add('general', 'date_format', _('Date format'))

   # L = evas.render_method_list()
   # for remove in ('buffer', 'software_generic', 'gl_generic'):
   #    if remove in L: L.remove(remove)
   # if 'gl_x11' in L:
   #    L.remove('gl_x11')
   #    L.append('opengl_x11')
   # standard_item_string_from_list_add('general', 'evas_engine',
                                      # _('Rendering engine'), L, 'icon/evas',
                                      # cb=_restart_needed)
   standard_item_bool_add('general', 'evas_accelerated',
                          _('Use hardware acceleration'), 'icon/evas',
                          cb=_restart_needed)

   L = ['vlc', 'gstreamer1', 'gstreamer', 'xine', 'generic']
   standard_item_string_from_list_add('mediaplayer', 'backend',
                                      _('Multimedia engine'), L, 'icon/evas')

   standard_item_number_add('general', 'fps',
                            _('Frames per second'), 'icon/evas',
                            fmt='%.0f', udm='fps', min=10, max=120, step=10,
                            cb=_change_fps)
   standard_item_action_add(_('Clear thumbnails cache'), icon='icon/refresh',
                            cb=_clear_thumbnails_cache)
   standard_item_action_add(_('Clear online images cache'), icon='icon/refresh',
                            cb=_clear_remotes_cache)

def _restart_needed():
   EmcDialog(style='info', title=_('Restart needed'),
      text=_('You need to restart the program to apply the new configuration.'))

def _change_fps():
   gui.fps_set(ini.get_int('general', 'fps'))

def _change_scale():
   gui.scale_set(ini.get_float('general', 'scale'))

def _clear_thumbnails_cache():
   def _idler_cb(generator):
      try:
         fname = next(generator)
         os.remove(fname)
         dia.my_counter += 1
      except StopIteration:
         EmcDialog(style='cancel',  title=_('Clear thumbnails cache'),
               text='Operation completed, %d files deleted.' % dia.my_counter)
         dia.delete()
         return ecore.ECORE_CALLBACK_CANCEL
      return ecore.ECORE_CALLBACK_RENEW

   dia = EmcDialog(style='minimal', title=_('Clear thumbnails cache'),
                  spinner=True, text=_('Operation in progress, please wait...'))
   dia.my_counter = 0
   gen = utils.grab_files(os.path.join(utils.user_cache_dir, 'thumbs'))
   ecore.Idler(_idler_cb, gen)

def _clear_remotes_cache():
   def _idler_cb(generator):
      try:
         fname = next(generator)
         os.remove(fname)
         dia.my_counter += 1
      except StopIteration:
         EmcDialog(style='cancel',  title=_('Clear online images cache'),
               text='Operation completed, %d files deleted.' % dia.my_counter)
         dia.delete()
         return ecore.ECORE_CALLBACK_CANCEL
      return ecore.ECORE_CALLBACK_RENEW

   dia = EmcDialog(style='minimal', title=_('Clear online images cache'),
                  spinner=True, text=_('Operation in progress, please wait...'))
   dia.my_counter = 0
   gen = utils.grab_files(os.path.join(utils.user_cache_dir, 'remotes'))
   ecore.Idler(_idler_cb, gen)

def _vkeyb_layouts_list():
   dia = EmcDialog(title=_('Virtual keyboard layouts'), style='list',
                   done_cb=_vkeyb_layouts_select_cb)
   dia.button_add(_('Close'),
                  selected_cb=_vkeyb_layouts_close_cb, cb_data=dia)
   dia.button_add(_('Select'), default=True,
                  selected_cb=_vkeyb_layouts_select_cb, cb_data=dia)

   avail = ini.get_string_list('general', 'keyb_layouts')
   for k in sorted(gui.keyboard_layouts.keys()):
      name = gui.keyboard_layouts[k][0]
      end = 'icon/check_on' if k in avail else 'icon/check_off'
      it = dia.list_item_append(name, end=end)
      it.data['key'] = k

def _vkeyb_layouts_select_cb(obj, dia=None):
   if not dia: dia = obj
   it = dia.list_item_selected_get()
   key = it.data['key']
   avail = ini.get_string_list('general', 'keyb_layouts')

   if key in avail:
      avail.remove(key)
      dia.list_item_icon_set(it, 'icon/check_off', end=True)
   else:
      avail.append(key)
      dia.list_item_icon_set(it, 'icon/check_on', end=True)

   ini.set_string_list('general', 'keyb_layouts', sorted(avail))

def _vkeyb_layouts_close_cb(btn, dia):
   dia.delete()

##############  VIEWS  ########################################################

def _views_list():
   _browser.page_add('config://views/', _('Views'), None, _views_populate)
   
def _views_populate(browser, url):
   standard_item_bool_add('general', 'back_in_lists',
                          _('Show Back item in lists'), 'icon/back')
   standard_item_number_add('general', 'view_postergrid_size',
                            _('Poster grid items size'), 'icon/view_postergrid',
                            fmt='%.0f', udm='px', min=50, max=500, step=25)
   standard_item_number_add('general', 'view_covergrid_size',
                            _('Cover grid items size'), 'icon/view_covergrid',
                            fmt='%.0f', udm='px', min=50, max=500, step=25)
   standard_item_bool_add('general', 'ignore_views_restrictions',
                          _('Ignore views restrictions for pages'))
   
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
      return '<title>%s</><br><name>%s:</> %s<br>' \
             '<name>%s:</> %s<br>%s' % (
               theme_info['name'], _('Author'), theme_info['author'],
               _('Version'), theme_info['version'], theme_info['info'])

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
   _browser.page_add('config://modules/', _('Modules'), None, _modules_populate)

def _modules_populate(browser, url):
   for mod in sorted(modules.list_get(), key=attrgetter('name')):
      browser.item_add(ModulesItemClass(), mod.name, mod)

##############  SUBTITLES  ####################################################

subs_encs = ['UTF-8','latin_1','iso8859_2','iso8859_3','iso8859_4','iso8859_5',
'iso8859_6','iso8859_7','iso8859_8','iso8859_9','iso8859_10','iso8859_13',
'iso8859_14','iso8859_15','iso8859_16']

def _subtitles_list():
   _browser.page_add('config://subtitles/', _('Subtitles'), None, _subtitles_populate)

def _subtitles_populate(browser, url):
   standard_item_lang_add('subtitles', 'langs', _('Subtitles preferred languages'), multi=True)
   standard_item_string_from_list_add('subtitles', 'encoding', _('Subtitles encoding'), subs_encs)
   standard_item_bool_add('subtitles', 'always_try_utf8', _('Always try UTF-8 first'))
   standard_item_string_add('subtitles', 'opensubtitles_user', _('Opensubtitles.org Username'))
   standard_item_string_add('subtitles', 'opensubtitles_pass', _('Opensubtitles.org Password'), pwd=True)


##############  SYS INFO  #####################################################

def _sys_info():
   from epymc.gui import _theme_generation
   from epymc import __version__ as emc_version
   try:
      from efl import __version__ as efl_version
   except:
      efl_version = _('Unknown')
   
   downl_avail = ecore.file_download_protocol_available('http://')
   win_w, win_h = gui.win.size
   scr_x, scr_y, scr_w, scr_h = gui.win.screen_size
   dpi_x, dpi_y = gui.win.screen_dpi
   text = '<title>%s</><br>' \
          '<name>%s:</name> %s<br>' \
          '<name>%s:</name> %s - %s<br>' \
          '<name>%s:</> %dx%d <name>%s:</> %dx%d+%d+%d <name>%s:</> %d %d<br>' \
          '<br><title>%s</><br>' \
          '<name>%s:</name> %s<br>' \
          '<name>%s:</name> %s<br>' \
          '<br><title>%s</><br>' \
          '<name>%s:</name> %s <name> %s:</name> %s<br>' \
          '<name>%s:</name> %s<br>' \
          '<name>%s:</name> %s<br>' % (
            _('Core'),
            _('Download available'), _('yes') if downl_avail else _('no'),
            _('Theme'), ini.get('general', 'theme'), gui.theme_file,
            _('Window size'), win_w, win_h,
            _('screen'), scr_w, scr_h, scr_x, scr_y,
            _('dpi'), dpi_x, dpi_y,
            _('Paths'),
            _('Base folder'), utils.emc_base_dir,
            _('Config folder'), utils.user_conf_dir,
            _('Versions'),
            _('EpyMC'), emc_version, _('EpyMC themes API'), _theme_generation,
            _('Python'), sys.version,
            _('Python-EFL'), efl_version,
          )
   EmcDialog(style='panel', title=_('System info'), text=text)

