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
import re
import copy
from xml.etree import ElementTree

from efl.evas import FILL_BOTH, EXPAND_BOTH
from efl import elementary as elm

from epymc import config_gui
from epymc import mainmenu
from epymc import utils
from epymc import ini
from epymc import gui
from epymc import browser

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.gui import EmcDialog, EmcYesNoDialog, EmcErrorDialog, \
    EmcInfoDialog, EmcImage, EmcNotify, EmcVKeyboard, EmcFileSelector

from .kodi_addon_base import load_installed_addons, load_single_addon, \
    get_installed_addon, get_installed_addons, install_from_local_zip, \
    uninstall_addon, base_pkgs_path, base_addons_path, \
    base_addons_data_path, base_temp_path, base_repos_path, KodiAddonBase
from .kodi_repository import KodiRepository
from .kodi_pluginsource import KodiPluginSource


def DBG(*args):
   print('KODI MODULE:', *args)
   pass

_mod = None


def notify_addon_installed(addon):
   txt = '<title>{0}</title><br>{1.name}<br>{1.version}'.format(
         _('Addon installed'), addon)
   EmcNotify(txt, icon=addon.icon)


kodi_tags_replace_map = {'[CR]': '<br>',
                         '[B]': '<b>', '[/B]': '</b>',
                         '[I]': '<em>', '[/I]': '</em>',
                         '[UPPERCASE]': '<title>', '[/UPPERCASE]': '</title>'}


def _replace_func(matchobj):
   tag = matchobj.group(0)
   return kodi_tags_replace_map.get(tag) or tag


def convert_kodi_tags(text):
   """ http://kodi.wiki/view/Label_Formatting """
   if text is not None:
      return re.sub('\[[A-Z//]*\]', _replace_func, text)


#  Browser ItemClass  ##########################################################
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
      return repo.icon

   def fanart_get(self, url, repo):
      return repo.fanart


class AddonItemClass(EmcItemClass):
   def item_selected(self, url, addon):
      if addon.is_installed:
         _mod.request_addon_page(url)
      else:
         AddonInfoPanel(addon)

   def label_get(self, url, addon):
      return addon.name.replace('&', '&amp;')

   def label_end_get(self, url, addon):
      provides = ' '.join(addon.provides)
      if addon.is_installed:
         return provides
      else:
         size = int(addon.metadata.get('size', 0))
         if size > 0:
            return provides + ' ' + utils.hum_size(size)

   def info_get(self, url, addon):
      txt = []
      title = addon.metadata.get('summary')
      desc = addon.metadata.get('description')
      disclaimer = addon.metadata.get('disclaimer')
      if title:
         txt.append('<title>{}</title>'.format(title))
      if desc:
         txt.append(desc)
      if disclaimer:
         txt.append('<br><small>{}</small>'.format(disclaimer))
      return '<br>'.join(txt)

   def icon_get(self, url, addon):
      return addon.icon

   def poster_get(self, url, addon):
      return addon.icon

   def fanart_get(self, url, addon):
      return addon.fanart


class StandardItemClass(EmcItemClass):
   def item_selected(self, url, listitem):
      if listitem['isFolder'] or url.startswith('plugin://'):
         _mod.request_addon_page(url, listitem)
      else:
         listitem.play()

   def label_get(self, url, listitem):
      return convert_kodi_tags(listitem.best_label)

   def icon_get(self, url, listitem):
      return listitem.best_icon

   def poster_get(self, url, listitem):
      return listitem.best_poster

   def fanart_get(self, url, listitem):
      return listitem.best_fanart

   def info_get(self, url, listitem):
      return convert_kodi_tags(listitem.best_info)


