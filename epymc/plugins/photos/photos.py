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

try:
   from PIL import Image as PILImage
   from PIL.ExifTags import TAGS as PILTags
except ImportError:
   pil_available = False
else:
   pil_available = True

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.gui import EmcSourcesManager, EmcSlideshow

import epymc.mainmenu as mainmenu
import epymc.ini as ini
import epymc.utils as utils
import epymc.config_gui as cgui



# debuggin stuff
def DBG(msg):
   print('PHOTOS: %s' % msg)
   pass


mod_instance = None


def extract_usefull_exif(pil_image):
   ret = {}
   info = pil_image._getexif()
   if info is not None:
      for tag, val in info.items():
         name = PILTags.get(tag, tag)
         print(name, repr(val))
         if name in ('DateTime','Flash', 'ISOSpeedRatings', 'Make', 'Model', 'Orientation'):
            ret[name] = val
         elif name == 'ExposureTime':
            ret[name] = '%.3f (%d/%d)' % ((val[0] / val[1]), val[0], val[1])
         elif name == 'FNumber':
            ret[name] = 'f%.1f' % (val[0] / val[1])
         elif name == 'ApertureValue':
            ret[name] = '%.1f mm' % (val[0] / val[1])
   return ret


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
   def item_selected(self, url, mod):
      EmcSlideshow(url, delay=ini.get_int('photos', 'slideshow_delay'),
               show_controls=ini.get_bool('photos', 'slideshow_show_controls'))

   def label_get(self, url, mod):
      return os.path.basename(url)

   def icon_get(self, url, mod):
      return 'icon/photo'
   
   def poster_get(self, url, mod):
      return utils.url2path(url)

   def info_get(self, url, mod):
      path = utils.url2path(url)
      file_size = utils.hum_size(os.path.getsize(path))
      basic = '<title>{}</title><br>' \
              '<name>{}:</name> {}<br>'.format(os.path.basename(path),
                                               _('File size'), file_size)
      if pil_available:
         i = PILImage.open(path)
         # basic image info
         pil = '<name>{}:</name> {} x {} pixel<br>' \
               '<name>{}:</name> {} ({})<br>'.format(
                  _('Dimensions'), i.size[0], i.size[1],
                  _('Format'), i.format, i.mode)

         # exif info
         exif_dict = extract_usefull_exif(i)
         exif = []
         for name, value in exif_dict.items():
            exif.append('<small><name>{}:</name> {}</small>'.format(name, value))
         if len(exif) > 0:
            exif = '<br>'.join(exif)
         else:
            exif = ''
      else:
         exif = ''
         pil = '<small>{}</small>'.format(
                _('Please install PIL to read image metadata.'))

      return basic + pil + exif


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
   info = _('A module to watch your photos.')

   _browser = None


   def __init__(self):
      DBG('Init module')

      # keep a global instance reference (to be accessed from the item classes)
      global mod_instance
      mod_instance = self

      # create config ini section if not exists, with defaults
      ini.add_section('photos')
      ini.get('photos', 'slideshow_delay', 4)
      ini.get('photos', 'slideshow_show_controls', 'True')

      # add an item in the mainmenu
      mainmenu.item_add('photos', 15, _('Photos'), 'icon/photo', self.cb_mainmenu)

      # add an entry in the config gui
      cgui.root_item_add('photos', 14, _('Photos'), icon='icon/photo',
                         callback=self.config_panel_cb)

      # create a browser instance
      self._browser = EmcBrowser(_('Photos'), 'List')

   def __shutdown__(self):
      DBG('Shutdown module')

      # delete mainmenu item
      mainmenu.item_del('photos')

      # delete config menu item
      cgui.root_item_del('photos')

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
            if ext.lower() in utils.supported_images:
               files.append(fname)

      for fname in utils.natural_sort(dirs):
         self._browser.item_add(FolderItemClass(), os.path.join(url, fname), self)
      for fname in utils.natural_sort(files):
         self._browser.item_add(PhotoItemClass(), os.path.join(url, fname), self)


###### Config Panel stuff
   def config_panel_cb(self):
      bro = cgui.browser_get()
      bro.page_add('config://photos/', _('Photos'), None, self.populate_config)

   def populate_config(self, browser, url):
      cgui.standard_item_bool_add('photos', 'slideshow_show_controls',
                                  _('Show slideshow controls on start'))
      L = '3 4 5 10 15 20 30 60'.split()
      cgui.standard_item_string_from_list_add('photos', 'slideshow_delay',
                                              _('Slideshow delay'), L)

