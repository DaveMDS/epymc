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
import io
import locale
import zipfile
import shutil
import polib
from xml.etree import ElementTree
from distutils.version import StrictVersion

from efl.elementary import utf8_to_markup

from epymc import utils
from epymc import ini


def DBG(*args):
   print('KODI ADDON:', *args)
   pass


base_kodi_path = os.path.join(utils.user_conf_dir, 'kodi')
base_addons_path = os.path.join(base_kodi_path, 'addons')
base_addons_data_path = os.path.join(base_kodi_path, 'userdata', 'addon_data')
base_pkgs_path = os.path.join(base_kodi_path, 'packages')
base_temp_path = os.path.join(base_kodi_path, 'temp')
base_repos_path = os.path.join(base_kodi_path, 'repos')
sys_addons_path = os.path.join(os.path.dirname(__file__), 'addons')

installed_addons = {}  # key: addon_in  val: KodiAddon instance


def safe_po_parser(pofile):
   """ Remove unwanted comments from a po file before passing it to polib
   Kodi po files use non-standard comment lines, like:

   #YouTube
   #empty strings from id 30121 to 30199

   So we need to strip those lines that otherwise will make polib parse fail
   """
   fhandle = io.open(pofile, 'rt', encoding='utf-8')
   lines = [line for line in fhandle if line[0] != '#']
   fhandle.close()
   return polib.pofile(''.join(lines))


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
      return sorted([a for a in installed_addons.values() if type(a) == cls])


def install_from_local_zip(zip_file, preinstall=False):
   """ Install (and load if preinstall is False) any type of addons
   from a local zip file

   Args:
      zip_file (str): Full path of the zip to install
      preinstall (bool): If True addon will be installed in a temp folder and
                         will not be included in the list of addons (loaded)
   Return:
      The new addon instance or None on errors
   """
   addon_id = os.path.basename(zip_file)
   addon_id = addon_id[0:addon_id.rindex('-')]
   dest_folder = base_temp_path if preinstall else base_addons_path

   try:
      with zipfile.ZipFile(zip_file, 'r') as zf:
         zf.extractall(dest_folder)
   except zipfile.BadZipfile:
      return None

   if preinstall:
      xml_path = os.path.join(base_temp_path, addon_id, 'addon.xml')
      addon = addon_factory(xml_path)
      addon.preinstall = True
      addon.preinstall_zipfile = zip_file
      return addon
   else:
      return load_single_addon(addon_id)


def uninstall_addon(addon):
   """ Uninstall (and unload) the given addon
   Args:
      addon: The addon instance to uninstall
   Return:
      True if success, False otherwise
   """
   try:
      shutil.rmtree(addon.path)
   except:
      return False

   del installed_addons[addon.id]
   return True


