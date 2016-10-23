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
from lxml import etree
from operator import attrgetter

from efl import ecore

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.utils as utils
import epymc.gui as gui
# import epymc.ini as ini
# import epymc.config_gui as cgui

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.gui import EmcDialog


def DBG(msg):
   print('KODI ADDONS: %s' % msg)
   pass




_mod = None



class KodiAddon(object):

   def __init__(self, path):
      print("\n##### ADDON FROM: %s  #####" % path)
      self._path = path
      self._xml_tree = etree.parse(os.path.join(path, 'addon.xml')) # TODO check errors

      # fetch basic info from the xml file
      addon = self._xml_tree.getroot()
      self._id = addon.get('id')
      self._name = addon.get('name')
      self._version = addon.get('version')
      self._author = addon.get('provider-name')

      for extension in addon.findall('extension'):
         if extension.get('point') == 'xbmc.python.pluginsource':
            self._main_exe = extension.get('library')
            self._provides = extension.findtext('provides')

   def __str__(self):
      return '<KodiAddon {0.id} v={0.version} main={0._main_exe}>'.format(self)

   def __repr__(self):
      return 'KodiAddon("{}")'.format(self._path)

   @property
   def id(self):
      """ex: "plugin.video.southpark_unofficial" """
      return self._id

   @property
   def name(self):
      """ ex: "South Park" """
      return self._name

   @property
   def author(self):
      """ ex: "Deroad" """
      return self._author

   @property
   def version(self):
      """ ex: "0.4.3" """
      return self._version

   @property
   def path(self):
      """ full path of the installed addon """
      return self._path

   @property
   def main_exe(self):
      """ main executable script (full_path) """
      return os.path.join(self._path, self._main_exe)

   @property
   def root_url(self):
      """ ex: "plugin://plugin.video.southpark_unofficial/" """
      return 'plugin://{}/'.format(self.id)

   @property
   def provides(self):
      """ ['video', 'audio', 'image', 'executable'] """
      return self._provides.split()

   def main_item_add(self, browser):
      """ Add the addon main item to the given browser """
      self._browser = browser
      self._browser.item_add(AddonItemClass(), None, self)

   ### Utils
   def best_poster_for_listitem(self, listitem):
      if not listitem:
         return None
      try:
         return listitem['art']['thumb']
      except KeyError:
         return listitem.get('thumbnailImage')

   ### Addon runner
   def request_page(self, url=None):

      if url is None:
         url = self.root_url

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


class AddonItemClass(EmcItemClass):
   def item_selected(self, url, addon):
      print('item_selected', url)
      addon.request_page(None)

   def label_get(self, url, addon):
      return addon.name.replace('&', '&amp;')


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
      return 'icon/folder' # TODO listitem iconImage or thumbnailImage

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

class KodiAddonsModule(EmcModule):
   name = 'kodi_addons'
   label = _('Kodi Addons')
   icon = 'icon/evas'
   info = _('Use Kodi addons in epymc.')

   _browser = None
   _styles = ('List',)
   _addons = []


   def __init__(self):
      global _mod
      
      DBG('Init module')

      _mod = self

      # create ini options if not exists (with defaults)
      # ini.add_section('videochannels')
      # ini.get('videochannels', 'autoupdate_ytdl', 'True')


      # add an item in the mainmenu
      mainmenu.item_add(self.name, 15, self.label, self.icon, self.mainmenu_cb)

      # create the browser instance
      self._browser = EmcBrowser(self.label, icon=self.icon)

   def __shutdown__(self):
      DBG('Shutdown module')
      mainmenu.item_del('videochannels')
      self._browser.delete()


   def mainmenu_cb(self):

      # TODO create folders in .config/epymc/kodi (or in __init__)

      if not self._addons:
         folder = os.path.join(utils.user_conf_dir, 'kodi', 'addons')
         for fname in os.listdir(folder):
            path = os.path.join(folder, fname)
            a = KodiAddon(path)
            # TODO check err
            self._addons.append(a)
            print(a)

      self._browser.page_add('kodi_addons://root', self.label, self._styles,
                             self.populate_root_page)
      self._browser.show()
      mainmenu.hide()

   def populate_root_page(self, browser, url):
      for addon in sorted(self._addons, key=attrgetter('name')):
         # self._browser.item_add(AddonItemClass(), None, addon)
         addon.main_item_add(browser)

   
      # self.current_addon = KodiAddon()
      
      # if not self._sources:
         # self.build_sources_list()
      # for ch in self._sources:
         # self._browser.item_add(ChannelItemClass(), ch['name'], ch)
      # self._browser.item_add(DownloadItemClass(), None)




      