#  The epymc module  ###########################################################
class KodiAddonsModule(EmcModule):
   name = 'kodi_addons'
   label = _('Kodi Addons')
   icon = 'icon/evas'
   info = _('Use Kodi addons in epymc.')

   _browser = None
   _styles = ('List',)

   def __init__(self):
      global _mod

      DBG('Init module')

      _mod = self

      # create ini options if not exists (with defaults)
      ini.add_section('kodiaddons')
      ini.get('kodiaddons', 'disabled_addons', '')

      # create needed folders in ~/.config/epymc/kodi
      if not os.path.exists(base_pkgs_path):
         os.makedirs(base_pkgs_path)
      if not os.path.exists(base_temp_path):
         os.makedirs(base_temp_path)
      if not os.path.exists(base_addons_path):
         os.makedirs(base_addons_path)
      if not os.path.exists(base_addons_data_path):
         os.makedirs(base_addons_data_path)
      if not os.path.exists(base_repos_path):
         os.makedirs(base_repos_path)

      # load all available addons
      load_installed_addons()

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
      self._browser.page_add('kodi_addons://root', self.label, self._styles,
                             self.populate_root_page)
      self._browser.show()
      mainmenu.hide()

   def populate_root_page(self, browser, url):
      for addon in get_installed_addons(KodiPluginSource):
         if not addon.disabled:
            browser.item_add(AddonItemClass(), addon.root_url, addon)
      browser.item_add(GetMoreItemClass(), 'kodi_addons://manage', self)

   def request_addon_page(self, url, listitem=None):
      # addons can request pages from other addons!
      if url.startswith('plugin://'):
         addon_id = url[9:url.index('/', 10)]
      elif listitem:
         addon_id = listitem['addon_id']
      else:
         print("ERROR (this should never happend)")
         return

      addon = get_installed_addon(addon_id)
      addon.request_page(url, self._request_page_done_cb)

   def _request_page_done_cb(self, addon, page_url, listitems):
      if listitems:
         self._browser.page_add(page_url, addon.name, None,
                                self.populate_addon_page, listitems)

   def populate_addon_page(self, browser, url, listitems):
      for listitem in listitems:
         self._browser.item_add(StandardItemClass(), listitem['url'], listitem)

   def populate_repositories_page(self, browser, url):
      for repo in get_installed_addons(KodiRepository):
         if not repo.disabled:
            browser.item_add(RepoItemClass(), url + '/' + repo.id, repo)

   def populate_repository_page(self, browser, url, repo):
      repo.get_addons(self._repo_get_addons_done)
      # TODO show a dialog when downloading repo addons.xml !!

   def _repo_get_addons_done(self, repo, addons):
      L = [a for a in addons.values() if type(a) == KodiPluginSource]
      for addon in sorted(L):
         self._browser.item_add(AddonItemClass(), 'url', addon)  # TODO fix url

   #  Config Panel stuff  ######################################################
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
      def add_repos_page():
         browser.page_add('config://kodi_addon/repos', _('Repositories'),
                          None, self.populate_config_repos)

      def add_chans_page():
         browser.page_add('config://kodi_addon/chans', _('Channels'),
                          None, self.populate_config_chans)

      config_gui.standard_item_action_add(_('Repositories'), cb=add_repos_page)
      config_gui.standard_item_action_add(_('Channels'), cb=add_chans_page)

   def populate_config_repos(self, browser, url):
      for repo in get_installed_addons(KodiRepository):
         config_gui.standard_item_action_add(repo.name, repo.icon, r=repo,
                                             cb=lambda r:
                                             AddonInfoPanel(r))
      config_gui.standard_item_action_add(_('Add new repository from zip file'),
                                          icon='icon/plus',
                                          cb=lambda: AddonInstallDialog())

   def populate_config_chans(self, browser, url):
      for addon in get_installed_addons(KodiPluginSource):
         config_gui.standard_item_action_add(addon.name, addon.icon, a=addon,
                                             cb=lambda a:
                                             AddonInfoPanel(a))
      config_gui.standard_item_action_add(_('Add a new channel from zip file'),
                                          icon='icon/plus',
                                          cb=lambda: AddonInstallDialog())


