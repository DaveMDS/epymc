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
import ast
try:
   import configparser as ConfigParser
except:
   import ConfigParser

from efl import evas, elementary

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.utils import EmcExec, download_url_async
from epymc.gui import EmcDialog, EmcVKeyboard

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.utils as utils
import epymc.gui as gui
import epymc.ini as ini
import epymc.events as events

from epymc.extapi.onlinevideo import ACT_DEFAULT, ACT_NONE, ACT_FOLDER, \
   ACT_MORE, ACT_PLAY, ACT_SEARCH, ydl_executable


def DBG(msg):
   print('ONLINEVID: %s' % msg)
   pass


F_STATE = 0
F_LABEL = 1
F_URL = 2
F_INFO = 3
F_ICON = 4
F_POSTER = 5
F_ACTION = 6


_mod = None


class ChannelItemClass(EmcItemClass):
   def item_selected(self, url, channel):
      _mod._current_src = channel
      _mod._request_index()

   def label_get(self, url, channel):
      return channel['label']

   def icon_get(self, url, channel):
      return channel['icon']

   def poster_get(self, url, channel):
      return channel['poster']

   def fanart_get(self, url, channel):
      return channel['backdrop']

   def info_get(self, url, channel):
      return '<title>%s</><br><name>%s:</> %s<br><name>%s:</> %s<br>%s' % (
               channel['label'], _('Version'), channel['version'],
               _('Author'), channel['author'], channel['info'])


class StandardItemClass(EmcItemClass):
   def item_selected(self, url, item_data):
      _mod._request_page(item_data)

   def label_get(self, url, item_data):
      return item_data[F_LABEL].replace('&', '&amp;')

   def icon_get(self, url, item_data):
      if not item_data[F_ICON] and item_data[F_ACTION] == ACT_FOLDER:
            return 'icon/folder'
      return item_data[F_ICON]
   
   def poster_get(self, url, item_data):
      return item_data[F_POSTER] or _mod._current_src['poster']

   def info_get(self, url, item_data):
      if item_data[F_INFO]:
         return item_data[F_INFO].replace('&', '&amp;')


class OnlinevideoModule(EmcModule):
   name = 'onlinevideo'
   label = _('Online Channels')
   icon = 'icon/olvideo'
   info = _('Browse, watch and download videos from your favorite online sources.')

   _browser = None
   _sources = []
   _current_src = None
   _run_dialog = None
   _py = sys.executable or ''

   _search_folders = [
      os.path.dirname(__file__),
      os.path.join(utils.user_conf_dir, 'channels')
      # TODO add a system dir....but where?
      ]

   def __init__(self):
      global _mod
      
      DBG('Init module')

      _mod = self

      # add an item in the mainmenu
      mainmenu.item_add('onlinechannels', 15, _('Online Channels'),
                        'icon/olvideo', self.cb_mainmenu)

      # create the browser instance
      self._browser = EmcBrowser(_('Online Channels'))

   def __shutdown__(self):
      DBG('Shutdown module')
      mainmenu.item_del('onlinechannels')
      self._browser.delete()

   def parse_source_ini_file(self, path):
      section = 'EmcChannelV3'
      options = ['name','label','info','icon','poster','banner',
                 'backdrop', 'mature', 'version', 'exec', 'author']
      source = {}
      parser = ConfigParser.ConfigParser()
      parser.read(path)

      if parser.has_section(section):
         # check required options
         for opt in options:
            if not parser.has_option(section, opt):
               del parser
               return None

         # check mature
         if ini.get_bool('general', 'show_mature_contents') != True and \
            parser.get(section, 'mature').lower() == 'yes':
            del parser
            return None

         # populate channel dict
         for opt in options:
            source[opt] = parser.get(section, opt)
         dirname = os.path.dirname(path)
         for opt in ['exec', 'icon', 'poster', 'banner', 'backdrop']:
            source[opt] = os.path.join(dirname, source[opt])
      del parser
      return source

   def cb_mainmenu(self):
      self._browser.page_add('olvid://root', _('Channels'), None,
                             self.populate_root_page)
      self._browser.show()
      mainmenu.hide()
      self.youtubedl_check_update()

   def populate_root_page(self, browser, url):
      if not self._sources:
         self.build_sources_list()
      for ch in self._sources:
         self._browser.item_add(ChannelItemClass(), ch['name'], ch)

###### YOUTUBE-DL DOWNLOAD AND UPDATE
   def youtubedl_check_update(self):
      ydl = ydl_executable()
      if not os.path.exists(ydl):
         self._ydl_download_latest()
      else:
         EmcExec(ydl + ' --version', True, self._ydo_local_version_done)

   def _ydl_download_latest(self):
      dia = EmcDialog(title=_('please wait'), style='progress',
                      text=_('Updating the helper program <b>youtube-dl</b> to the latest version.<br><br>For info please visit:<br>rg3.github.io/youtube-dl/'))
      download_url_async('http://youtube-dl.org/latest/youtube-dl',
                         dest=ydl_executable(),
                         complete_cb=self._ydl_complete_cb,
                         progress_cb=self._ydl_progress_cb,
                         dia=dia)
      
   def _ydl_progress_cb(self, dest, dltotal, dlnow, dia):
      dia.progress_set((float(dlnow) / dltotal) if dltotal > 0 else 0)

   def _ydl_complete_cb(self, dest, status, dia):
      os.chmod(dest, 484) # 0o0744 (make it executable)
      dia.delete()

   def _ydo_local_version_done(self, version):
      if version:
         download_url_async('http://youtube-dl.org/latest/version',
                            complete_cb=self._ydo_remote_version_done,
                            version=version.strip())

   def _ydo_remote_version_done(self, dest, status, version):
      if status == 200:
         with open(dest) as f:
            available = f.read().strip()
         os.remove(dest)
         if available != version:
            self._ydl_download_latest()
         else:
            DBG('youtube-dl is up-to-date (%s)' % version)

   
