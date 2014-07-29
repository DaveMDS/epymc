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

import os
import xml.dom.minidom
import operator

from efl import evas, ecore, elementary

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.gui import EmcDialog, EmcRemoteImage
from epymc.utils import EmcExec
import epymc.mainmenu as mainmenu
import epymc.browser as browser
import epymc.utils as utils
import epymc.gui as gui
import epymc.ini as ini


def DBG(msg):
   print('MAME: ' + str(msg))
   pass

MAME_EXE = 'mame'
_mod = None


class MyGamesItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('mame://mygames', 'My Games', None,
                            mod.populate_mygames_page)

   def label_get(self, url, mod):
      return _('My Games')

   def label_end_get(self, url, mod):
      return str(mod.count_roms())


class AllGamesItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('mame://allgames', 'All Games', None,
                            mod.populate_allgames_page)

   def label_get(self, url, mod):
      return _('All Games')

   def label_end_get(self, url, mod):
      return str(len(mod._games))


class FavoriteGamesItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('mame://favgames', 'Favorite Games', None,
                            mod.populate_favgames_page)

   def label_get(self, url, mod):
      return _('Favorite Games')

   def label_end_get(self, url, mod):
      return str(len(mod._favorites))


class CategoriesItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('mame://cats', 'Categories', None,
                            mod.populate_categories_page)

   def label_get(self, url, mod):
      return _('Categories')


class GameItemClass(EmcItemClass):
   def item_selected(self, url, game):
     game.dialog_show()

   def label_get(self, url, game):
      return game.name

   # Short info disabled to avoid a nasty BUG:
   #   the game class do this async if it has not yet fetched the game info
   #   using the mame executable (EmcExe). When the exe is done it call the
   #   browser refresh() function, that will trigger another download of the
   #   poster...while the download of the poster is still in progress...
   # def info_get(self, url, game):
      # return game.short_info_get()

   def icon_get(self, url, game):
      if url in _mod._favorites:
         return 'icon/star'

   def poster_get(self, item_url, game):
      (local, url) = game.poster_get()
      return (url, local)


class CatItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add(url, url[12:], None, mod.populate_categorie_page)

   def label_get(self, url, mod):
      return url[12:]


class MameModule(EmcModule):
   name = 'mame'
   label = _('M.A.M.E')
   icon = 'icon/mame'
   info = _("""Long info for the <b>M.A.M.E</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>""")

   def __init__(self):
      global _mod
      _mod = self

      DBG('Init MAME')
      self._snapshoot_dir = None
      self._rompaths = []
      self._favorites = []
      self._categories = {}

      self._games = {} # key = game_id<str>  value = <MameGame> instance
      self._browser = EmcBrowser('MAME')
      mainmenu.item_add('mame', 50, _('M.A.M.E'), 'icon/mame', self.cb_mainmenu)
      ini.add_section('mame')

   def __shutdown__(self):
      DBG('Shutdown MAME')

      # save favorite games
      ini.set_string_list('mame', 'favorites', self._favorites, ',')

      # clear stuff
      self._browser.delete()
      mainmenu.item_del('mame')
      del self._games

   def cb_mainmenu(self):
      """ Mainmenu clicked, build the root page """
      # set backdrop image
      bg = os.path.join(os.path.dirname(__file__), 'mamebg.jpg')
      gui.background_set(bg)

      # read favorite list from config (just the first time)
      if not self._favorites:
         self._favorites = ini.get_string_list('mame', 'favorites', ',')

      # show the spinning dialog
      self.dialog = EmcDialog(title=_('Searching games, please wait...'),
                              spinner=True, style='cancel')

      # Aquire mame dirs from the command 'mame -showconfig'
      self._rompaths = []
      self._snapshoot_dir = None
      EmcExec(MAME_EXE + ' -showconfig', grab_output=True,
              done_cb=self.cb_showconfig_done)

   def count_roms(self):
      tot = 0
      for dir in self._rompaths:
         if os.path.exists(dir):
            for f in os.listdir(dir):
               if f.endswith('.zip'):
                  tot += 1
      return tot