class KodiAddonBase(object):
   """ Base class for any type of kodi addon """

   def __init__(self, xml_root, folder=None, repository=None):
      self._root = xml_root
      self._repo = repository
      self._folder = folder

      self._id = xml_root.get('id')
      self._name = xml_root.get('name')
      self._version = xml_root.get('version', '0.0.1')
      self._author = xml_root.get('provider-name')
      self._preinstall = False
      self._preinstall_zipfile = None
      self._metadata = None  # will be lazily parsed
      self._requires = None  # will be lazily parsed
      self._settings = None  # will be lazily loaded
      self._localize = None  # will be lazily loaded

   def __repr__(self):
      return '<{0.__class__.__name__} id={0.id} v={0.version}>'.format(self)

   def __lt__(self, other):
      return self.name.lower() < other.name.lower()

   def __gt__(self, other):
      return self.name.lower() > other.name.lower()

   @property
   def is_installed(self):  # TODO rename to "installed"
      """ Whenever the addon is already installed """
      return self._folder is not None

   @property
   def preinstall(self):
      """ True when we are in the preinstall phase """
      return self._preinstall

   @preinstall.setter
   def preinstall(self, value):
      self._preinstall = value

   @property
   def preinstall_zipfile(self):
      """ In pre-install mode this is the source zip file """
      return self._preinstall_zipfile

   @preinstall_zipfile.setter
   def preinstall_zipfile(self, value):
      self._preinstall_zipfile = value

   @property
   def disabled(self):
      """ Whenever the addon has been disabled (bool) """
      return self._id in ini.get_string_list('kodiaddons', 'disabled_addons')

   @disabled.setter
   def disabled(self, disable):
      """ Disable (True) or enable (False) the addon """
      L = ini.get_string_list('kodiaddons', 'disabled_addons')
      if disable is True and self._id not in L:
         L.append(self._id)
      elif disable is False and self._id in L:
         L.remove(self._id)
      else:
         return
      ini.set_string_list('kodiaddons', 'disabled_addons', L)

   @property
   def path(self):
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
      icon = self.metadata.get('icon')
      if icon:
         if self.is_installed:
            icon = os.path.join(self._folder, icon)
            if os.path.exists(icon):
               return icon
         else:
            return os.path.join(self._repo.base_url, self._id, icon)

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
         for require in self._root.find('requires') or []:
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
         if meta is None:
            return self._metadata
         for elem in meta:
            if elem.tag == 'assets':
               for ass_elem in elem:
                  if ass_elem.tag == 'screenshot':
                     self._metadata['screenshots'].append(ass_elem.text)
                  else:  # 'icon' or 'fanart'
                     self._metadata[ass_elem.tag] = ass_elem.text
            else:
               lang = elem.get('lang', 'en_GB')
               if lang == syslang or lang == syslang[:2] or lang[:2] == 'en':
                  t = elem.text
                  if t:
                      # TODO better replace
                     self._metadata[elem.tag] = t.strip().replace('[CR]', '\n')

         # old style assets
         if not self._metadata.get('icon'):
            self._metadata['icon'] = 'icon.png'
         if not self._metadata.get('fanart'):
            if self._metadata.get('nofanart') != 'true':
               self._metadata['fanart'] = 'fanart.jpg'

      return self._metadata

   @property
   def changelog(self):
      return self.metadata.get('news')

   @property
   def description(self):
      return self.metadata.get('description')

   @property
   def disclaimer(self):
      return self.metadata.get('disclaimer')

   @property
   def summary(self):
      return self.metadata.get('summary')

   @property
   def info_text_short(self):
      pass  # TODO

   @property
   def info_text_long(self):
      txt = []

      summary = self.metadata.get('summary')
      if summary:
         txt.append('<big>{}</big><br>'.format(utf8_to_markup(summary)))

      mapp = (('author', _('Author')),
              ('version', _('Version')),
              ('language', _('Content language')),
              ('license', _('License')),
              ('description', _('Description')),
              ('disclaimer', _('Disclaimer')),
              ('news', _('News')))

      for key, label in mapp:
         val = self.metadata.get(key) or getattr(self, key, None)
         if val:
            if key == 'language':
               val = ', '.join(val.split())
            txt.append('<name>{}:</name> <value>{}</value>'.format(
                       label, utf8_to_markup(val)))

      return '<br>'.join(txt)

   # # #  Settings stuff  # # # # # # # # # # # # # # # # # # # # # # # # # # #
   @property
   def settings(self):
      """ A dict with all the actual user settings values """
      if self._settings is None:
         self.settings_load()
      return self._settings

   @settings.setter
   def settings(self, settings_dict):
      self._settings = settings_dict
      self.settings_save()

   @property
   def master_settings_file(self):
      """ The main settings xml file path, None if addon have no options """
      path = os.path.join(self.path, 'resources', 'settings.xml')
      return path if os.path.exists(path) else None

   @property
   def user_settings_file(self):
      """ The user settings xml file path """
      return os.path.join(base_addons_data_path, self.id, 'settings.xml')

   def settings_create_defaults(self):
      """ Create default user settings, in _settings dict and user xml file """
      master_xml_file = self.master_settings_file

      self._settings = {}

      # read keys and defaults from master xml file (if exists)
      if master_xml_file is not None:
         DBG('Creating default settings from:', master_xml_file)
         root = ElementTree.parse(master_xml_file).getroot()
         for elem in root.iter('setting'):
            if elem.get('id'):
               self._settings[elem.get('id')] = elem.get('default', '')
      else:
         DBG('Creating empty settings for:', self.id)
      # and save to user settings xml file
      self.settings_save()

   def settings_load(self):
      """ Load settings from the user xml file, create defaults if not exists"""
      xml_file = self.user_settings_file

      if not os.path.exists(xml_file):
         self.settings_create_defaults()
      else:
         DBG('Loading settings from:', xml_file)
         self._settings = {}
         root = ElementTree.parse(xml_file).getroot()
         for elem in root.iter('setting'):
            self._settings[elem.get('id')] = elem.get('value', '')

   def settings_save(self):
      """ Save current settings to the user xml file """
      user_xml_file = self.user_settings_file
      DBG('Saving settings to:', user_xml_file)

      # build the xml tree
      root = ElementTree.Element('settings')
      for key, val in sorted(self._settings.items()):
         ElementTree.SubElement(root, 'setting', {'id': key, 'value': val})

      # prettify the tree
      from xml.dom import minidom
      rough_str = ElementTree.tostring(root)  # , 'utf-8')
      reparsed = minidom.parseString(rough_str)
      pretty_str = reparsed.toprettyxml(indent='    ')

      # save to user file
      os.makedirs(os.path.dirname(user_xml_file), exist_ok=True)
      with open(user_xml_file, 'w') as f:
         f.write(pretty_str)

   # # #  Translation stuff   # # # # # # # # # # # # # # # # # # # # # # # # #
   @property
   def localized(self):
      """ Dict with localized strings (key: '#30000'  val: 'local. string') """
      if self._localize is None:
         self._search_and_parse_localization_file()
      return self._localize

   def localized_string(self, string_id):
      """ Get a localized string, string_id: 30000 or '30000' or '#30000' """
      if isinstance(string_id, int):
         string_id = str(string_id)
      if not string_id.startswith('#'):
         string_id = '#' + string_id
      return self.localized.get(string_id, '')

   def _search_and_parse_localization_file(self):
      # TODO also support: "en_US" (only "en" atm)
      lang, encoding = locale.getdefaultlocale()
      lname = utils.iso639_1_to_name(lang[:2], 'English') if lang else 'English'

      # search a po file
      for lang in (lname, 'English'):
         po_file = os.path.join(self.path, 'resources', 'language', lang,
                                'strings.po')
         try:
            po = safe_po_parser(po_file)
         except IOError:
            continue
         else:
            self._localize = self._extract_strings_from_po(po)
            return

      # or seach an xml file
      for lang in (lname, 'English'):
         xml_file = os.path.join(self.path, 'resources', 'language', lang,
                                 'strings.xml')
         if not os.path.exists(xml_file):
            continue
         # try different encoding (if encoding not provided in xml)
         for enc in (None, 'utf-8', 'iso-8859-1'):
            parser = ElementTree.XMLParser(encoding=enc)
            try:
               et = ElementTree.parse(xml_file, parser=parser)
            except ElementTree.ParseError:
               continue
            else:
               self._localize = self._extract_strings_from_xml(et)
               return

      # no language file available, do not search again the next time
      self._localize = {}

   def _extract_strings_from_po(self, po):
      return {i.msgctxt: i.msgstr or i.msgid for i in po}

   def _extract_strings_from_xml(self, et):
      return {'#' + e.get('id'): e.text for e in et.getroot()}