#  Addon info panel  ###########################################################
class AddonInfoPanel(EmcDialog):
   def __init__(self, addon):
      self.addon = addon
      EmcDialog.__init__(self, style='panel', title=addon.name,
                         content=EmcImage(addon.icon),
                         text=addon.info_text_long)
      if addon.is_installed and not addon.preinstall:
         b = self.button_add(_('Options'),
                             selected_cb=lambda b: AddonSettingsPanel(addon))
         if addon.master_settings_file is None:
            b.disabled = True
         self.button_add(_('Enable') if addon.disabled else _('Disable'),
                         selected_cb=self.enable_disable_btn_cb,
                         cb_data=not addon.disabled)
         self.button_add(_('Update'), selected_cb=self.install_btn_cb)
         self.button_add(_('Uninstall'), selected_cb=self.uninstall_btn_cb)
      else:
         self.button_add(_('Install'), selected_cb=self.install_btn_cb)

   def enable_disable_btn_cb(self, btn, disable):
      self.addon.disabled = disable
      self.delete()
      browser.current_browser_refresh()

   def install_btn_cb(self, btn):
      self.delete()
      AddonInstallDialog(self.addon)

   def uninstall_btn_cb(self, btn):
      txt = '{0}<br><br><hilight>{1.name} v.{1.version}</hilight>'.format(
            _('Are you sure you want to delete this addon?'), self.addon)
      EmcYesNoDialog(_('Remove addon'), txt, self.uninstall_confirmed_cb)

   def uninstall_confirmed_cb(self, confirmed):
      if not confirmed:
         return
      if not uninstall_addon(self.addon):
         EmcErrorDialog(_('Cannot remove this addon'))
      else:
         self.delete()
         browser.current_browser_refresh()