## async mame stuff
   def cb_showconfig_done(self, output):
      # mame not found
      if not output:
         self.dialog.delete()
         EmcDialog(title=_('M.A.M.E not found'), style='error',
                   text=_('Is mame installed?'))
         return

      # parse "mame -showconfig" output
      for l in output.split('\n'):
         if l.startswith('snapshot_directory ') or l.startswith('rompath '):
            key, val = l.split()
            val = val.replace('$HOME', os.getenv('HOME'))
            if key == 'snapshot_directory':
               self._snapshoot_dir = val
            elif key == 'rompath':
               for d in val.split(';'):
                  if not os.path.exists(d):
                     os.makedirs(d)
                  self._rompaths.append(d)

      DBG('ROM PATHS: %s' % self._rompaths)
      DBG('SNAP PATH: %s' % self._snapshoot_dir)

      # no path for roms found
      if len(self._rompaths) < 1:
         self.dialog.delete()
         EmcDialog(title=_('Can not get rom path from M.A.M.E.'), style='error',
                   text=_('Is your mame well configured?'))
         return

      # build the list of ALL the know games (only the first time)
      if self._games:
         self.cb_exe_end_listfull(None, None)
      else:
         exe = ecore.Exe(MAME_EXE + ' -listfull',
                         ecore.ECORE_EXE_PIPE_READ |
                         ecore.ECORE_EXE_PIPE_READ_LINE_BUFFERED)
         exe.on_data_event_add(self.cb_exe_event_listfull)
         exe.on_del_event_add(self.cb_exe_end_listfull)

   def cb_exe_event_listfull(self, exe, event):
      """ Data from the command 'mame -listfull' received.
-         Parse the line and fill the games list """
      for l in event.lines:
         gid = l[0:l.find(' ')]
         name = l[l.find('"') + 1:l.rfind('"')]
         # DBG("ID '" + gid + "' NAME '"+name+"'")
         if gid != 'Name:': #skip first line
            self._games[gid] = MameGame(gid, name)

   def cb_exe_end_listfull(self, exe, event):
      """ The command 'mame -listfull' is done, create the root page """
      self._browser.page_add('mame://root', _('M.A.M.E'), None, self.populate_root_page)
      self._browser.show()
      mainmenu.hide()
      self.dialog.delete()


## browser pages
   def populate_root_page(self, browser, url):
      """ Create the first list, the root one """
      self._browser.item_add(MyGamesItemClass(), 'mame://mygames', self)
      self._browser.item_add(AllGamesItemClass(), 'mame://allgames', self)
      self._browser.item_add(FavoriteGamesItemClass(), 'mame://favgames', self)
      self._browser.item_add(CategoriesItemClass(), 'mame://cats', self)

   def populate_mygames_page(self, browser, page_url):
      """ Create the list of personal games """
      L = list()
      for dir in self._rompaths:
         for rom in os.listdir(dir):
            id = os.path.splitext(rom)[0]
            if id and id in self._games:
               L.append(self._games[id])

      for game in sorted(L, key=operator.attrgetter('name')):
         self._browser.item_add(GameItemClass(), game.gid, game)

   def populate_allgames_page(self, browser, page_url):
      """ Create the list of all know mame games """
      itc = GameItemClass()
      for game in sorted(self._games.values(), key=operator.attrgetter('name')):
         self._browser.item_add(itc, game.gid, game)

   def populate_favgames_page(self, browser, page_url):
      """ Create the list of favorite games """
      for gid in self._favorites:
         if gid in self._games:
            game = self._games[gid]
            self._browser.item_add(GameItemClass(), gid, game)

   def populate_categories_page(self, browser, url):
      """ Create the list of categories """
      # get catver file from config (or set the default one)
      catver_file = ini.get('mame', 'catver_file')
      if not catver_file:
         catver_file = os.path.join(os.getenv('HOME'), '.mame', 'Catver.ini')
         ini.set('mame', 'catver_file', catver_file)

      # parse the cats list (if not yet done)
      if not self._parse_cats_file(): return

      for cat_name in sorted(self._categories.keys()):
         self._browser.item_add(CatItemClass(), 'mame://cats/' + cat_name, self)

   def populate_categorie_page(self, browser, url):
      """ Create the list of games in a given cat """
      cat_name = url[12:]
      for gid in self._categories[cat_name]:
         if gid in self._games:
            self._browser.item_add(GameItemClass(), gid, self._games[gid])

   def _parse_cats_file(self):
      # just the first time
      if self._categories: return True

      catver_file = ini.get('mame', 'catver_file')
      if not os.path.exists(catver_file):
         EmcDialog(title=_('No category file found'),style='error',
                   text=_('The category file is not included in mame, you '
                          'need to download a copy from the net. <br>'
                          'The file must be placed in %s') % (catver_file))
         return False

      f = open(catver_file, 'r')
      state = 0
      for line in f:
         #state0: searching for '[Category]'
         if state == 0:
            if line.startswith('[Category]'):
               state = 1
         #state1: filling cats
         elif state == 1:
            stripped = line.strip()
            if (stripped == ''):
               state = 2
            else:
               (game_id, cat) = stripped.split('=')
               if cat in self._categories:
                  self._categories[cat].append(game_id)
               else:
                  self._categories[cat] = [game_id]
         #state2: end
         elif state == 2:
            break
      f.close()
      return True


