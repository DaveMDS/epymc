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

from __future__ import absolute_import, print_function

import os
from lxml import etree

import epymc.utils as utils

from .kodi_addon_base import KodiAddonBase, addon_factory, base_repos_path


def DBG(*args):
   print('KODI REPO:', *args)
   pass


class KodiRepository(KodiAddonBase):

   extension_point = ".//extension[@point='xbmc.addon.repository']"

   def __init__(self, *args):
      KodiAddonBase.__init__(self, *args)
      self._addons = {} # key: addon_id  val: KodiAddon instance

      ext = self._root.find(self.extension_point)
      for elem in ext.iterchildren():
         if elem.tag == 'info':
            self._addons_xml_url = elem.text.strip()
         elif elem.tag == 'checksum':
            self._addons_xml_md5_url = elem.text.strip()
         elif elem.tag == 'datadir':
            self._base_url = elem.text.strip()

   @property
   def base_url(self):
      """ ex: http://mirrors.kodi.tv/addons/krypton (datadir) """
      return self._base_url

   @property
   def addons_xml(self):
      """ Local path and remote url for the addons.xml file (tuple) """
      local = os.path.join(base_repos_path, self.id , 'addons.xml')
      remote = self._addons_xml_url
      return (local, remote)

   @property
   def addons_xml_md5(self):
      """ Local path and remote url for the addons.xml.md5 file (tuple) """
      local = os.path.join(base_repos_path, self.id , 'addons.xml.md5')
      remote = self._addons_xml_md5_url
      return (local, remote)

   def addon_available(self, addon_id, min_version=None):
      """ return the KodiAddon instance if available, also check min_version if given """
      addon = self._addons.get(addon_id)
      if addon and min_version and addon.check_version(min_version) == False:
         return None
      return addon

   def get_addons(self, done_cb, **kargs):
      """ TODO doc """
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
      root = etree.parse(local).getroot()
      for addon_el in root.iterchildren():
         addon = addon_factory(addon_el, self)
         if addon:
            self._addons[addon.id] = addon

      self._done_cb(self, self._addons, **self._done_cb_kargs)



