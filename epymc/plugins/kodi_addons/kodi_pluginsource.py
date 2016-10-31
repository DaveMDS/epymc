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

# Todo:
#  - Playlist (southpark)

from __future__ import absolute_import, print_function

import os
import ast

from efl import ecore

import epymc.mediaplayer as mediaplayer
from epymc.browser import EmcItemClass
from epymc.gui import EmcDialog, EmcWaitDialog

from .kodi_addon_base import KodiAddonBase, get_installed_addon
from .kodi_pythonmodule import KodiPythonModule


def DBG(*args):
   print('KODI SOURCE:', *args)
   pass


xbmclib_path = os.path.join(os.path.dirname(__file__), 'xbmclib')


def return_to_addon(meth):
   """ Decorator for proxied functions that return a value back to the addon """
   def func_wrapper(self, *args, **kargs):
      ret = meth(self, *args, **kargs)
      self._exe.send('{}\n'.format(ret))
   return func_wrapper


### listitem utils ############################################################
""" listitem reference:
{
   url: ''             # those 2 are added by emc in _addDirectoryItem
   isFolder: bool      #

   path: ''
   label: ''
   label2: ''

   art: {
      icon: ''
      thumb: ''
      poster: ''
      banner: ''
      fanart: ''
      clearart: ''
      clearlogo: ''
      landscape: ''
      ... and any other key name
   }

   infoLabels: {
      # All types:
      count: integer (12) - can be used to store an id for later, or for sorting purposes
      size: long (1024) - size in bytes
      date: string (d.m.Y / 01.01.2009) - file date

      # Video values:
      genre: string (Comedy)
      year: integer (2009)
      episode: integer (4)
      season: integer (1)
      top250: integer (192)
      tracknumber: integer (3)
      rating: float (6.4) - range is 0..10
      userrating: integer (9) - range is 1..10
      watched: depreciated - use playcount instead
      playcount: integer (2) - number of times this item has been played
      overlay: integer (2) - range is 0..8. See GUIListItem.h for values
      cast: list (["Michal C. Hall","Jennifer Carpenter"]) - if provided a list of tuples cast will be interpreted as castandrole
      castandrole: list of tuples ([("Michael C. Hall","Dexter"),("Jennifer Carpenter","Debra")])
      director: string (Dagur Kari)
      mpaa: string (PG-13)
      plot: string (Long Description)
      plotoutline: string (Short Description)
      title: string (Big Fan)
      originaltitle: string (Big Fan)
      sorttitle: string (Big Fan)
      duration: integer (245) - duration in seconds
      studio: string (Warner Bros.)
      tagline: string (An awesome movie) - short description of movie
      writer: string (Robert D. Siegel)
      tvshowtitle: string (Heroes)
      premiered: string (2005-03-04)
      status: string (Continuing) - status of a TVshow
      code: string (tt0110293) - IMDb code
      aired: string (2008-12-07)
      credits: string (Andy Kaufman) - writing credits
      lastplayed: string (Y-m-d h:m:s = 2009-04-05 23:16:04)
      album: string (The Joshua Tree)
      artist: list (['U2'])
      votes: string (12345 votes)
      trailer: string (/home/user/trailer.avi)
      dateadded: string (Y-m-d h:m:s = 2009-04-05 23:16:04)
      mediatype: string - "video", "movie", "tvshow", "season", "episode" or "musicvideo"

      # Music values:
      tracknumber: integer (8)
      discnumber: integer (2)
      duration: integer (245) - duration in seconds
      year: integer (1998)
      genre: string (Rock)
      album: string (Pulse)
      artist: string (Muse)
      title: string (American Pie)
      rating: string (3) - single character between 0 and 5
      lyrics: string (On a dark desert highway...)
      playcount: integer (2) - number of times this item has been played
      lastplayed: string (Y-m-d h:m:s = 2009-04-05 23:16:04)

      # Picture values:
      title: string (In the last summer-1)
      picturepath: string (/home/username/pictures/img001.jpg)
      exif: string (See CPictureInfoTag::TranslateString in PictureInfoTag.cpp for valid strings) 
   }

   properties: { # Always lowercase, here use camel only for readability
      AspectRatio: '1.85 : 1'
      StartOffset: '256.4'
      fanart_image: ''       # only see in SouthPark addon :/
   }

   streamInfo: {
      ...
   }
}
"""

