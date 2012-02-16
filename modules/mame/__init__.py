#!/usr/bin/env python
#
# Copyright (C) 2010 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of EpyMC.
#
# EpyMC is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# EpyMC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with EpyMC. If not, see <http://www.gnu.org/licenses/>.

import os
import xml.dom.minidom
import operator

import evas
import ecore
import elementary

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser
from epymc.gui import EmcDialog
import epymc.mainmenu as mainmenu
import epymc.browser as browser
import epymc.utils as utils
import epymc.gui as gui
import epymc.ini as ini


def DBG(msg):
   print('MAME: ' + str(msg))
   pass

MAME_EXE = 'mame'
_instance = None

class MameModule(EmcModule):
   name = 'mame'
   label = 'M.A.M.E'
   icon = 'icon/mame'
   info = """Long info for the <b>M.A.M.E</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>"""


   _snapshoot_dir = None
   _rompaths = []
   _favorites = []
   _categories = {}

   def __init__(self):
      global _instance
      DBG('Init MAME')
      _instance = self
      self._games = {} # key = game_id<str>  value = <MameGame> instance
      self._browser = EmcBrowser('MAME',
                       item_selected_cb = self.browser_item_selected,
                       poster_get_cb = self.browser_poster_get,
                       info_get_cb = self.browser_info_get,
                       icon_get_cb = self.browser_icon_get)

      mainmenu.item_add("mame", 50, "M.A.M.E", None, self.cb_mainmenu)

      # create config ini section if not exists
      ini.add_section('mame')

   def __shutdown__(self):
      DBG('Shutdown MAME')

      # save favorite games
      ini.set_string_list("mame", "favorites", MameModule._favorites, ',')

      # clear stuff
      self._browser.delete()
      mainmenu.item_del("mame")
      del self._games

   def cb_mainmenu(self):
      """ Mainmenu clicked, build the root page """
      #set backdrop image
      bg = os.path.join(utils.base_dir_get(), 'modules', 'mame', 'mamebg.jpg')
      gui.background_set(bg)

      # read favorite list from config (just the first time)
      if not MameModule._favorites:
         MameModule._favorites = ini.get_string_list('mame', 'favorites', ',')

      # show the spinning dialog
      self.dialog = EmcDialog(title = 'Searching games, please wait...',
                              spinner = True, style = 'cancel')

      # Aquire mame dirs from the command 'mame -showconfig'
      MameModule._rompaths = []
      MameModule._snapshoot_dir = None
      exe = ecore.Exe(MAME_EXE + " -showconfig | grep -e snapshot_directory -e rompath",
                     ecore.ECORE_EXE_PIPE_READ |
                     ecore.ECORE_EXE_PIPE_READ_LINE_BUFFERED)
      exe.on_data_event_add(self.cb_exe_event_showconfig)
      exe.on_del_event_add(self.cb_exe_end_showconfig)

   def count_roms(self):
      tot = 0
      for dir in MameModule._rompaths:
         if os.path.exists(dir):
            for f in os.listdir(dir):
               if f.endswith('.zip'):
                  tot += 1
      return tot

## async mame stuff
   def cb_exe_event_showconfig(self, exe, event):
      """ Data from the command 'mame -showconfig' received.
         Parse the line and fill the class vars """
      for l in event.lines:
         (key, val) = l.split()
         for dir in val.split(';'):
            dir_real = dir.replace('$HOME', os.getenv('HOME'))
            if key == 'rompath':
               if not os.path.exists(dir_real):
                  os.makedirs(dir_real)
               MameModule._rompaths.append(dir_real)
            elif key == 'snapshot_directory':
               MameModule._snapshoot_dir = dir_real

   def cb_exe_end_showconfig(self, exe, event):
      """ The command 'mame -showconfig' is done """
      if event.exit_code == 0:
         DBG('mame found')
         DBG('ROM PATHS: ' + str(MameModule._rompaths))
         DBG('SNAP PATH: ' + MameModule._snapshoot_dir)

         # build the full list only the first time
         if self._games:
            self.cb_exe_end_listfull(None, None)
            return

         if len(MameModule._rompaths) > 0:
            # get the list of games now
            exe = ecore.Exe(MAME_EXE + " -listfull",
                           ecore.ECORE_EXE_PIPE_READ |
                           ecore.ECORE_EXE_PIPE_READ_LINE_BUFFERED)
            exe.on_data_event_add(self.cb_exe_event_listfull)
            exe.on_del_event_add(self.cb_exe_end_listfull)
         else:
            self.dialog.delete()
            EmcDialog(title = 'Can\'t get rom path from M.A.M.E.',
                      text = 'Is your mame well configured?',
                      style = 'error')
      else:
         DBG('ERROR: mame not found in PATH')
         self.dialog.delete()
         EmcDialog(title = 'M.A.M.E not found', style = 'error',
                   text = '<br>Is mame in your path?')

   def cb_exe_event_listfull(self, exe, event):
      """ Data from the command 'mame -listfull' received.
         Parse the line and fill the games list """
      first = True
      for l in event.lines:
         id = l[0:l.find(' ')]
         name = l[l.find('"') + 1:l.rfind('"')]
         #~ DBG("ID '" + id + "' NAME '"+name+"'")
         if id != 'Name:': #skip first line
            self._games[id] = MameGame(id, name)

   def cb_exe_end_listfull(self, exe, event):
      """ The command 'mame -listfull' is done, create the root page """
      self.create_root_page()
      self._browser.show()
      mainmenu.hide()
      self.dialog.delete()


