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
import zipfile
from lxml import etree
from operator import attrgetter

from efl import ecore
from efl.elementary import utf8_to_markup

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.utils as utils
import epymc.gui as gui
# import epymc.ini as ini
import epymc.config_gui as config_gui

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.gui import EmcDialog, EmcImage

from .kodi_repository import KodiRepository, load_available_repos
from .kodi_pluginsource import KodiAddon, load_available_addons



def DBG(*args):
   print('KODI ADDONS:', *args)
   pass



_mod = None


class AddonInfoPanel(EmcDialog):
   def __init__(self, addon):
      self.addon = addon
      EmcDialog.__init__(self, style='panel',
                         title=addon.name + ' v' + addon.version,
                         content=EmcImage(addon.icon),
                         text=addon.info_text_long)
      self.button_add('Options').disabled = True
      self.button_add('Install/Update',  selected_cb=self.install_btn_cb)
      self.button_add('Uninstall').disabled = True

   def install_btn_cb(self, btn):
      addon = self.addon
      repo = self.addon.repository

      if is_addon_installed(addon.id, addon.version):
         EmcDialog(style='info', text='already installed') # TODO better dialog
         return

      # addon package
      print("INSTALL:", addon.id, repo)
      zip_url = '{0}/{1}/{1}-{2}.zip'.format(repo.base_url, addon.id, addon.version)
      needed_pkgs = [zip_url]

      # dependencies packages
      for id, min_version in addon.requires:
         if is_addon_installed(id, min_version):
            continue

         repo_version = repo.addon_available(id, min_version)
         if repo_version is not None:
            zip_url = '{0}/{1}/{1}-{2}.zip'.format(repo.base_url, id, repo_version)
            needed_pkgs.append(zip_url)
            continue

         EmcDialog(style='error', text='missing pkg in repo') # TODO better dialog
         return

      print("REQUIRES:", addon.requires)
      print(needed_pkgs)
      self._to_download_pkgs = needed_pkgs
      self._to_install_pkgs = []
      self.download_next_package()
      EmcDialog(style='minimal', text='installing...', spinner=True) # TODO better dialog

   def download_next_package(self):
      try:
         pkg = self._to_download_pkgs.pop()
      except IndexError: # all downloads done
         self.install_next_package()
         return

      fname = os.path.basename(pkg)
      dest = os.path.join(utils.user_conf_dir, 'kodi', 'packages', fname)
      utils.download_url_async(pkg, dest, complete_cb=self.download_complete_cb)
      
   def download_complete_cb(self, dest, status):
      if status == 200:
         self._to_install_pkgs.append(dest)
         self.download_next_package()
      else:
         EmcDialog(style='error', text='download failed')  # TODO better dialog

   def install_next_package(self):
      try:
         pkg = self._to_install_pkgs.pop(0)
      except IndexError: # all installations done
         self.install_completed()
         return
      print("INSTALL", pkg)

      dest_path = os.path.join(utils.user_conf_dir, 'kodi', 'addons')
      with zipfile.ZipFile(pkg, 'r') as z: # TODO make this async?
         z.extractall(dest_path)

      self.install_next_package()

   def install_completed(self):
      print("ALL DONE \o/")




def is_addon_installed(id, min_version):
   for addon in _mod._addons:
      # TODO ver < ver
      if addon.id == id and addon.version == min_version:
         return True
   return False



class RepoInfoPanel(EmcDialog):
   def __init__(self, repo):
      self._repo = repo
      EmcDialog.__init__(self, style='panel',
                         title=_('Addons Repository'),
                         content=EmcImage(repo.icon),
                         text=repo.info_text_long)
      self.button_add('Enable/Disable').disabled = True
      self.button_add('Uninstall').disabled = True


class GetMoreItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('kodi_addons://repos', _('Get more'), None,
                             mod.populate_repositories_page)

   def label_get(self, url, mod):
      return _('Get more channels')

   def info_get(self, url, mod):
      return _('Install, remove or update addons')

   def icon_get(self, url, mod):
      return 'icon/plus'

class RepoItemClass(EmcItemClass):
   def item_selected(self, url, repo):
      _mod._browser.page_add(url, repo.name, None,
                             _mod.populate_repository_page, repo)

   def label_get(self, url, repo):
      return repo.name

   # def info_get(self, url, repo):
      # return _('Install, remove or update addons')

   def icon_get(self, url, repo):
      return repo.icon

   def poster_get(self, url, repo):
      return addon.icon

   def fanart_get(self, url, repo):
      return addon.fanart

class AddonItemClass(EmcItemClass):
   def item_selected(self, url, addon):
      if addon.is_installed:
         addon.request_page(None, _mod._browser)
      else:
         AddonInfoPanel(addon)

   def label_get(self, url, addon):
      return addon.name.replace('&', '&amp;')

   def label_end_get(self, url, addon):
      return ' '.join(addon.provides)

   def info_get(self, url, addon):
      txt = []
      title = addon.metadata.get('summary')
      desc = addon.metadata.get('description')
      disclaimer = addon.metadata.get('disclaimer')
      if title: txt.append('<title>{}</title>'.format(title))
      if desc: txt.append(desc)
      if disclaimer: txt.append('<br><small>{}</small>'.format(disclaimer))
      return '<br>'.join(txt)

   def icon_get(self, url, addon):
      return addon.icon

   def poster_get(self, url, addon):
      return addon.icon

   def fanart_get(self, url, addon):
      return addon.fanart