def listitem_best_label(listitem):
   if listitem:
      return listitem.get('label') or listitem['infoLabels'].get('title')

def listitem_best_icon(listitem):
   if listitem:
      if listitem['isFolder']:
         return 'icon/folder'
      else:
         return 'icon/play'
      # TODO search in art

def listitem_best_poster(listitem):
   if listitem:
      return listitem['art'].get('thumb')

def listitem_best_fanart(listitem):
   if listitem:
      return listitem['art'].get('fanart')

def listitem_best_info(listitem):
   if listitem:
      return listitem['infoLabels'].get('plot', '').replace('&', '&amp;')
      # TODO show all available infoLabels

def listitem_play(listitem, media_url=None):
   if listitem:
      url = media_url or listitem.get('url') or listitem.get('path')
      title = listitem_best_label(listitem)
      poster = listitem_best_poster(listitem)

      mediaplayer.play_url(url)
      mediaplayer.title_set(title)
      mediaplayer.poster_set(poster)


class StandardItemClass(EmcItemClass):
   def item_selected(self, url, item_data):
      addon, listitem = item_data
      addon._item_selected_cb(url, listitem)

   def label_get(self, url, item_data):
      addon, listitem = item_data
      return listitem_best_label(listitem).replace('&', '&amp;')

   def icon_get(self, url, item_data):
      addon, listitem = item_data
      return listitem_best_icon(listitem)

   def poster_get(self, url, item_data):
      addon, listitem = item_data
      return listitem_best_poster(listitem)

   def fanart_get(self, url, item_data):
      addon, listitem = item_data
      return listitem_best_fanart(listitem) or addon.fanart

   def info_get(self, url, item_data):
      addon, listitem = item_data
      import pprint  # usefull for debug
      pprint.pprint(listitem)
      return listitem_best_info(listitem)