## browser pages
   def create_root_page(self):
      self._browser.page_add('mame://root', "M.A.M.E")
      self._browser.item_add('mame://mygames',
                             'My Games (%d)' % (self.count_roms()))
      self._browser.item_add('mame://allgames',
                             'All Games (%d)' % (len(self._games)))
      self._browser.item_add('mame://favgames',
                             'Favorite Games (%d)' % (len(MameModule._favorites)))
      self._browser.item_add('mame://cats', 'Categories')

   def my_games_list(self):
      """ Create the list of personal games """
      self._browser.page_add('mame://mygames', "My Games")

      L = list()
      for dir in MameModule._rompaths:
         for rom in os.listdir(dir):
            id = rom.strip(".zip")
            if id and self._games.has_key(id):
               L.append((id, self._games[id].name))

      L.sort(key = operator.itemgetter(1))
      for k, l in L:
         self._browser.item_add(k, l)

   def all_games_list(self):
      """ Create the list of all know mame games """
      self._browser.page_add('mame://allgames', "All Games")

      L = list()
      for id, g in self._games.items():
         L.append((id, g.name))

      L.sort(key = operator.itemgetter(1))
      for k, l in L:
         self._browser.item_add(k, l)

   def fav_games_list(self):
      """ Create the list of favorite games """
      self._browser.page_add('mame://favgames', "Favorite Games")

      for gid in MameModule._favorites:
         if self._games.has_key(gid):
            g = self._games[gid]
            self._browser.item_add(gid, g.name)

   def cats_list(self):
      """ Create the list of categories """
      # get catver file from config (or set the default one)
      catver_file = ini.get('mame', 'catver_file')
      if not catver_file:
         catver_file = os.path.join(os.getenv('HOME'), '.mame', 'Catver.ini')
         ini.set('mame', 'catver_file', catver_file)

      # parse the cats list (if not yet done)
      if not self._parse_cats_file(): return

      self._browser.page_add('mame://cats', "Categories")

      for cat_name in sorted(self._categories.keys()):
         self._browser.item_add('mame://cats/' + cat_name,
                  cat_name + ' (' + str(len(self._categories[cat_name])) + ')')

   def game_by_cat_list(self, cat_name):
      """ Create the list of games in the given cat """
      self._browser.page_add('mame://cats/' + cat_name, cat_name)

      for gid in MameModule._categories[cat_name]:
         if self._games.has_key(gid):
            self._browser.item_add(gid, self._games[gid].name)

   def _parse_cats_file(self):
      # just the first time
      if MameModule._categories: return True

      catver_file = ini.get('mame', 'catver_file')
      if not os.path.exists(catver_file):
         EmcDialog(title = 'No category file found',style = 'error',
                   text = 'The category file is not included in mame, you '
                          'need to download a copy from the net. <br>'
                          'The file must be placed in ' + catver_file)
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
               if MameModule._categories.has_key(cat):
                  MameModule._categories[cat].append(game_id)
               else:
                  MameModule._categories[cat] = [game_id]
         #state2: end
         elif state == 2:
            break
      f.close()
      return True

