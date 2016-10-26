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
import locale
from lxml import etree
# from operator import attrgetter

from efl import ecore
from efl.elementary import utf8_to_markup

import epymc.utils as utils
import epymc.gui as gui
# import epymc.ini as ini
# import epymc.config_gui as cgui

from .kodi_addon import KodiAddonBase
from .kodi_pluginsource import KodiAddon



def DBG(*args):
   print('KODI REPO:', *args)
   pass


def load_available_repos():
   L = []
   # r = KodiRepository('http://mirrors.kodi.tv/addons/krypton')
   r = KodiRepository('/home/dave/.config/epymc/kodi/repos/repository.kodi_official/addon.xml')
   L.append(r)
   return L





class KodiRepository(KodiAddonBase):

   extension_point = ".//extension[@point='xbmc.addon.repository']"

   def __init__(self, xml_info):
      KodiAddonBase.__init__(self, xml_info)
      self._addons = []

      ext = self._root.find(self.extension_point)
      for elem in ext.iterchildren():
         if elem.tag == 'info':
            self._addons_info_url = elem.text
         elif elem.tag == 'checksum':
            self._addons_list_md5_url = elem.text
         elif elem.tag == 'datadir':
            self._base_url = elem.text

   @property
   def base_url(self):
      """ ex: http://mirrors.kodi.tv/addons/krypton (datadir) """
      return self._base_url

   @property
   def addons_list_url(self):
      """ ex: http://mirrors.kodi.tv/addons/krypton/addons.xml (info) """
      return self._addons_info_url

   @property
   def addons_xml(self):
      """ ex: http://mirrors.kodi.tv/addons/krypton/addons.xml (info) """
      local = os.path.join(self._folder, 'addons.xml')
      remote = self._addons_info_url
      return (local, remote)

   @property
   def addons_list_md5_url(self):
      """ ex: http://mirrors.kodi.tv/addons/krypton/addons.xml.md5 (checksum) """
      return self._addons_list_md5_url

   def get_addons(self, done_cb, **kargs):
      if self._addons:
         done_cb(self, self._addons, **kargs) # hmm, I don't like this instant resolution...

      self._done_cb = done_cb
      self._done_cb_kargs = kargs

      local, remote = self.addons_xml
      if os.path.exists(local): # TODO check updates (using the checksum file)
         self._parse_xml(local)
      else:
         self._download_xml(local, remote)

   def _download_xml(self, local, remote):
      utils.download_url_async(remote, dest=local,
                               complete_cb=self._download_xml_complete_cb,
                               progress_cb=None)
      

   def _download_xml_complete_cb(self, dest, status):
      self._parse_xml(dest)

   def _parse_xml(self, local):
      print("PARSE")
      root = etree.parse(local).getroot()
      print(root)
      for addon_el in root.iterchildren():
         ext = addon_el.find(".//extension[@point='xbmc.python.pluginsource']")
         if ext is not None:
            self._addons.append(KodiAddon(addon_el, repository=self))
         # id = addon_el.get('id')
         # if id.startswith(('plugin.video.', 'plugin.audio.', 'plugin.image.')):
            # self._addons.append(KodiAddon(xml_element=addon_el, repo=self))
            # self._addons.append(KodiAddon(addon_el))

      self._done_cb(self, self._addons, **self._done_cb_kargs)
      

class KodiRepository_OLD(object):

   supported_extensions = ('xbmc.python.pluginsource')

   def __init__(self, base_url):
      self._addons = []
      self._base_url = base_url
      self._xml_url = base_url + '/addons.xml'
      self._xml_cache = os.path.join(utils.user_cache_dir, 'kodirepos', 'asasd', 'addons.xml') # TODO fix asasd !! :)
      # http://mirrors.kodi.tv/addons/krypton/addons.xml

   def __str__(self):
      return '<KodiRepo from {}>'.format(self._base_url)





