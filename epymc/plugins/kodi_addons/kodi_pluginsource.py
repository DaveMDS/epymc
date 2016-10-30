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
import ast

from efl import ecore

import epymc.mediaplayer as mediaplayer
from epymc.browser import EmcItemClass
from epymc.gui import EmcDialog

from .kodi_addon_base import KodiAddonBase, get_installed_addon
from .kodi_pythonmodule import KodiPythonModule


def DBG(*args):
   print('KODI SOURCE:', *args)
   pass


xbmclib_path = os.path.join(os.path.dirname(__file__), 'xbmclib')


class StandardItemClass(EmcItemClass):
   def item_selected(self, url, item_data):
      addon, listitem = item_data
      if listitem.get('isFolder', False):
         addon.request_page(url)
      else:
         addon.play_listitem(listitem)

   def label_get(self, url, item_data):
      addon, listitem = item_data
      return listitem['label'].replace('&', '&amp;')

   def icon_get(self, url, item_data):
      addon, listitem = item_data
      if listitem.get('isFolder') == True:
         return 'icon/folder'
      else:
         return 'icon/play'
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


class KodiPluginSource(KodiAddonBase):

   extension_point = ".//extension[@point='xbmc.python.pluginsource']"

   def __init__(self, *args):
      KodiAddonBase.__init__(self, *args)

      ext = self._root.find(self.extension_point)
      self._main_exe = ext.get('library')
      for elem in ext:
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

   def best_label_for_listitem(self, listitem):
      title = listitem.get('label')
      if not title:
         try:
            title = listitem['infoLabels']['Title']
         except KeyError:
            title = ''
      return title

   def play_listitem(self, listitem, media_url=None):
         url = media_url or listitem.get('url') or listitem.get('path')
         title = self.best_label_for_listitem(listitem)
         poster = self.best_poster_for_listitem(listitem)

         mediaplayer.play_url(url)
         mediaplayer.title_set(title)
         mediaplayer.poster_set(poster)

   ### Addon runner
   def request_page(self, url=None, browser=None):

      if url is None:
         url = self.root_url
      if browser is not None:
         self._browser = browser

      DBG('running: "{}" with url: "{}"'.format(self.name, url))

      # 3 "well-know" arguments for the plugin
      idx = url.find('?')
      arg1 = url[:idx] if idx != -1 else url
      arg3 = url[idx:] if idx != -1 else ''
      arg2 = '123456'

      # augmented with: our xbmclib, addon lib folders, all plugin requirements
      PYTHONPATH = [xbmclib_path,
                    os.path.join(self.installed_path, 'lib'),
                    os.path.join(self.installed_path, 'resources', 'lib')]
      for require_id, min_version in self.requires:
         mod = get_installed_addon(require_id)
         if mod is None:
            EmcDialog(style='error', text='Missing dep') # TODO better dialog
            return

         if mod.check_version(min_version) is False:
            EmcDialog(style='error', text='Dep too old') # TODO better dialog
            return

         if type(mod) == KodiPythonModule:
            PYTHONPATH.append(mod.main_import)

      # build (and run) the plugin command line
      cmd = 'env PYTHONPATH="{}" python2 "{}" "{}" "{}" "{}"'.format(
             ':'.join(PYTHONPATH), self.main_exe, arg1, arg2, arg3)
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
         DBG("OK, DONE")
         self._page_items = None
         self._page_url = None

   def _populate_requested_page(self, browser, page_url, items):
      for listitem in items:
         self._browser.item_add(StandardItemClass(), listitem['url'], (self, listitem))


   ### Addons proxied functions
   def _addDirectoryItem(self, handle, url, listitem, isFolder=False, totalItems=1):
      listitem['url'] = url
      listitem['isFolder'] = isFolder
      self._page_items.append(listitem)

   def _Player_play(self, item=None, listitem=None, windowed=False, startpos=-1):
      self.play_listitem(listitem, item)

   def _endOfDirectory(self, succeeded=True, updateListing=False, cacheToDisc=True):
      if succeeded == True:
         self._browser.page_add(self._page_url, 'page label', None, # TODO item styles
                                 self._populate_requested_page, items=self._page_items)
         self._page_items = None
      else:
         pass # TODO ALERT

   def _setResolvedUrl(self, succeeded, listitem):
      if succeeded:
         self.play_listitem(listitem)
      else:
         EmcDialog(style='error', text='Addon error') # TODO better dialog