## browser model functions
   def browser_info_get(self, page_url, item_url):
      if self._games.has_key(item_url):
         return self._games[item_url].short_info_get()
      return None

   def browser_poster_get(self, page_url, item_url):
      if self._games.has_key(item_url):
         g = self._games[item_url]
         (local, url) = g.poster_get()
         return local if not url else url + ';' + local
      return None

   def browser_icon_get(self, page_url, item_url):
      if not item_url.startswith('mame://'):
         if item_url in MameModule._favorites:
            return 'icon/star'

   def browser_item_selected(self, page_url, item_url):
      DBG("PAGE: " + str(page_url))
      DBG("ITEM: " + str(item_url))
      if item_url == "mame://root": self.create_root_page()
      elif item_url == "mame://mygames": self.my_games_list()
      elif item_url == "mame://allgames": self.all_games_list()
      elif item_url == "mame://favgames": self.fav_games_list()
      elif item_url == "mame://cats": self.cats_list()
      elif item_url.startswith("mame://cats/"):
         self.game_by_cat_list(item_url[12:])
      elif self._games.has_key(item_url):
         self._games[item_url].dialog_show()


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

   def run(self):
      DBG('RUN GAME: ' + self.gid)
      ecore.exe_run('%s %s' % (MAME_EXE, self.gid))

   def poster_get(self):
      snap_file = os.path.join(MameModule._snapshoot_dir, self.gid, '0000.png')
      snap_url = 'http://www.progettoemma.net/snap/%s/0000.png' % self.gid
      if os.path.isfile(snap_file):
         return (snap_file, None)
      else:
         return (snap_file, snap_url)

   def short_info_get(self):
      self._more_game_info()
      return '<title>%s</><br>' \
             '<hilight>Year:</> %s<br>' \
             '<hilight>Manufacturer:</> %s<br>' \
             '<hilight>Players:</> %s<br>' \
             '<hilight>Buttons:</> %s<br>' % \
             (self.name, self.year, self.manufacturer, self.players,
              self.buttons)

   def file_name_get(self):
      for dir in MameModule._rompaths:
         f = os.path.join(dir, self.gid + '.zip')
         if (os.access(f, os.R_OK)):
            return f
      return None

## game dialog stuff
   def dialog_show(self):
      box = elementary.Box(gui.win)
      box.horizontal_set(True)
      box.homogenous_set(True)
      box.show()

      image = gui.EmcRemoteImage(gui.win)
      image.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      image.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      (local, remote) = self.poster_get()
      image.url_set(remote, local)
      image.show()
      box.pack_end(image)

      sentry = elementary.ScrolledEntry(gui.win)
      sentry.style_set("dialog")
      sentry.editable_set(False)
      sentry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      sentry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      text = '<hilight>Year:</> %s<br>' \
             '<hilight>Manufacturer:</> %s<br>' \
             '<hilight>Players:</> %s<br>' \
             '<hilight>Buttons:</> %s<br>' \
             '<hilight>Savestate:</> %s<br>' \
             '<hilight>Driver status:</> %s<br>' \
             '   <hilight>emulation:</> %s<br>' \
             '   <hilight>color:</> %s<br>' \
             '   <hilight>sound:</> %s<br>' \
             '   <hilight>graphic:</> %s<br>' % \
             (self.year, self.manufacturer, self.players,
              self.buttons, self.driver_savestate, self.driver_status,
              self.driver_emulation, self.driver_color,
              self.driver_sound, self.driver_graphic)
      sentry.entry_set(text)
      sentry.show()
      box.pack_start(sentry)

      self.dialog = EmcDialog(self.name, content = box)

      if self.file_name_get():
         self.dialog.button_add('Play', (lambda btn: self.run()))
      else:
         self.dialog.button_add('Download', (lambda btn: self.download_zip()))

      if self.gid in MameModule._favorites:
         self.dialog.button_add('', self._cb_favorite_button, icon = 'icon/star')
      else:
         self.dialog.button_add('', self._cb_favorite_button, icon = 'icon/star_off')

      self.dialog.button_add('History', (lambda btn: self.history_show()))

      if self.file_name_get():
         self.dialog.button_add('Delete', (lambda btn: self.delete_zip()))

      self.dialog.button_add('Close', (lambda btn: self.dialog.delete()))
      self.dialog.activate()

   def _cb_favorite_button(self, btn):
      if self.gid in MameModule._favorites:
         btn.icon_set(gui.load_icon('icon/star_off'))
         MameModule._favorites.remove(self.gid)
      else:
         MameModule._favorites.append(self.gid)
         btn.icon_set(gui.load_icon('icon/star'))
      _instance._browser.refresh()

   def history_show(self):
      # get history file from config (or set the default one)
      history_file = ini.get('mame', 'history_file')
      if not history_file:
         history_file = os.path.join(os.getenv('HOME'), '.mame', 'history.dat')
         ini.set('mame', 'history_file', history_file)

      # history.dat file not found
      if not os.path.exists(history_file):
         EmcDialog(title = 'No History file found',style = 'error',
                   text = 'The History file is not included in mame, you '
                          'should download a copy from aracade-history.com <br>'
                          'The file must be unzipped and placed in ' + history_file)
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
                  print names
                  if self.gid in names:
                     print names
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
                  history = history + line + '<br>'
            #state3: end
            elif state == 3:
               break

         f.close()
         self.history = history
      
      if not self.history:
         EmcDialog(title = 'Game not found in history file', style = 'error')
         return

      # build the dialog
      se = elementary.ScrolledEntry(gui.win)
      se.style_set('dialog')
      se.editable_set(False)
      se.show()
      #~ se.bounce_set(0, 1)
      se.entry_set(self.history)

      dia = EmcDialog(title = self.name, content = se, style = 'default')
      dia.button_add('Close', lambda btn: dia.delete())
      dia.activate()