#  Addon install panel  ########################################################
class AddonInstallDialog(EmcDialog):
   """ A dialog to perform all type of addon installation

   If installing from zip (local or remote) the addon will be installed
   in a temporary location and the user will be presented the addon info
   panel, that will let the user to perform the real installation.

   Addon dependencies are installed from the repo of the addon or from the
   kodi official repo.

   When install is completed the currently visible browser page will receive
   an hard refresh() request.

   Args:
      addon: Can be of different type:
         (KodiAddon instance): to install from an already loaded addon,
                               usually from a repo
         (str - local path): to install from a zip file
         (str - url): to install a remote zip
         (None): will ask the user to type an url or choose a file
      cb: Function to call when installation is complete
         signature: func((success, **kargs)
      **kargs: Any other keyword arguments will be passed back in cb
   """

   zipfile_regexp = '[a-z0-9.-]+-[0-9]+\.[0-9]+\.[0-9]+\.zip'

   def __init__(self, addon=None):
      EmcDialog.__init__(self, style='minimal', text='',
                         title=_('Addon installation'))

      # ask a zip or an url
      if addon is None:
         self.ask_for_a_zip()

      # or install from repo (or from preinstalled zip)
      elif isinstance(addon, KodiAddonBase):
         self.install_addon(addon)

      elif isinstance(addon, str) and addon.lower().endswith('.zip'):
         # or pre-install from url
         if asson.startswith(('http://', 'https://')):
            self.preinstall_from_url(addon)
         # or pre-install from zip
         elif os.path.exists(addon):
            self.preinstall_from_zip(addon)

   ### 1. Ask for a local or remote zip
   def ask_for_a_zip(self):
      txt = '{}<br>{}'.format(
            _('Addon can be manually installed from a zip file.'),
            _('Choose a zip file on your device or type the URL of a '
              'remote zip resource.'))
      self.text_set(txt)
      self.button_add(_('Type the URL'), selected_cb=self._ask_url_btn_cb)
      self.button_add(_('Choose a file'), selected_cb=self._ask_file_btn_cb)

   def _ask_url_btn_cb(self, btn):
      EmcVKeyboard(title=_('Type the URL'),
                   accept_cb=lambda keyb, url: self.preinstall_from_url(url))

   def _ask_file_btn_cb(self, btn):
      EmcFileSelector(title=_('Select a zip file'), file_filter='*.zip',
                      done_cb=lambda path: self.preinstall_from_zip(path))

   ### 2. Download a given url
   def preinstall_from_url(self, url):
      zip_name = os.path.basename(url)
      if re.fullmatch(self.zipfile_regexp, zip_name) is None:
         self.delete()
         EmcErrorDialog(_('The given URL is not valid'))
         return

      self.buttons_clear()
      self.progress_show()
      self.text_set(_('Download in progress, please wait.'))

      dest = os.path.join(base_pkgs_path, zip_name)
      utils.download_url_async(url, dest,
                               progress_cb=self._url_progress_cb,
                               complete_cb=self._url_done_cb)

   def _url_progress_cb(self, dest, total, done):
      if total and done:
         self.progress_set(done / total)

   def _url_done_cb(self, dest, status):
      if status != 200:
         self.delete()
         EmcErrorDialog(_('Download failed'))
      else:
         self.preinstall_from_zip(dest)

   ### 3. Open the zip in tmp to show the info dialog
   def preinstall_from_zip(self, zip_file):
      self.delete()
      zip_file = utils.url2path(zip_file)

      if re.fullmatch(self.zipfile_regexp, os.path.basename(zip_file)) is None:
         EmcErrorDialog(_('The given zip file is not valid'))
         return

      addon = install_from_local_zip(zip_file, preinstall=True)
      if addon is None:
         EmcErrorDialog(_('Addon installation failed'))
         return

      AddonInfoPanel(addon)

   ### 4. Real install from a know KodiAddon instance
   def _get_dependent_addons(self, addon, L=None):
      DBG("Cheking deps for:", addon)

      if L is None:
         L = [addon]

      for dep_id, dep_version in addon.requires:
         if dep_id == 'xbmc.addon':
            continue

         # is dep already installed ?
         inst = get_installed_addon(dep_id)
         if inst and inst.check_version(dep_version):
            continue

         # is dep present in addon repo?
         available = None
         if addon.repository:
            available = addon.repository.addon_available(dep_id, dep_version)

         # or in default repo?
         if not available:
            repo = get_installed_addon('repository.kodi_official')
            print("try in kodi", repo)
            if repo:
               available = repo.addon_available(dep_id, dep_version)
               print("try in kodi2 ", available)

         if not available:
            raise RuntimeError(dep_id)

         if available not in L:
            L.append(available)
            # recursively check dependencies
            self._get_dependent_addons(available, L)

      return L

   def install_addon(self, addon):
      # is addon already installed ?
      inst = get_installed_addon(addon.id)
      if inst and inst.check_version(addon.version):
         self.delete()
         EmcInfoDialog(_('Addon already installed'))
         # TODO a dialog to force the installation?
         return

      # recursively build dependencies list (base addon included)
      try:
         needed_addons = self._get_dependent_addons(addon)
      except RuntimeError as missing_addon_id:
         self.delete()
         EmcErrorDialog('{}<br><br><hilight>{}</hilight>'.format(
                        _('Cannot find the addon'), missing_addon_id))
         return

      # try to calculate total size from addons metadata
      total_size = 0
      for a in needed_addons:
         total_size += int(a.metadata.get('size', 0))

      # TODO ask a confirmation if deps are requireed?

      # setup stuff for the progressbar
      self._needed_addons = needed_addons
      self._total_download_size = total_size or 1
      self._total_downloaded = 1

      # prepare the dialog
      self.text_set(_('Installing addons, please wait...'))
      self.progress_show()
      self.progress_set(0)

      # start downloading
      self._download_next_addon()

   def _download_next_addon(self):
      try:
         addon = self._needed_addons.pop()
      except IndexError:  # all addons done
         self._install_completed()
         return

      zip_name = '{0}-{1}.zip'.format(addon.id, addon.version)
      if addon.preinstall:
         zip_exist = addon.preinstall_zipfile
         self._download_complete_cb(zip_exist, 200, addon)
      else:
         zip_url = '/'.join((addon.repository.base_url, addon.id, zip_name))
         zip_dest = os.path.join(base_pkgs_path, zip_name)
         utils.download_url_async(zip_url, zip_dest, addon=addon,
                                  progress_cb=self._download_progress_cb,
                                  complete_cb=self._download_complete_cb)

   def _download_progress_cb(self, dest, tot, done, addon):
      done += self._total_downloaded
      self.progress_set(done / self._total_download_size)

   def _download_complete_cb(self, dest, status, addon):
      if status != 200:
         self.delete()
         EmcErrorDialog('{}<br><br><hilight>{}</hilight>'.format(
                        _('Addon download failed'), addon.id))
         return

      self._total_downloaded += int(addon.metadata.get('size', 0))

      addon = install_from_local_zip(dest)
      if addon is None:
         self.delete()
         EmcErrorDialog('{}<br><br><hilight>{}</hilight>'.format(
                        _('Addon installation failed'), addon.id))
      else:
         notify_addon_installed(addon)
         self._download_next_addon()

   ### 5. All done
   def _install_completed(self):
      self.delete()
      browser.current_browser_refresh(hard=True)