###### SOURCES STUFF
   def build_sources_list(self):
      # search all the source.ini files in all the subdirs of _search_folders
      for folder in self._search_folders:
         for top, dirs, files in os.walk(folder):
            for f in files:
               if f == 'channel.ini':
                  source = self.parse_source_ini_file(os.path.join(top, f))
                  if source:
                     self._sources.append(source)

   def get_source_by_name(self, src_name):
      for s in self._sources:
         if s['name'] == src_name:
            return s

   def _request_index(self):
      # request the index page from the channel
      src = self._current_src
      item_data = (0, src['label'], 'index', None, None, None, ACT_DEFAULT)
      self._request_page(item_data)

   def _request_page(self, item_data):
      # request a specific page from the channel
      (next_state, label, url, info, icon, poster, action) = item_data
      if action == ACT_PLAY:
         mediaplayer.play_url(url)
         mediaplayer.title_set(label)
         mediaplayer.poster_set(poster)
      elif action == ACT_SEARCH:
         EmcVKeyboard(title=_('Search query'), user_data=item_data,
                      accept_cb=self._search_vkeyb_done)
      elif action != ACT_NONE:
         src = self._current_src
         cmd = '%s %s %d "%s"' % (self._py, src['exec'], next_state, url)
         DBG('Executing: ' + cmd)
         EmcExec(cmd, True, self._request_page_done, item_data)
         self._run_dialog = EmcDialog(title=_('please wait'), style='cancel',
                                      text=_('Getting info...'), )

   def _search_vkeyb_done(self, vkeyb, text, item_data):
      (next_state, label, url, info, icon, poster, action) = item_data
      src = self._current_src
      cmd = '%s %s %d "%s"' % (self._py, src['exec'], next_state, text)
      DBG('ExecutingSearch: ' + cmd)
      EmcExec(cmd, True, self._request_page_done, item_data)
      self._run_dialog = EmcDialog(title=_('please wait'), style='cancel',
                                   text=_('Getting info...'), )

   def _request_page_done(self, output, parent_item_data):
      # parse the output of the channel execution
      self._run_dialog.delete()
      lines = output.split('\n')
      items = []
      suggested = None
      for line in lines:
         DBG(' ---' + line)
         if line.startswith('PLAY!'):
            DBG('yes sir..' + line)
            url = line[5:]
            mediaplayer.play_url(url)
            mediaplayer.poster_set(parent_item_data[F_POSTER]) # TODO FIXME
            mediaplayer.title_set(parent_item_data[F_LABEL])
            suggested = [] # from now on every item is a suggestion
         elif line.startswith('ERR!'):
            text = '%s:<br><failure>%s</>' % (_('Reported error'), line[4:])
            EmcDialog(title=_('Error reading channel'), style='error', text=text)
            return
         else:
            try:
               # WARNING keep item_data consistent !
               (next_state, label, url, info, icon, poster, action) = \
                     ast.literal_eval(line)
               if icon is None:
                  if action == ACT_SEARCH: icon = 'icon/search'
                  if action == ACT_MORE: icon = 'icon/next'
               if info is not None:
                  info = info.replace('\n', '<br>')
               item_data = (next_state, label, url, info, icon, poster, action)
               if suggested is not None:
                  suggested.append(item_data)
               else:
                  items.append(item_data)
               # DBG(str(item_data))
            except:
               continue
      
      if len(items) < 1 and suggested is None:
         EmcDialog(title=_('Error reading channel'), style='error',
                   text=_('No items returned'))
         return

      if suggested and len(suggested) > 0:
         # prepare the suggestions dialog that will be shown on PLAYBACK_FINISHED
         d = EmcDialog(title=_('Suggestions'), style='list',
                       done_cb=self._suggestion_selected_cb)
         d.hide()
         for item in suggested:
            d.list_item_append(item[F_LABEL], item_data=item)
         d.list_go()
         events.listener_add_single_shot("PLAYBACK_FINISHED", lambda: d.show())

      (next_state, label, url, info, icon, poster, action) = parent_item_data
      if items and action != ACT_MORE:
         self._browser.page_add(url, label, None,
                                self._populate_requested_page, items)
      elif action == ACT_MORE:
         self._populate_requested_page(self._browser, url, items, scroll=True)
      else:
         self._populate_requested_page(self._browser, url, items)

   def _suggestion_selected_cb(self, dia, item_data):
      self._request_page(item_data)
      dia.delete()

   def _populate_requested_page(self, browser, url, items, scroll=False):
      for item_data in items:
         (next_state, label, url, info, icon, poster, action) = item_data
         self._browser.item_add(StandardItemClass(), url, item_data)

      if scroll is True:
         self._browser.item_bring_in(pos='top', animated=True)