## delete game stuff
   def delete_zip(self):
      def _cb_done(dialog):
         self._delete_zip_real()
         dialog.delete()
      EmcDialog(title = 'Really delete this game?', style='yesno',
                done_cb = _cb_done)

   def _delete_zip_real(self):
      done = False
      for dir in MameModule._rompaths:
         f = os.path.join(dir, self.gid + '.zip')
         if (os.access(f, os.W_OK)):
            os.remove(f)
            done = True
      if done:
         self.dialog.delete()
         EmcDialog(title = 'Game deleted', style = 'info')
         _instance._browser.refresh(recreate=True)
      else:
         EmcDialog(text = 'Can not delete game', style = 'error')

## download game stuff
   def download_zip(self):
      # choose a writable folder in rompath
      dest = None
      for dir in MameModule._rompaths:
         if os.path.isdir(dir) and os.access(dir, os.W_OK):
            dest = dir
      if dest is None:
         EmcDialog(title = 'Error, can not find a writable rom directory',
                   text = 'You sould check your mame configuration',
                   style = 'error')
         return
      dest = os.path.join(dest, self.gid + '.zip')
      DBG('Download to: ' + dest)

      # create the new download dialog
      self.dialog.delete()
      self.dialog = EmcDialog(title = 'Game download', spinner = True,
                              text = '', style= 'minimal_vertical')
      self.dialog.button_add('Close', lambda btn: self.dialog.delete()) # TODO abort download well if needed
      self.dialog.activate()

      # Try to download the game from various roms site
      sources = []
      # freeroms.com
      title = "Trying at freeroms.org...<br>"
      prefix = 'NUM' if self.gid[0].isdigit() else self.gid[0]
      url = 'http://download.freeroms.com/mame_roms/%s/%s.zip' % (prefix, self.gid)
      sources.append((title, url))
       # try somewhere else (suggestions are welcome)
      title = "Trying not_work.com...<br>"
      url = 'http://freeroms67.freeroms.com/mame_roms/%c/%s.zip' % (self.gid[0], self.gid)
      sources.append((title, url))

      self._try_download_multi_sources(sources, dest)

   def _try_download_multi_sources(self, sources, dest):
      (title, url) = sources.pop(0)
      self.dialog.text_append(title)
      DBG('Download from: ' + url)
      try:
         utils.download_url_async(url, dest, min_size = 2000,
                           complete_cb = self._cb_multi_download_complete,
                           progress_cb = self._cb_multi_download_progress,
                           sources = sources)
      except SystemError:
         if sources:
            self._try_download_multi_sources(sources, dest)
         else:
            self.dialog.text_append('<b>Can not find the game online, sorry.</>')
      else:
         self.dialog.spinner_start()

   def _cb_multi_download_complete(self, dest, status, sources):
      self.dialog.spinner_stop()
      if status == 200: # no errors
         self.dialog.text_append('<b>Download done :)</>')
      else:
         if sources:
            self._try_download_multi_sources(sources, dest)
         else:
            self.dialog.text_append('<b>Can not find the game online, sorry.</b>')

   def _cb_multi_download_progress(self, file, dltotal, dlnow, sources):
      #~ print dlnow
      pass

## game info (from mame -listxml <rom>)
   def _more_game_info(self):
      # do this only once
      if self.parsed: return

      # get game info from the command: mame -listxml <id>
      # TODO use a better/portable way (but not async)
      os.system(MAME_EXE + ' -listxml ' + self.gid + ' > /tmp/PyEmc__MAME_tmp')
      #ecore.exe_run('%s -listxml %s > /tmp/PyEmc__MAME_tmp' % (MAME_EXE, self.gid))

      # parse the xml file
      doc = xml.dom.minidom.parse('/tmp/PyEmc__MAME_tmp')
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

   def _get_text_from_xml(self, nodelist):
      rc = []
      for node in nodelist:
         for child in node.childNodes:
            if child.nodeType == node.TEXT_NODE:
               rc.append(child.data)
      return ''.join(rc)