class KodiAddonsModule(EmcModule):
   name = 'kodi_addons'
   label = _('Kodi Addons')
   icon = 'icon/evas'
   info = _('Use Kodi addons in epymc.')

   _browser = None
   _styles = ('List',)
   _addons = []
   _repos = []


   def __init__(self):
      global _mod
      
      DBG('Init module')

      _mod = self

      # create ini options if not exists (with defaults)
      # ini.add_section('videochannels')
      # ini.get('videochannels', 'autoupdate_ytdl', 'True')

      self._repos = load_available_repos()
      self._addons = load_available_addons()
      # r = KodiRepository('http://mirrors.kodi.tv/addons/krypton')
      # print(r)
      # self._repos.append(r)

      # add an item in the mainmenu
      mainmenu.item_add(self.name, 15, self.label, self.icon, self.mainmenu_cb)

      # add an entry in the config gui
      config_gui.root_item_add(self.name, 10, self.label,
                               icon=self.icon, callback=self.config_panel_cb)

      # create the browser instance
      self._browser = EmcBrowser(self.label, icon=self.icon)

   def __shutdown__(self):
      DBG('Shutdown module')
      mainmenu.item_del(self.name)
      config_gui.root_item_del(self.name)
      self._browser.delete()


   def mainmenu_cb(self):

      # TODO create folders in .config/epymc/kodi (or in __init__)

      # if not self._addons:
         # self._addons = load_available_addons()

      self._browser.page_add('kodi_addons://root', self.label, self._styles,
                             self.populate_root_page)
      self._browser.show()
      mainmenu.hide()

   def populate_root_page(self, browser, url):
   
      for addon in sorted(self._addons, key=attrgetter('name')):
         browser.item_add(AddonItemClass(), None, addon)

      browser.item_add(GetMoreItemClass(), 'kodi_addons://manage', self)
   
      # self.current_addon = KodiAddon()
      
      # if not self._sources:
         # self.build_sources_list()
      # for ch in self._sources:
         # self._browser.item_add(ChannelItemClass(), ch['name'], ch)
      # self._browser.item_add(DownloadItemClass(), None)


   def populate_repositories_page(self, browser, url):
      for repo in self._repos:
         browser.item_add(RepoItemClass(), url+'/repo_name', repo) # TODO fix repo_name

   def populate_repository_page(self, browser, url, repo):
      repo.get_addons(self._repo_get_addons_done)

   def _repo_get_addons_done(self, repo, addons):
      print("HEYAAA", repo)
      for addon in sorted(addons.values()): # TODO fix order
         self._browser.item_add(AddonItemClass(), 'url', addon) # TODO fix url
      # for addon in sorted(addons, key=attrgetter('name')):
         # self._browser.item_add(AddonItemClass(), 'url', addon)


   ###### Config Panel stuff ##################################################
   def config_panel_cb(self):
      browser = config_gui.browser_get()
      browser.page_add('config://kodi_addon/', self.label, None,
                       self.populate_config_root)
      """
      repositories
         repo1  -> RepoPanel
         repo2  -> RepoPanel
         ...
         + add new repo -> RepoWizard (from url or zip)
      addons
         addon1 -> AddonPanel
         addon2 -> AddonPanel
         ...
         + add new addon -> AddonWizard (from url or zip)
      show addons in activities
      show kodi_addons in main menu
      automatically update installed addons
      automatically update installed repos
      """

   def populate_config_root(self, browser, url):
      print("ROOT")
      def add_repos_page():
         browser.page_add('config://kodi_addon/repos', _('Repositories'),
                          None, self.populate_config_repos)
      def add_addons_page():
         browser.page_add('config://kodi_addon/addons', _('Addons'),
                          None, self.populate_config_addons)

      config_gui.standard_item_action_add(_('Repositories'), icon=None,
                                          info=None, cb=add_repos_page)
      config_gui.standard_item_action_add(_('Addons'), icon=None,
                                          info=None, cb=add_addons_page)

   def populate_config_repos(self, browser, url):
      print("REPOS")
      for repo in self._repos:
         config_gui.standard_item_action_add(repo.name, repo.icon, info=None,
                                             cb=lambda r: RepoInfoPanel(r),
                                             r=repo)
      config_gui.standard_item_action_add(_('Add a new repo'), icon='icon/plus',
                                          info=None, cb=self.new_repo_wizard)

   def new_repo_wizard(self):
      EmcDialog(style='minimal', text='repo wizard')

   def populate_config_addons(self, browser, url):
      print("ADDONS")
      for addon in self._addons:
         config_gui.standard_item_action_add(addon.name, addon.icon, info=None,
                                             cb=lambda a: AddonInfoPanel(a),
                                             a=addon)
      config_gui.standard_item_action_add(_('Add a new addon'), icon='icon/plus',
                                          info=None,
                                          cb=self.new_addon_wizard)

   def new_addon_wizard(self):
      EmcDialog(style='minimal', text='addon wizard')
