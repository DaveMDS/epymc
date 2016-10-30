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
import locale
import zipfile
import shutil
from xml.etree import ElementTree
from distutils.version import StrictVersion

from efl.elementary import utf8_to_markup

import epymc.utils as utils
import epymc.ini as ini


def DBG(*args):
   print('KODI ADDON:', *args)
   pass


base_kodi_path = os.path.join(utils.user_conf_dir, 'kodi')
base_addons_path = os.path.join(base_kodi_path, 'addons')
base_pkgs_path = os.path.join(base_kodi_path, 'packages')
base_temp_path = os.path.join(base_kodi_path, 'temp')
base_repos_path = os.path.join(base_kodi_path, 'repos')
sys_addons_path = os.path.join(os.path.dirname(__file__), 'addons')

installed_addons = {} # key: addon_in  val: KodiAddon instance


def addon_factory(xml_info, repository=None):
   """ TODO doc """
   from .kodi_pluginsource import KodiPluginSource
   from .kodi_pythonmodule import KodiPythonModule
   from .kodi_repository import KodiRepository

   # xml_info can be the xml file path or an already opened ET Element
   if isinstance(xml_info, ElementTree.Element):
      root = xml_info
      folder = None
   elif os.path.exists(xml_info):
      root = ElementTree.parse(xml_info).getroot()
      folder = os.path.dirname(xml_info)
   else:
      raise TypeError('xml_info must be str (xml file) or ET Element')

   # create the correct subclass (based on the xlm extension point)
   for elem in root.iterfind('extension'):
      ext_point = elem.get('point')

      if ext_point == 'xbmc.python.pluginsource':
         return KodiPluginSource(root, folder, repository)

      elif ext_point == 'xbmc.python.module':
         return KodiPythonModule(root, folder, repository)

      elif ext_point == 'xbmc.addon.repository':
         return KodiRepository(root, folder, repository)

      elif ext_point != 'xbmc.addon.metadata':
         DBG('Unsupported extension: "{}" for addon: "{}"'.format(
             ext_point, root.get('id')))

   return None


def load_installed_addons():
   """ Load all installed addons, in system and user dirs """

   for fname in os.listdir(sys_addons_path):
      load_single_addon(fname, True)

   for fname in os.listdir(base_addons_path):
      load_single_addon(fname)


def load_single_addon(addon_id, system=False):
   """ Load a single (installed) addon
   Args:
      addon_id (str): the addon id
      system (bool): whenever to load from system dir or user dir
   Return:
      The KodiAddon instance (any of the base subclass)
   """
   if system:
      xml_path = os.path.join(sys_addons_path, addon_id, 'addon.xml')
   else:
      xml_path = os.path.join(base_addons_path, addon_id, 'addon.xml')

   addon = addon_factory(xml_path)
   # TODO check err
   installed_addons[addon.id] = addon

   return addon


def get_installed_addon(addon_id):
   """ Get a single addon instance, addon must be installed """
   return installed_addons.get(addon_id)


def get_installed_addons(cls=None):
   """ Get a sorted list of installed addons, optionally filtered
   Args:
      cls: the class to filter by (ex: KodiPluginSource or KodiRepository)
   Return:
      A sorted list of addons instances
   """
   if cls is None:
      return sorted(installed_addons.values())
   else:
      return sorted([ a for a in installed_addons.values() if type(a) == cls ])


def install_from_local_zip(zip_file):
   """ Install (and load) any type of addons from a local zip file
   Args:
      zip_file (str): Full path of the zip to install
   Return:
      The new installed addon instance or None on errors
   """
   addon_id = os.path.basename(zip_file).split('-')[0]
   
   # TODO check errors
   with zipfile.ZipFile(zip_file, 'r') as z:
      z.extractall(base_addons_path)

   return load_single_addon(addon_id)


def uninstall_addon(addon):
   """ Uninstall (and unload) the given addon
   Args:
      addon: The addon instance to uninstall
   Return:
      True if success, False otherwise
   """
   try:
      shutil.rmtree(addon.installed_path)
   except:
      return False

   del installed_addons[addon.id]
   return True
   
   

class KodiAddonBase(object):
   """ Base class for any kodi addon: pluginsource, repository or python module """

   def __init__(self, xml_root, folder=None, repository=None):
      self._root = xml_root
      self._repo = repository
      self._folder = folder

      self._id = xml_root.get('id')
      self._name = xml_root.get('name')
      self._version = xml_root.get('version', '0.0.1')
      self._author = xml_root.get('provider-name')
      self._metadata = None # will be lazily parsed
      self._requires = None # will be lazily parsed

   def __str__(self):
      return '<{0.__class__.__name__} id={0.id} version={0.version}>'.format(self)

   def __lt__(self, other):
      return self.name.lower() < other.name.lower()

   def __gt__(self, other):
      return self.name.lower() > other.name.lower()

   @property
   def is_installed(self): # TODO rename to "installed"
      return self._folder is not None

   @property
   def disabled(self):
      """ Whenever the addon has been disabled (bool) """
      return self._id in ini.get_string_list('kodiaddons', 'disabled_addons')

   @disabled.setter
   def disabled(self, disable):
      """ Disable (True) or enable (False) the addon """
      L = ini.get_string_list('kodiaddons', 'disabled_addons')
      if disable == True and self._id not in L:
         L.append(self._id)
      elif disable == False and self._id in L:
         L.remove(self._id)
      else:
         return
      ini.set_string_list('kodiaddons', 'disabled_addons', L)
      
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

   def check_version(self, min_version):
      """ True if addon version >= min_version """
      return StrictVersion(self.version) >= StrictVersion(min_version)

   @property
   def author(self):
      """ ex: 'DaveMDS' """
      return self._author

   @property
   def icon(self):
      """ full path (or url) of the png icon """
      if self.is_installed:
         icon = os.path.join(self._folder, self.metadata.get('icon'))
         if os.path.exists(icon):
            return icon
      else:
         return os.path.join(self._repo.base_url, self._id, self.metadata.get('icon'))

   @property
   def fanart(self):
      """ full path (or url) of the jpg fanart (if available) """
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
         for elem in meta:
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


