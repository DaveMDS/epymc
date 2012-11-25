#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
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


import os
import ConfigParser
import ast

import evas, elementary

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.utils import EmcExec
from epymc.widgets import EmcDialog

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.utils as utils
import epymc.gui as gui
import epymc.ini as ini



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
   info = """Long info for the film module, explain what it does and what it 
need to work well, can also use markup like <title>this</> or <b>this</>"""

   _browser = None
   _sources = []
   _current_src = None
   _item_data = {}
   _run_dialog = None

   _search_folders = [
      os.path.dirname(__file__),
      os.path.join(utils.config_dir_get(), 'channels')
      # TODO add a system dir....but where?
      ]

   def __init__(self):
      global _mod
      
      LOG('dbg', 'Init module')

      self._item_data = {}
      _mod = self

      # add an item in the mainmenu
      img = os.path.join(os.path.dirname(__file__), 'menu_bg.png')
      mainmenu.item_add('onlinechannels', 10, 'Online Channels',
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
      src = self._current_src
      item_data = (0, src['label'], 'index', None, None, None, 0)
      self._request_page(item_data)

   def _request_page(self, item_data):
      (next_state, label, url, info, icon, poster, action) = item_data
      src = self._current_src
      cmd = '%s %d "%s"' % (src['exec'], next_state, url)
      LOG('dbg', 'Executing: ' + cmd)
      EmcExec(cmd, True, self._request_page_done, item_data)
      self._run_dialog = EmcDialog(title = 'please wait', style = 'cancel',
                                   text = 'Scraping site...', )

   def _request_page_done(self, output, page_data):
      self._run_dialog.delete()
      # get all the valid items from the output of the command
      lines = output.split('\n')
      items = []
      for line in lines:
         # LOG('dbg', ' ---' + line)
         if line.startswith('PLAY!http://'):
            LOG('inf', 'yes sir..' + line)
            url = line[5:]
            mediaplayer.play_url(url)

            # if self._item_data.has_key(url):
               # item_data = self._item_data[url]
               # mediaplayer.poster_set(item_data[F_POSTER])
               # mediaplayer.title_set(item_data[F_TITLE])
               # return item_data[F_POSTER] or self._current_src['poster']

            return
         else:
            try:
               # WARNING keep item_data consistent !
               (next_state, label, url, info, icon, poster, action) = \
                     ast.literal_eval(line)
               item_data = (next_state, label, url, info, icon, poster, action)
               items.append(item_data)
               LOG('dbg', str(item_data))
            except:
               continue
      
      if len(items) < 1:
         EmcDialog(text = 'Error executing script', style = 'error')
         return

      (next_state, label, url, info, icon, poster, action) = page_data
      if action != ACT_MORE:
         # store the items data in the dictiornary (key=url)
         del self._item_data # TODO need to del all the item_data inside?? !!!!!!!!!!!!!!!!!!!!!!
         self._item_data = {}

         # new browser page
         self._browser.page_add(url.encode('ascii'), label, None,
                                self._populate_requested_page, items)

   def _populate_requested_page(self, browser, url, items):
      for item_data in items:
         (next_state, label, url, info, icon, poster, action) = item_data
         self._browser.item_add(StandardItemClass(), url, item_data)
         self._item_data[url] = item_data


