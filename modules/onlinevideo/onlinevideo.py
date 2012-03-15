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
# import epymc.ini as ini
import epymc.utils as utils
import epymc.gui as gui




DEBUG = True
DEBUGN = 'ONLINEVID'
def LOG(sev, msg):
   if   sev == 'err': print('%s ERROR: %s' % (DEBUGN, msg))
   elif sev == 'inf': print('%s: %s' % (DEBUGN, msg))
   elif sev == 'dbg' and DEBUG: print('%s: %s' % (DEBUGN, msg))
if DEBUG:
   from pprint import pprint
   import pdb


class OnlinevideoModule(EmcModule):
   name = 'onlinevideo'
   label = 'Online Videos'
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
      os.path.join(utils.config_dir_get(), 'video_sources')
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
      mainmenu.item_add('onlinevideo', 10, 'Online Videos',
                        img, self.cb_mainmenu)

      # create a browser instance
      self._browser = EmcBrowser('OnlineVideos', 'List',
                              item_selected_cb = self.cb_url_selected,
                              icon_get_cb = self.cb_icon_get,
                              poster_get_cb = self.cb_poster_get,
                              fanart_get_cb = self.cb_fanart_get,
                              info_get_cb = self.cb_info_get)

   def __shutdown__(self):
      LOG('dbg', 'Shutdown module')
      # delete mainmenu item
      mainmenu.item_del('onlinevideo')
      # delete browser
      self._browser.delete()

   def parse_source_ini_file(self, path):
      section = 'EmcVideoSource'
      source = {}
      parser = ConfigParser.ConfigParser()
      parser.read(path)
      if parser.has_section(section):
         if not parser.has_option(section, 'name') or \
            not parser.has_option(section, 'label') or \
            not parser.has_option(section, 'info') or \
            not parser.has_option(section, 'icon') or \
            not parser.has_option(section, 'poster') or \
            not parser.has_option(section, 'fanart') or \
            not parser.has_option(section, 'version') or \
            not parser.has_option(section, 'exec'):
            return
         dirname = os.path.dirname(path)
         source['name'] = parser.get(section, 'name')
         source['label'] = parser.get(section, 'label')
         source['info'] = parser.get(section, 'info')
         source['icon'] = os.path.join(dirname, parser.get(section, 'icon'))
         source['exec'] = os.path.join(dirname, parser.get(section, 'exec'))
         source['poster'] = os.path.join(dirname, parser.get(section, 'poster'))
         source['fanart'] = os.path.join(dirname, parser.get(section, 'fanart'))
         source['version'] = os.path.join(dirname, parser.get(section, 'version'))
      del parser
      return source


###### BROWSER STUFF
   def cb_mainmenu(self):
      self.create_root_page()
      mainmenu.hide()
      self._browser.show()

   def create_root_page(self):
      self._browser.page_add('olvid://root', 'Online Videos')
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

   def cb_source_selected(self, fullpath):
      self.__folders.append(fullpath)
      ini.set_string_list('film', 'folders', self.__folders, ';')
      self.__browser.refresh(recreate=True)

   def cb_icon_get(self, page_url, item_url):
      if page_url == 'olvid://root':
         source = self.get_source_by_name(item_url)
         # return 'icon/plus'
         return source['icon']
      # print page_url, item_url
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
         return source['fanart']
      return None

   def cb_info_get(self, page_url, item_url):
      if page_url == 'olvid://root':
         source = self.get_source_by_name(item_url)
         return source['info']
      return 'Not found'


###### SOURCES STUFF
   def build_sources_list(self):
      # search all the source.ini files in all the subdirs of _search_folders
      for folder in self._search_folders:
         for top, dirs, files in os.walk(folder):
            for f in files:
               if f == 'source.ini':
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
      cmd = '%s %d %s' % (src['exec'], 0, 'url')
      item_data = (src['label'],'index',0,'',0)
      self._request_page(item_data)

   def _request_page(self, item_data):
      (label,url,state,icon,action) = item_data
      src = self._current_src
      cmd = '%s %d "%s"' % (src['exec'], state, url)
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
            mediaplayer.play_video(line[5:])
            return
         else:
            try:
               # WARNING keep item_data consistent !
               (label, url, state, icon, action) = ast.literal_eval(line)
               item_data = (label,url,state,icon,action)
               items.append(item_data)
               LOG('dbg', str(item_data))
            except:
               continue
      
      if len(lines) < 1:
         EmcDialog(text = 'Error executing script', style = 'error')
         return

      (label,url,state,icon,action) = page_data
      if action != 2:
         # store the items data in the dictiornary (key=url)
         del self._item_data # TODO need to del all the item_data inside?? !!!!!!!!!!!!!!!!!!!!!!
         self._item_data = {}

         # new browser page
         self._browser.page_add(url.encode('ascii'), label,
                                item_selected_cb = self._item_selected_cb,
                                icon_get_cb = self._item_image_cb,
                                poster_get_cb = self._item_image_cb,
                                fanart_get_cb = None,
                                info_get_cb = None,
                                page_data = page_data)
      for item_data in items:
         (label, url, state, icon, action) = item_data
         if not icon and action == 1:
            icon = 'icon/folder'
         self._browser.item_add(url, label)
         self._item_data[url] = (label, url, state, icon, action)

   def _item_selected_cb(self, page_url, item_url, page_data):
      if self._item_data.has_key(item_url):
         item_data = self._item_data[item_url]
         self._request_page(item_data)
      elif page_data:
         self._request_page(page_data)

   def _item_image_cb(self, page_url, item_url):
      if self._item_data.has_key(item_url):
         item_data = self._item_data[item_url]
         return item_data[3]