class MameGame(object):
   """
   This class describe a single mame game.
   """
   def __init__(self, gid, name):
      self.gid = gid
      self.name = name
      self.parsed = False
      self.history = None
      self.year = None
      self.manufacturer = None
      self.players = None
      self.buttons = None
      self.driver_savestate = None
      self.driver_status = None
      self.driver_emulation = None
      self.driver_color = None
      self.driver_sound = None
      self.driver_graphic = None

      self._dwnl_handler = None

   def run(self):
      DBG('RUN GAME: ' + self.gid)
      ecore.exe_run('%s %s' % (MAME_EXE, self.gid))

   def poster_get(self):
      snap_file = os.path.join(_mod._snapshoot_dir, self.gid, '0000.png')
      snap_url = 'http://www.progettoemma.net/snap/%s/0000.png' % self.gid
      return (snap_file, snap_url)

   def short_info_get(self):
      if self.parsed:
         return '<title>%s</><br>' \
                '<name>%s:</> %s<br>' \
                '<name>%s:</> %s<br>' \
                '<name>%s:</> %s<br>' \
                '<name>%s:</> %s<br>' % (
                  self.name,
                  _('Year'), self.year,
                  _('Manufacturer'), self.manufacturer,
                  _('Players'), self.players,
                  _('Buttons'), self.buttons)
      else:
         # update of the browser postponed... when_finished...quite an hack :/
         self._more_game_info(when_finished=(lambda: _mod._browser.refresh()))
         return ''

   def file_name_get(self):
      for dir in _mod._rompaths:
         f = os.path.join(dir, self.gid + '.zip')
         if (os.access(f, os.R_OK)):
            return f
      return None

