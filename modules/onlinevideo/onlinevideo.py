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
from epymc.browser import EmcBrowser
from epymc.utils import EmcExec
from epymc.gui import EmcDialog

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
      LOG('dbg', 'Init module')

      # create config ini section if not exists
      # ini.add_section('film')

      # open film/person database (they are created if not exists)
      # self.__film_db = EmcDatabase('film')
      # self.__person_db = EmcDatabase('person')
      self._item_data = {}

      # add an item in the mainmenu
      img = os.path.join(os.path.dirname(__file__), 'menu_bg.png')
      mainmenu.item_add('onlinechannels', 10, 'Online Channels',
                        img, self.cb_mainmenu)

      # create a browser instance
      self._browser = EmcBrowser('OnlineChannels', 'List',
                              item_selected_cb = self.cb_url_selected,
                              icon_get_cb = self.cb_icon_get,
                              poster_get_cb = self.cb_poster_get,
                              fanart_get_cb = self.cb_fanart_get,
                              info_get_cb = self.cb_info_get)

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


###### BROWSER STUFF
   def cb_mainmenu(self):
      self.create_root_page()
      mainmenu.hide()
      self._browser.show()

   def create_root_page(self):
      self._browser.page_add('olvid://root', 'Channels')
      if not self._sources: self.build_sources_list()
      for source in self._sources:
         self._browser.item_add(source['name'], source['label'])

   def cb_url_selected(self, page_url, item_url):
      if page_url == 'olvid://root':
         self.set_current_source(item_url)
         self._request_index()
      elif item_url == 'olvid://root':
         self.create_root_page()
      else:
         self._request_index()

   # def cb_source_selected(self, fullpath):
      # self.__folders.append(fullpath)
      # ini.set_string_list('film', 'folders', self.__folders, ';')
      # self.__browser.refresh(recreate=True)

   def cb_icon_get(self, page_url, item_url):
      if page_url == 'olvid://root':
         source = self.get_source_by_name(item_url)
         return source['icon']
      return None

   def cb_poster_get(self, page_url, item_url):
      if page_url == 'olvid://root':
         source = self.get_source_by_name(item_url)
         return source['poster']

      print page_url, item_url
      return None

   def cb_fanart_get(self, page_url, item_url):
      if page_url == 'olvid://root':
         source = self.get_source_by_name(item_url)
         return source['backdrop']
      return None

   def cb_info_get(self, page_url, item_url):
      if page_url == 'olvid://root':
         source = self.get_source_by_name(item_url)
         text  = '<title>%s</><br>' \
                 '<hilight>version:</> %s<br>' \
                 '<hilight>author:</> %s<br>' \
                 '<br>%s<br>' % \
                 (source['label'], source['version'], source['author'], source['info'])
         return text


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

   def set_current_source(self, src_name):
      for s in self._sources:
         if s['name'] == src_name:
            self._current_src = s
            return

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
            mediaplayer.play_video(url)

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
         self._browser.page_add(url.encode('ascii'), label,
                                item_selected_cb = self._item_selected_cb,
                                icon_get_cb = self._item_icon_cb,
                                poster_get_cb = self._item_poster_cb,
                                fanart_get_cb = None,
                                info_get_cb = self._item_info_cb,
                                page_data = page_data)
      for item_data in items:
         (next_state, label, url, info, icon, poster, action) = item_data
         self._browser.item_add(url, item_data[F_LABEL])
         self._item_data[url] = item_data

   def _item_selected_cb(self, page_url, item_url, page_data):
      if self._item_data.has_key(item_url):
         item_data = self._item_data[item_url]
         self._request_page(item_data)
      elif page_data:
         self._request_page(page_data)

   def _item_icon_cb(self, page_url, item_url):
      if self._item_data.has_key(item_url):
         item_data = self._item_data[item_url]
         if not item_data[F_ICON] and item_data[F_ACTION] == ACT_FOLDER:
            return 'icon/folder'
         return item_data[F_ICON]

   def _item_poster_cb(self, page_url, item_url):
      if self._item_data.has_key(item_url):
         item_data = self._item_data[item_url]
         return item_data[F_POSTER] or self._current_src['poster']

   def _item_info_cb(self, page_url, item_url):
      if self._item_data.has_key(item_url):
         item_data = self._item_data[item_url]
         return item_data[F_INFO]