class KodiPluginSource(KodiAddonBase):

   extension_point = ".//extension[@point='xbmc.python.pluginsource']"

   def __init__(self, *args):
      KodiAddonBase.__init__(self, *args)
      self._run_dialog = None
      self._run_dialog_timer = None
      self._selected_listitem = None

      ext = self._root.find(self.extension_point)
      self._main_exe = ext.get('library')
      for elem in ext:
         if elem.tag == 'provides':
            self._provides = elem.text

   @property
   def main_exe(self):
      """ main executable script (full_path) """
      return os.path.join(self.path, self._main_exe)

   @property
   def root_url(self):
      """ ex: "plugin://plugin.video.southpark_unofficial/" """
      return 'plugin://{}/'.format(self.id)

   @property
   def provides(self):
      """ ['video', 'audio', 'image', 'executable'] """
      return self._provides.split()


   ###  Addon runner  ##########################################################
   def show_run_dialog(self):
      if self._run_dialog_timer is not None:
         self._run_dialog_timer.delete()
         self._run_dialog_timer = None
      self._run_dialog = EmcWaitDialog(_('Getting info...'), self._cmd_canc_cb)

   def hide_run_dialog(self):
      if self._run_dialog_timer is not None:
         self._run_dialog_timer.delete()
         self._run_dialog_timer = None
      if self._run_dialog is not None:
         self._run_dialog.delete()
         self._run_dialog = None

   def _item_selected_cb(self, url, listitem):
      self._selected_listitem = listitem

      # addons can request pages from another addons!
      addon = self
      if url.startswith('plugin://'):
         addon_id = url[9:url.index('/', 10)]
         if addon_id != self.id:
            addon = get_installed_addon(addon_id)

      if listitem.get('isFolder') or url.startswith('plugin://'):
         addon.request_page(url)
      else:
         listitem_play(listitem)

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
                    os.path.join(self.path, 'lib'),
                    os.path.join(self.path, 'resources', 'lib')]
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
      self._stderr_lines = []
      self._page_items = []
      self._page_url = url

      self._exe = ecore.Exe(cmd, ecore.ECORE_EXE_PIPE_READ |
                                 ecore.ECORE_EXE_PIPE_READ_LINE_BUFFERED |
                                 ecore.ECORE_EXE_PIPE_ERROR |
                                 ecore.ECORE_EXE_PIPE_ERROR_LINE_BUFFERED |
                                 ecore.ECORE_EXE_PIPE_WRITE |
                                 ecore.ECORE_EXE_TERM_WITH_PARENT)
      self._exe.on_data_event_add(self._addon_stdout_cb)
      self._exe.on_error_event_add(self._addon_stderr_cb)
      self._exe.on_del_event_add(self._addon_complete_cb)

      DBG('RUNNING CMD:', cmd)
      self._run_dialog_timer = ecore.Timer(0.5, lambda: self.show_run_dialog())

   def _cmd_canc_cb(self):
      self._exe.delete()

   def _addon_stdout_cb(self, exe, event):
      """ Lines from addon stdout use this protocol:

      func_name {args: (...), kargs: {...}}\n

      Func is resolved to a method of this class and called with args and kargs
      Function from xbmclib is prefixed with a _ (ex: _addDirectoryItem)
      while methods become: _Class_method (ex: _Player_play)
      """
      for line in event.lines:
         # print('LINE: "{}"'.format(line))
         try:
            func_name, args_and_kargs = line.split(' ', 1)
            method = getattr(self, func_name)
         except (AttributeError, ValueError):
            DBG("-->", line)
         else:
            args_and_kargs = ast.literal_eval(args_and_kargs)
            method(*args_and_kargs['args'], **args_and_kargs['kargs'])

   def _addon_stderr_cb(self, exe, event):
      self._stderr_lines += event.lines

   def _addon_complete_cb(self, exe, event):
      self.hide_run_dialog()
      if event.exit_code != 0:
         txt = '<small>{}</small>'.format('<br>'.join(self._stderr_lines))
         EmcDialog(style='error', text=txt)
         DBG('\n'.join(self._stderr_lines)) # TODO remove me?
      else:
         DBG("OK, DONE")
         self._page_items = None
         self._page_url = None

   def _populate_requested_page(self, browser, page_url, items):
      self.hide_run_dialog()
      for listitem in items:
         self._browser.item_add(StandardItemClass(), listitem['url'], (self, listitem))

   ###  xbmclib.xbmc proxied functions  ########################################
   @return_to_addon
   def _getInfoLabel(self, infotag):
      """ http://kodi.wiki/view/InfoLabels """
      ctx, key = infotag.split('.', 1)
      val = None

      if ctx == 'ListItem':
         listitem = self._selected_listitem
         val = listitem['infoLabels'].get(key.lower())

      # TODO implement more context

      if val is None:
         DBG('ERROR: cannot resolve InfoLabel: {}'.format(infotag))

      return val or 'Unknown'

   def _Player_play(self, player_id, item=None, listitem=None, windowed=False, startpos=-1):
      self.hide_run_dialog()
      listitem_play(listitem, item)

   ###  xbmclib.addon proxied functions  #######################################
   @return_to_addon
   def _Addon_getAddonInfo(self, addon_id, id):
      addon = get_installed_addon(addon_id)
      if addon is None:
         return None

      # TODO not supported ids: type, profile, stars
      try:
         val = getattr(addon, id)
      except AttributeError:
         DBG('Unknown AddonInfo id:', id)
      else:
         return val

   @return_to_addon
   def _Addon_getSetting(self, addon_id, id):
      addon = get_installed_addon(addon_id)
      val = addon.settings.get(id)
      DBG("GET SETTING:", id, " val:", val)
      return val # TODO not sure if need to return None or '' for unknown id 

   def _Addon_setSetting(self, addon_id, id, value):
      addon = get_installed_addon(addon_id)
      DBG("SET SETTING:", id, " val:", value)
      addon.settings[id] = value
      addon.settings_save() # TODO really save at every set ?

   ###  xbmclib.gui proxied functions  #########################################
   
   ###  xbmclib.xbmcplugin proxied functions  ##################################
   def _addDirectoryItem(self, handle, url, listitem, isFolder=False, totalItems=1):
      listitem['url'] = url
      listitem['isFolder'] = isFolder
      self._page_items.append(listitem)

   def _endOfDirectory(self, handle, succeeded=True, updateListing=False, cacheToDisc=True):
      self.hide_run_dialog()
      if succeeded == True:
         self._browser.page_add(self._page_url, 'page label', None, # TODO item styles
                                 self._populate_requested_page, items=self._page_items)
         self._page_items = None
      else:
         pass # TODO ALERT

   def _setResolvedUrl(self, succeeded, listitem):
      self.hide_run_dialog()
      if succeeded:
         listitem_play(listitem)
      else:
         EmcDialog(style='error', text='Addon error') # TODO better dialog