## game dialog stuff
   def dialog_show(self):
      if not self.parsed:
         # postpone the action until info parsed
         self._more_game_info(when_finished=(lambda: self.dialog_show()))
         return

      (local, remote) = self.poster_get()
      image = EmcRemoteImage(remote, local)
      text = '<name>%s:</> %s<br>' \
             '<name>%s:</> %s<br>' \
             '<name>%s:</> %s<br>' \
             '<name>%s:</> %s<br>' \
             '<name>%s:</> %s<br>' \
             '<name>%s:</> %s<br>' \
             '   <name>%s:</> %s<br>' \
             '   <name>%s:</> %s<br>' \
             '   <name>%s:</> %s<br>' \
             '   <name>%s:</> %s<br>' % (
               _('Year'), self.year,
               _('Manufacturer'), self.manufacturer,
               _('Players'), self.players,
               _('Buttons'), self.buttons,
               _('Save state'), self.driver_savestate,
               _('Driver status'), self.driver_status,
               _('Emulation'), self.driver_emulation,
               _('Color'), self.driver_color,
               _('Sound'), self.driver_sound,
               _('Graphic'), self.driver_graphic)
      self.dialog = EmcDialog(self.name, content=image, text=text)

      if self.file_name_get():
         self.dialog.button_add(_('Play'), (lambda btn: self.run()))
      else:
         self.dialog.button_add(_('Download'), (lambda btn: self.download_zip()))

      if self.gid in _mod._favorites:
         self.dialog.button_add('', self._cb_favorite_button, icon='icon/star')
      else:
         self.dialog.button_add('', self._cb_favorite_button, icon='icon/star_off')

      self.dialog.button_add(_('History'), (lambda btn: self.history_show()))

      if self.file_name_get():
         self.dialog.button_add(_('Delete'), (lambda btn: self.delete_zip()))

   def _cb_favorite_button(self, btn):
      if self.gid in _mod._favorites:
         btn.content_set(gui.load_icon('icon/star_off'))
         _mod._favorites.remove(self.gid)
      else:
         _mod._favorites.append(self.gid)
         btn.content_set(gui.load_icon('icon/star'))
      _mod._browser.refresh()

   def history_show(self):
      # get history file from config (or set the default one)
      history_file = ini.get('mame', 'history_file')
      if not history_file:
         history_file = os.path.join(os.getenv('HOME'), '.mame', 'history.dat')
         ini.set('mame', 'history_file', history_file)

      # history.dat file not found
      if not os.path.exists(history_file):
         EmcDialog(title=_('No History file found'), style='error',
                   text=_('The History file is not included in mame, you '
                     'should download a copy from arcade-history.com<br>'
                     'The file must be unzipped and placed in %s') % history_file)
         return

      # parse the history file
      if not self.history:
         history = ''
         state = 0
         f = open(history_file, 'r')
         for line in f:
            # state0: search line that start with '$info'
            if state == 0:
               #~ DBG('0')
               if line.startswith('$info'):
                  names = line[6:].split(',')
                  names.pop() # discard last element (is a '\n\r')
                  if self.gid in names:
                     state = 1
            # state1: skip until '$bio'
            elif state == 1:
               if line.startswith('$bio'):
                  state = 2
            # state2: copy text until '$end'
            elif state == 2:
               if line.startswith('$end'):
                  state = 3 # done
               else:
                  line = line.replace('\r', '')
                  if line[0] == '-':
                     line = '<hilight>%s</>' % line
                  history = history + line + '<br>'
            #state3: end
            elif state == 3:
               break

         f.close()
         self.history = history
      
      if not self.history:
         EmcDialog(title=_('Game not found in history file'), style='error')
         return

      # show a scrollable text dialog with the game history
      EmcDialog(title=self.name, text=self.history, style='panel')

## delete game stuff
   def delete_zip(self):
      def _cb_done(dialog):
         self._delete_zip_real()
         dialog.delete()
      EmcDialog(title=_('Really delete this game?'), style='yesno',
                done_cb=_cb_done)

   def _delete_zip_real(self):
      done = False
      for dir in _mod._rompaths:
         f = os.path.join(dir, self.gid + '.zip')
         if (os.access(f, os.W_OK)):
            os.remove(f)
            done = True
      if done:
         self.dialog.delete()
         EmcDialog(title=_('Game deleted'), style='info')
         _mod._browser.refresh(hard=True)
      else:
         EmcDialog(text=_('Can not delete game'), style='error')

