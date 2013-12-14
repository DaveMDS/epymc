#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2013 Davide Andreoli <dave@gurumeditation.it>
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

import os
import ast
try:
   import configparser as ConfigParser
except:
   import ConfigParser

from efl import evas, elementary

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.utils import EmcExec
from epymc.gui import EmcDialog, EmcVKeyboard

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.utils as utils
import epymc.gui as gui
import epymc.ini as ini
import epymc.events as events



DEBUG = True
DEBUGN = 'ONLINEVID'
def LOG(sev, msg):
   if   sev == 'err': print('%s ERROR: %s' % (DEBUGN, msg))
   elif sev == 'inf': print('%s: %s' % (DEBUGN, msg))
   elif sev == 'dbg' and DEBUG: print('%s: %s' % (DEBUGN, msg))
if DEBUG:
   from pprint import pprint
   import pdb


ACT_NONE = 0
ACT_FOLDER = 1
ACT_MORE = 2
ACT_PLAY = 3
ACT_SEARCH = 4

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
      return url

   def icon_get(self, url, channel):
      return channel['icon']

   def poster_get(self, url, channel):
      return channel['poster']

   def fanart_get(self, url, channel):
      return channel['backdrop']

   def info_get(self, url, channel):
      return '<title>%s</><br>' \
             '<hilight>version:</> %s<br>' \
             '<hilight>author:</> %s<br>' \
             '<br>%s<br>' % \
             (channel['label'], channel['version'],
              channel['author'], channel['info'])


class StandardItemClass(EmcItemClass):
   def item_selected(self, url, item_data):
      _mod._request_page(item_data)

   def label_get(self, url, item_data):
      return item_data[F_LABEL]

   def icon_get(self, url, item_data):
      if not item_data[F_ICON] and item_data[F_ACTION] == ACT_FOLDER:
            return 'icon/folder'
      return item_data[F_ICON]
   
   def poster_get(self, url, item_data):
      return item_data[F_POSTER] or _mod._current_src['poster']

   def info_get(self, url, item_data):
       return item_data[F_INFO]



class OnlinevideoModule(EmcModule):
   name = 'onlinevideo'
   label = 'Online Channels'
   icon = 'icon/module'
   info = """Long info for the online channels module, explain what it does and what it 
need to work well, can also use markup like <title>this</> or <b>this</>"""

   _browser = None
   _sources = []
   _current_src = None
   _run_dialog = None

   _search_folders = [
      os.path.dirname(__file__),
      os.path.join(utils.user_conf_dir, 'channels')
      # TODO add a system dir....but where?
      ]

   def __init__(self):
      global _mod
      
      LOG('dbg', 'Init module')

      _mod = self

      # add an item in the mainmenu
      img = os.path.join(os.path.dirname(__file__), 'menu_bg.png')
      mainmenu.item_add('onlinechannels', 15, 'Online Channels',
                        img, self.cb_mainmenu)

      # create the browser instance
      self._browser = EmcBrowser('OnlineChannels')

   def __shutdown__(self):
      LOG('dbg', 'Shutdown module')
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
      self._browser.page_add('olvid://root', 'Channels', None,
                             self.populate_root_page)
      self._browser.show()
      mainmenu.hide()

   def populate_root_page(self, browser, url):
      if not self._sources:
         self.build_sources_list()
      for ch in self._sources:
         self._browser.item_add(ChannelItemClass(), ch['name'], ch)


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
      item_data = (0, src['label'], 'index', None, None, None, 0)
      self._request_page(item_data)

   def _request_page(self, item_data):
      # request a specific page from the channel
      (next_state, label, url, info, icon, poster, action) = item_data
      if action == ACT_PLAY:
         mediaplayer.play_url(url)
         mediaplayer.title_set(label)
         mediaplayer.poster_set(poster)
      elif action == ACT_SEARCH:
         EmcVKeyboard(title = 'Search query', user_data = item_data,
                      accept_cb = self._search_vkeyb_done)
      else:
         src = self._current_src
         cmd = '%s %d "%s"' % (src['exec'], next_state, url)
         LOG('dbg', 'Executing: ' + cmd)
         EmcExec(cmd, True, self._request_page_done, item_data)
         self._run_dialog = EmcDialog(title = 'please wait', style = 'cancel',
                                      text = 'Scraping site...', )

   def _search_vkeyb_done(self, vkeyb, text, item_data):
      (next_state, label, url, info, icon, poster, action) = item_data
      src = self._current_src
      cmd = '%s %d "%s"' % (src['exec'], next_state, text)
      LOG('dbg', 'ExecutingSearch: ' + cmd)
      EmcExec(cmd, True, self._request_page_done, item_data)
      self._run_dialog = EmcDialog(title = 'please wait', style = 'cancel',
                                   text = 'Scraping site...', )

   def _request_page_done(self, output, parent_item_data):
      # parse the output of the channel execution
      self._run_dialog.delete()
      lines = output.split('\n')
      items = []
      suggested = None
      for line in lines:
         LOG('dbg', ' ---' + line)
         if line.startswith('PLAY!'):
            LOG('inf', 'yes sir..' + line)
            url = line[5:]
            mediaplayer.play_url(url)
            mediaplayer.poster_set(parent_item_data[F_POSTER]) # TODO FIXME
            mediaplayer.title_set(parent_item_data[F_LABEL])
            suggested = [] # from now on every item is a suggestion
         else:
            try:
               # WARNING keep item_data consistent !
               (next_state, label, url, info, icon, poster, action) = \
                     ast.literal_eval(line)
               item_data = (next_state, label, url, info, icon, poster, action)
               if suggested is not None:
                  suggested.append(item_data)
               else:
                  items.append(item_data)
               LOG('dbg', str(item_data))
            except:
               continue
      
      if len(items) < 1 and suggested is None:
         EmcDialog(text = 'Error executing script', style = 'error')
         return

      if suggested and len(suggested) > 0:
         # prepare the suggestions dialog that will be shown on PLAYBACK_FINISHED
         d = EmcDialog(title = 'Suggestions', style = 'list',
                       done_cb = self._suggestion_selected_cb)
         d.hide()
         for item in suggested:
            d.list_item_append(item[F_LABEL], item_data=item)
         events.listener_add_single_shot("PLAYBACK_FINISHED", lambda: d.show())

      (next_state, label, url, info, icon, poster, action) = parent_item_data
      if items and action != ACT_MORE:
         self._browser.page_add(url.encode('ascii'), label, None,
                                self._populate_requested_page, items)
      else:
         self._populate_requested_page(self._browser, url, items)

   def _suggestion_selected_cb(self, dia, item_data):
      self._request_page(item_data)
      dia.delete()

   def _populate_requested_page(self, browser, url, items):
      for item_data in items:
         (next_state, label, url, info, icon, poster, action) = item_data
         self._browser.item_add(StandardItemClass(), url, item_data)

