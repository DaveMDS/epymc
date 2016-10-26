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
from operator import attrgetter

from efl import ecore
from efl.elementary import utf8_to_markup

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.utils as utils
import epymc.gui as gui
# import epymc.ini as ini
# import epymc.config_gui as cgui

# from epymc.modules import EmcModule
# from epymc.browser import EmcBrowser, EmcItemClass
# from epymc.gui import EmcDialog, EmcImage



def DBG(*args):
   print('KODI ADDON:', *args)
   pass


def addon_factory(xml_info, repository=None):
   """ TODO doc """

   if isinstance(xml_info, etree._Element):
      root = xml_info
   elif os.path.exists(xml_info):
      document = etree.parse(xml_info)
      root = document.getroot()
   else:
      raise TypeError('xml_info must be str (xml file) or ET Element, given: %s' % xml_info)

   # create the correct subclass (based on the xlm extension point)   
   ext = root.find(".//extension[@point='xbmc.python.pluginsource']")
   if ext is not None:
      from .kodi_pluginsource import KodiAddon
      return KodiAddon(root, repository)

   ext = root.find(".//extension[@point='xbmc.python.module']")
   if ext is not None:
      from .kodi_module import KodiModule
      return KodiModule(root, repository)

   ext = root.find(".//extension[@point='xbmc.addon.repository']")
   if ext is not None:
      from .kodi_repository import KodiRepository
      return KodiRepository(root)


class KodiAddonBase(object):
   """ Base class for any kodi addon: pluginsource, repository or python module """

   def __init__(self, xml_root, repository=None):
      print("\n##### ADDON FROM: %s  #####" % xml_root)
      self._repo = repository
      self._root = xml_root

      self._id = xml_root.get('id')
      self._name = xml_root.get('name')
      self._version = xml_root.get('version')
      self._author = xml_root.get('provider-name')
      self._metadata = None # will be lazily parsed
      self._requires = None # will be lazily parsed

      if repository is None:
         self._folder = os.path.join(utils.user_conf_dir, 'kodi', 'addons', self._id)
      else:
         self._folder = None

   def __str__(self):
      return '<{0.__class__.__name__} id={0.id} version={0.version}>'.format(self)

   def __lt__(self, other):
      return self.name.lower() < other.name.lower()

   def __gt__(self, other):
      return self.name.lower() > other.name.lower()

   @property
   def is_installed(self):
      return self._folder is not None

   @property
   def installed_path(self):
      """ full path of the installed addon """
      return self._folder

   @property
   def repository(self):
      """ KodiRepository instance (if provided) """
      return self._repo

   @property
   def id(self):
      """ex: 'plugin.video.southpark' or 'repository.kodi_official' """
      return self._id

   @property
   def name(self):
      """ ex: 'South Park' """
      return self._name

   @property
   def version(self):
      """ ex: '0.4.3' """
      return self._version

   @property
   def author(self):
      """ ex: 'DaveMDS' """
      return self._author

   @property
   def icon(self):
      if self.is_installed:
         icon = os.path.join(self._folder, self.metadata.get('icon'))
         if os.path.exists(icon):
            return icon
      else:
         return os.path.join(self._repo.base_url, self._id, self.metadata.get('icon'))

   @property
   def fanart(self):
      if self.is_installed:
         fart = os.path.join(self._folder, self.metadata.get('fanart'))
         if os.path.exists(fart):
            return fart
      else:
         fart = self.metadata.get('fanart')
         if fart:
            return os.path.join(self._repo.base_url, self._id, fart)

   @property
   def requires(self):
      """ [ (id, vers), ... ] """
      if self._requires is None:
         self._requires = []
         for require in self._root.find('requires'):
            id = require.get('addon')
            ver = require.get('version')
            if id and ver and id != 'xbmc.python':
               self._requires.append((id, ver))
      return self._requires

   @property
   def metadata(self):
      """ a dict containing extended addon info (parsed lazily) """
      if self._metadata is None:
         self._metadata = {'screenshots': []}
         syslang, encoding = locale.getdefaultlocale()

         meta = self._root.find(".//extension[@point='xbmc.addon.metadata']")
         for elem in meta.iterchildren():
            if elem.tag == 'assets':
               for ass_elem in elem.iterchildren():
                  if ass_elem.tag == 'screenshot':
                     self._metadata['screenshots'].append(ass_elem.text)
                  else: # 'icon' or 'fanart'
                     self._metadata[ass_elem.tag] = ass_elem.text
            else:
               lang = elem.get('lang', 'en_GB')
               if lang == syslang or lang == syslang[:2] or lang[:2] == 'en':
                  t = elem.text
                  if t:
                     self._metadata[elem.tag] = t.strip().replace('[CR]', '\n') # TODO better replace

         # old style assets
         if not self._metadata.get('icon'):
            self._metadata['icon'] = 'icon.png'
         if not self._metadata.get('fanart') and self._metadata.get('nofanart') != 'true':
            self._metadata['fanart'] = 'fanart.jpg'

      return self._metadata


   @property
   def info_text_short(self):
      pass # TODO

   @property
   def info_text_long(self):
      txt = []

      summary = self.metadata.get('summary')
      if summary:
         txt.append('<big>{}</big><br>'.format(utf8_to_markup(summary)))

      mapp = (
         ('author', _('Author')),
         ('version', _('Version')),
         ('language', _('Content language')),
         ('license', _('License')),
         ('description', _('Description')),
         ('disclaimer', _('Disclaimer')),
         ('news', _('News')),
      )
      for key, label in mapp:
         val = self.metadata.get(key) or getattr(self, key, None)
         if val:
            if key == 'language':
               val = ', '.join(val.split())
            txt.append('<name>{}:</name> <value>{}</value>'.format(
                       label, utf8_to_markup(val)))

      return '<br>'.join(txt)