#  Addon options panel  ########################################################
class AddonSettingsPanel(EmcDialog):
   def __init__(self, addon):

      # work a local copy of the addon settings (so we can cancel or save)
      self.settings = copy.deepcopy(addon.settings)
      self.addon = addon

      # create the genlist and the item classes
      self._gl = elm.Genlist(gui.layout, style='dialog', homogeneous=True,
                             focus_allow=False, mode=elm.ELM_LIST_COMPRESS,
                             size_hint_align=FILL_BOTH,
                             size_hint_weight=EXPAND_BOTH)
      self._gl.callback_realized_add(self._gl_item_realized_cb)
      self._gl.callback_clicked_double_add(self.modify_selected_item)

      self._itc = elm.GenlistItemClass(item_style='default',
                                       text_get_func=self._gl_text_get,
                                       content_get_func=self._gl_content_get)
      self._itc_g = elm.GenlistItemClass(item_style='group_index',
                                         text_get_func=self._gl_group_text_get)

      # create the panel dialog
      EmcDialog.__init__(self, style='panel', title=addon.name,
                         content=self._gl)
      self.button_add(_('Modify'), selected_cb=self.modify_selected_item)
      self.button_add(_('Save'), selected_cb=self.save_settings)
      self.button_add(_('Cancel'), selected_cb=lambda b: self.delete())
      self.button_add(_('Defaults'), selected_cb=self.default_values)

      # populate the list from the addon master xml settings file
      self.build_list_from_xml()

   def _gl_item_realized_cb(self, gl, item):
      # force show/hide of icons, otherwise the genlist cache mechanism will
      # remember icons from previus usage of the item
      item.signal_emit('end,show' if item.part_content_get('elm.swallow.end')
                       else 'end,hide', 'emc')

   def _gl_text_get(self, obj, part, xml_elem):
      setting_id = xml_elem.get('id')
      if part == 'elm.text.main':
         return self.addon.localized_string(xml_elem.get('label'))

      if part == 'elm.text.end':
         typ = xml_elem.get('type')

         if typ == 'enum':
            val_idx = int(self.settings.get(setting_id, '0'))
            # direct labels
            labels = xml_elem.get('values')
            if labels is not None:
               return labels.split('|')[val_idx]
            # or translated labels
            label = xml_elem.get('lvalues').split('|')[val_idx]
            return self.addon.localized_string(label)

         elif typ != 'bool':
            return self.settings.get(setting_id, '')

   def _gl_content_get(self, obj, part, xml_elem):
      if part == 'elm.swallow.end' and xml_elem.get('type') == 'bool':
         setting_id = xml_elem.get('id')
         if self.settings.get(setting_id) == 'true':
            return gui.EmcImage('icon/check_on')
         else:
            return gui.EmcImage('icon/check_off')

   def _gl_group_text_get(self, obj, part, label):
      return label

   def build_list_from_xml(self):
      self._root = ElementTree.parse(self.addon.master_settings_file).getroot()
      categories = list(self._root.iter('category')) or [None]
      for cat_elem in categories:
         if cat_elem is not None:
            label = self.addon.localized_string(cat_elem.get('label'))
            cat_it = self._gl.item_append(self._itc_g, label,
                                          flags=elm.ELM_GENLIST_ITEM_GROUP)
            cat_it.select_mode = elm.ELM_OBJECT_SELECT_MODE_DISPLAY_ONLY
            elements = cat_elem.iter('setting')
         else:
            cat_it = None
            elements = self._root.iter('setting')

         for elem in elements:
            if elem.get('type') in ('sep', 'lsep'):
               # TODO separators
               continue

            if elem.get('visible', 'true') == 'false':
               # TODO this can be a conditional
               continue

            it = self._gl.item_append(self._itc, elem, cat_it)
            if self._gl.selected_item is None:
               it.selected = True

   def save_settings(self, *args):
      self.addon.settings = self.settings
      self.delete()

   def default_values(self, *args):
      for elem in self._root.iter('setting'):
         key, val = elem.get('id'), elem.get('default')
         if key and val:
            self.settings[key] = val
      self._gl.realized_items_update()

   def modify_selected_item(self, *args):
      item = self._gl.selected_item
      xml_elem = item.data_get()
      typ = xml_elem.get('type')
      setting_id = xml_elem.get('id')
      val = self.settings.get(setting_id, '')

      if typ == 'bool':
         self.settings[setting_id] = 'true' if val == 'false' else 'false'
         item.update()

      elif typ == 'slider':
         rng = xml_elem.get('range', '1,1,100').split(',')
         opt = xml_elem.get('option', 'int')
         if opt == 'float':
            rng = list(map(float, rng))
            val = float(val)
            fmt = '%1.3f'
         else:
            rng = list(map(int, rng))
            val = int(val)
            fmt = '%1.0f'
         if len(rng) == 3:
            min_val, step, max_val = rng
         else:
            min_val, max_val = rng
            step = 1
         gui.EmcSliderDialog(setting_id, self._slider_cb, val,
                             min_val, max_val, step, fmt,
                             setting_id=setting_id,
                             option=opt)

      elif typ == 'enum':
         values = xml_elem.get('values')
         if values is None:
            values = xml_elem.get('lvalues').split('|')
            values = list(map(self.addon.localized_string, values))
         else:
            values = values.split('|')

         gui.EmcSelectDialog(setting_id, values, self._enum_select_cb, int(val),
                             setting_id=setting_id)

      elif typ in ('select', 'enum', 'labelenum'):
         values = xml_elem.get('values')
         if values is None:
            values = xml_elem.get('lvalues').split('|')
            values = list(map(self.addon.localized_string, values))
         else:
            values = values.split('|')
         if typ == 'enum':
            gui.EmcSelectDialog(setting_id, values, self._enum_select_cb,
                                int(val), setting_id=setting_id)
         else:
            gui.EmcSelectDialog(setting_id, values, self._enum_select_cb2,
                                setting_id=setting_id)

      elif typ in ('text', 'number', 'ipaddress'):
         # TODO number/ipaddress special keyb
         EmcVKeyboard(title=setting_id, text=val, accept_cb=self._vkeyb_cb,
                      user_data=setting_id)

      else:
         DBG('Unsupported type: "{}"'.format(typ))

   def _vkeyb_cb(self, vkeyb, new_val, setting_id):
      self.settings[setting_id] = new_val
      self._gl.selected_item.update()

   def _slider_cb(self, new_val, setting_id, option):
      if new_val is not None:
         if option != 'float':
            new_val = int(new_val)
         self.settings[setting_id] = str(new_val)
         self._gl.selected_item.update()

   def _enum_select_cb(self, val_idx, val, setting_id):
      self.settings[setting_id] = str(val_idx)
      self._gl.selected_item.update()

   def _enum_select_cb2(self, val_idx, val, setting_id):
      self.settings[setting_id] = val
      self._gl.selected_item.update()

