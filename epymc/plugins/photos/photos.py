#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2014 Davide Andreoli <dave@gurumeditation.it>
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

# from efl import ecore, evas
# from efl.elementary.image import Image
# from efl.elementary.entry import utf8_to_markup

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
# from epymc.gui import EmcDialog, EmcSourcesManager, EmcNotify, EmcRemoteImage
from epymc.gui import EmcSourcesManager

import epymc.mainmenu as mainmenu
import epymc.ini as ini
import epymc.gui as gui
import epymc.utils as utils
# import epymc.events as events
# import epymc.config_gui as config_gui


# debuggin stuff
def DBG(msg):
   print('PHOTOS: %s' % msg)
   pass


IMG_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif')

mod_instance = None


class AddSourceItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      EmcSourcesManager('photos', done_cb=self._manager_cb)

   def _manager_cb(self, sources):
      mod_instance._folders = sources
      mod_instance._browser.refresh(hard=True)

   def label_get(self, url, mod):
      return _('Manage sources')

   def icon_get(self, url, mod):
      return 'icon/plus'


class PhotoItemClass(EmcItemClass):
   # def item_selected(self, url, mod):
      # mod_instance.play_url(url)

   def label_get(self, url, mod):
      return os.path.basename(url)

   def icon_get(self, url, mod):
      print("ICON", url)
   
   def poster_get(self, url, mod):
      return utils.url2path(url)


class FolderItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod_instance._browser.page_add(url, os.path.basename(url),
                                     None, mod_instance.populate_url)

   def label_get(self, url, mod):
      return os.path.basename(url)

   def icon_get(self, url, mod):
      return 'icon/folder'



class PhotosModule(EmcModule):
   name = 'phptos'
   label = _('Photos')
   icon = 'icon/photo'
   info = _('A module to browse your photos collection.')

   _browser = None            # the Browser widget instance


   def __init__(self):
      DBG('Init module')

      global mod_instance
      mod_instance = self

      # create config ini section if not exists, with defaults
      ini.add_section('photos')
      # if not ini.has_option('tvshows', 'episode_regexp'):
         # ini.set('tvshows', 'episode_regexp', DEFAULT_EPISODE_REGEXP)
      # if not ini.has_option('tvshows', 'info_lang'):
         # ini.set('tvshows', 'info_lang', DEFAULT_INFO_LANG)

      # add an item in the mainmenu
      mainmenu.item_add('photos', 15, _('Photos'), 'icon/photo', self.cb_mainmenu)

      # add an entry in the config gui
      # config_gui.root_item_add('photos', 11, _('Tv Shows Collection'),
                               # icon='icon/tv', callback=config_panel_cb)

      # create a browser instance
      self._browser = EmcBrowser(_('Photos'), 'List')

      # listen to emc events
      # events.listener_add('photos', self._events_cb)

   def __shutdown__(self):
      DBG('Shutdown module')

      # stop listening for events
      # events.listener_del('photos')

      # delete mainmenu item
      mainmenu.item_del('photos')

      # delete config menu item
      # config_gui.root_item_del('photos')

      # delete browser
      self._browser.delete()


###### BROWSER STUFF
   def cb_mainmenu(self):
      # get folders from config
      self._folders = ini.get_string_list('photos', 'folders', ';')

      # if not self._folders:
         #TODO alert the user. and instruct how to add folders

      self._browser.page_add('photos://root', _('Photos'), None, self.populate_root_page)
      self._browser.show()
      mainmenu.hide()

   def populate_root_page(self, browser, page_url):
      for folder in self._folders:
         self._browser.item_add(FolderItemClass(), folder, None)

      self._browser.item_add(AddSourceItemClass(), 'photo://add_source', self)

   def populate_url(self, browser, url):
      dirs, files = [], []
      for fname in os.listdir(url[7:]):
         if fname[0] == '.': continue
         if os.path.isdir(os.path.join(url[7:], fname)):
            dirs.append(fname)
         else:
            name, ext = os.path.splitext(fname)
            if ext.lower() in IMG_EXTENSIONS:
               files.append(fname)

      for fname in utils.natural_sort(dirs):
         self._browser.item_add(FolderItemClass(), os.path.join(url, fname), self)
      for fname in utils.natural_sort(files):
         self._browser.item_add(PhotoItemClass(), os.path.join(url, fname), self)

   """
   def _events_cb(self, event):
      # TODO: check that we are active and visible
      #       atm, this is fired also when a song end...
      if event == 'PLAYBACK_FINISHED':
         # refresh the page (maybe an unwatched movie becomes watched)
         if self._browser is not None:
            self._browser.refresh()
   """


"""
###### Config Panel stuff
def config_panel_cb():
   bro = config_gui.browser_get()
   bro.page_add('config://tvshows/', _('TV Shows'), None, populate_config)

def populate_config(browser, url):
   config_gui.standard_item_lang_add('tvshows', 'info_lang',
                                     _('Preferred language for contents'))
"""