## download game stuff
   def download_zip(self):
      # choose a writable folder in rompath
      dest = None
      for dir in _mod._rompaths:
         if os.path.isdir(dir) and os.access(dir, os.W_OK):
            dest = dir
      if dest is None:
         EmcDialog(title=_('Error, can not find a writable rom directory'),
                   text=_('You sould check your mame configuration'),
                   style='error')
         return
      dest = os.path.join(dest, self.gid + '.zip')
      DBG('Download to: ' + dest)

      # create the new download dialog
      self.dialog.delete()
      self.dialog = EmcDialog(title=_('Game download'), spinner=True,
                              text='', style='progress')
      self.dialog.button_add(_('Close'), self.close_dialog)

      # Try to download the game from various roms site
      sources = []
      # freeroms.com
      title = _('Trying at freeroms.org...<br>')
      prefix = 'NUM' if self.gid[0].isdigit() else self.gid[0]
      url = 'http://download.freeroms.com/mame_roms/%s/%s.zip' % (prefix, self.gid)
      sources.append((title, url))
       # try somewhere else (suggestions are welcome)
      title = 'Trying not_work.com...<br>'
      url = 'http://freeroms67.freeroms.com/mame_roms/%c/%s.zip' % (self.gid[0], self.gid)
      sources.append((title, url))

      self._try_download_multi_sources(sources, dest)

   def close_dialog(self, dia):
      if self._dwnl_handler:
         utils.download_abort(self._dwnl_handler)
         self._dwnl_handler = None
      self.dialog.delete()

   def _try_download_multi_sources(self, sources, dest):
      (title, url) = sources.pop(0)
      self.dialog.text_append(title)
      DBG('Download from: ' + url)
      try:
         self._dwnl_handler = utils.download_url_async(url, dest, min_size=2000,
                                 complete_cb=self._cb_multi_download_complete,
                                 progress_cb=self._cb_multi_download_progress,
                                 sources=sources)
      except SystemError:
         if sources:
            self._try_download_multi_sources(sources, dest)
         else:
             self.dialog.text_append('<b>%s</b>' % _('Can not find the game online.'))
      else:
         self.dialog.spinner_start()

   def _cb_multi_download_complete(self, dest, status, sources):
      self._dwnl_handler = None
      self.dialog.spinner_stop()
      if status == 200: # no errors
         self.dialog.text_append('<b>%s</b>' % _('Download completed'))
      else:
         if sources:
            self._try_download_multi_sources(sources, dest)
         else:
            self.dialog.text_append('<b>%s</b>' % _('Can not find the game online.'))

   def _cb_multi_download_progress(self, dest, tot, done, sources):
      if tot > 0: self.dialog.progress_set(float(done) / float(tot))


## game info (from mame -listxml <rom>)
   def _more_game_info(self, when_finished=None):
      # do this only once
      if self.parsed: return
      # get game info from the command: mame -listxml <id>
      cmd = '%s -listxml %s' % (MAME_EXE, self.gid)
      EmcExec(cmd, True, self._more_game_info_done, when_finished)

   def _more_game_info_done(self, output, when_finished):
      # parse the buffered xml data
      doc = xml.dom.minidom.parseString(output)
      game_node = doc.getElementsByTagName('game')[0]
      if game_node.getAttribute('name') != self.gid: return

      # fill the game infos
      self.year = self._get_text_from_xml(game_node.getElementsByTagName('year'))
      self.manufacturer = self._get_text_from_xml(game_node.getElementsByTagName('manufacturer'))

      input_node = game_node.getElementsByTagName('input')[0]
      self.players = input_node.getAttribute('players')
      self.buttons = input_node.getAttribute('buttons')

      driver_node = game_node.getElementsByTagName('driver')[0]
      self.driver_status = driver_node.getAttribute('status')
      self.driver_emulation = driver_node.getAttribute('emulation')
      self.driver_color = driver_node.getAttribute('color')
      self.driver_sound = driver_node.getAttribute('sound')
      self.driver_graphic = driver_node.getAttribute('graphic')
      self.driver_savestate = driver_node.getAttribute('savestate')
      doc.unlink()

      self.parsed = True
      if callable(when_finished):
         when_finished()

   def _get_text_from_xml(self, nodelist):
      rc = []
      for node in nodelist:
         for child in node.childNodes:
            if child.nodeType == node.TEXT_NODE:
               rc.append(child.data)
      return ''.join(rc)
