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

# Kodi references:
#  http://kodi.wiki/view/Python_development
#  http://mirrors.kodi.tv/docs/python-docs/16.x-jarvis/xbmc.html


# Require:
#  python2-polib

from __future__ import absolute_import, print_function

import os
import sys
import ast
import locale
from lxml import etree
from operator import attrgetter

from efl import ecore
from efl.elementary import utf8_to_markup

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.utils as utils
import epymc.gui as gui
from epymc.browser import EmcBrowser, EmcItemClass


from .kodi_addon import KodiAddonBase
from .kodi_module import KodiModule


def DBG(*args):
   print('KODI ADDON:', *args)
   pass



def load_available_addons():
   L = []
   folder = os.path.join(utils.user_conf_dir, 'kodi', 'addons')
   for fname in os.listdir(folder):
      path = os.path.join(folder, fname, 'addon.xml')
      try:
         a = KodiAddon(path)
      except: # TODO somethign better....
         a = KodiModule(path) 
      print(a)
      # TODO check err
      L.append(a)
   return L


class StandardItemClass(EmcItemClass):
   def item_selected(self, url, item_data):
      addon, listitem = item_data
      # _mod.run_addon(url=listitem['url'])
      addon.request_page(url)

   def label_get(self, url, item_data):
      addon, listitem = item_data
      return listitem['label'].replace('&', '&amp;')

   def icon_get(self, url, item_data):
      addon, listitem = item_data
      if listitem.get('isFolder') == True:
         return 'icon/folder'
      # TODO listitem iconImage or thumbnailImage

   def poster_get(self, url, item_data):
      addon, listitem = item_data
      return addon.best_poster_for_listitem(listitem)

   # def fanart_get(self, url, channel):
      # return _mod._current_src['backdrop']

   def info_get(self, url, item_data):
      addon, listitem = item_data
      try:
         return listitem['infoLabels']['plot'].replace('&', '&amp;')
      except KeyError:
         return None


class KodiAddon(KodiAddonBase):

   # _main_exe = None # ?????????????????????????
   extension_point = ".//extension[@point='xbmc.python.pluginsource']"

   # def __init__(self, path=None, xml_element=None, repo=None):
   def __init__(self, xml_info, repository=None):
      KodiAddonBase.__init__(self, xml_info, repository)

      ext = self._root.find(self.extension_point)
      self._main_exe = ext.get('library')
      for elem in ext.iterchildren():
         if elem.tag == 'provides':
            self._provides = elem.text

   @property
   def main_exe(self):
      """ main executable script (full_path) """
      return os.path.join(self.installed_path, self._main_exe)

   @property
   def root_url(self):
      """ ex: "plugin://plugin.video.southpark_unofficial/" """
      return 'plugin://{}/'.format(self.id)

   @property
   def provides(self):
      """ ['video', 'audio', 'image', 'executable'] """
      return self._provides.split()


   ### Utils
   def best_poster_for_listitem(self, listitem):
      if not listitem:
         return None
      try:
         return listitem['art']['thumb']
      except KeyError:
         return listitem.get('thumbnailImage')

   ### Addon runner
   def request_page(self, url=None, browser=None):

      if url is None:
         url = self.root_url
      if browser is not None:
         self._browser = browser

      DBG('running: "{}" with url: "{}"'.format(self.name, url))
      
      libpath = '/home/dave/github/davemds/epymc/epymc/plugins/kodi_addons/xbmclib/'
      # TODO FIX env !!!

      idx = url.find('?')
      if idx != -1:
         arg1 = url[:idx]
         arg3 = url[idx:]
      else:
         arg1 = url
         arg3 = ''

      cmd = 'env PYTHONPATH={} python2 "{}" "{}" "{}" "{}"'.format(
             libpath, self.main_exe, arg1, '123456', arg3)
      print('CMD:', cmd)
      self._stderr_lines = []
      self._page_items = []
      self._page_url = url
      
      exe = ecore.Exe(cmd, ecore.ECORE_EXE_PIPE_READ |
                           ecore.ECORE_EXE_PIPE_READ_LINE_BUFFERED |
                           ecore.ECORE_EXE_PIPE_ERROR |
                           ecore.ECORE_EXE_PIPE_ERROR_LINE_BUFFERED |
                           ecore.ECORE_EXE_TERM_WITH_PARENT)
      exe.on_data_event_add(self._addon_stdout_cb)
      exe.on_error_event_add(self._addon_stderr_cb)
      exe.on_del_event_add(self._addon_complete_cb)

   def _addon_stdout_cb(self, exe, event):
      # self._stdout_lines += event.lines
      for line in event.lines:
         # print('LINE: "{}"'.format(line))
         try:
            action, params = line.split(' ', 1)
            method = getattr(self, '_' + action)
         except (AttributeError, ValueError):
            print("---", line)
         else:
            method(**ast.literal_eval(params))
         # TODO error check

   def _addon_stderr_cb(self, exe, event):
      self._stderr_lines += event.lines

   def _addon_complete_cb(self, exe, event):
      if event.exit_code != 0:
         txt = '<small>{}</small>'.format('<br>'.join(self._stderr_lines))
         EmcDialog(style='error', text=txt)
         DBG('\n'.join(self._stderr_lines)) # TODO remove me?
      else:
         print("OK, DONE")
         self._page_items = None
         self._page_url = None

   def _populate_requested_page(self, browser, page_url, items):
      print("pop", page_url)
      for listitem in items:
         self._browser.item_add(StandardItemClass(), listitem['url'], (self, listitem))


   ### Addons proxied functions
   def _addDirectoryItem(self, handle, url, listitem, isFolder=False, totalItems=1):
      listitem['url'] = url
      listitem['isFolder'] = isFolder
      self._page_items.append(listitem)
      print(listitem)

   def _Player_play(self, item=None, listitem=None, windowed=False, startpos=-1):
      if item:
         try:
            title = listitem['infoLabels']['Title']
         except KeyError:
            title = ''
         
         poster = self.best_poster_for_listitem(listitem)
         mediaplayer.play_url(item)
         mediaplayer.title_set(title)
         mediaplayer.poster_set(poster)
         print("URL", item)

   def _endOfDirectory(self, succeeded=True, updateListing=False, cacheToDisc=True):
      if succeeded == True:
         self._browser.page_add(self._page_url, 'page label', None, # TODO item styles
                                 self._populate_requested_page, items=self._page_items)
         self._page_items = None
      else:
         pass # TODO ALERT
