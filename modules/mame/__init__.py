#!/usr/bin/env python

import os
import xml.dom.minidom
import operator

import evas
import ecore
import elementary

from modules import EmcModule
from browser import EmcBrowser
from gui import EmcDialog
import mainmenu
import browser
import utils
import gui
import downloader


def DBG(msg):
   print('MAME: ' + str(msg))
   pass

MAME_EXE = 'mame'

class MameModule(EmcModule):
   name = 'mame'
   label = 'M.A.M.E'

   def __init__(self):
      DBG('Init MAME')
      
      self._rompaths = []
      self._games = {} # key = game_id<str>  value = game_info<dict>
      self._snapshoot_dir = None

      self._browser = EmcBrowser('MAME',
                       item_selected_cb = self.browser_item_selected,
                       poster_get_cb = self.browser_poster_get,
                       info_get_cb = self.browser_info_get)

      mainmenu.item_add("mame", 50, "M.A.M.E", None, self.cb_mainmenu)

   def __shutdown__(self):
      DBG('Shutdown MAME')
      del self._browser
      mainmenu.item_del("mame")

   def cb_mainmenu(self):
      """ Mainmenu clicked, build the root page """

      # show the spinning dialog
      self.dialog = EmcDialog(title = 'Searching games, please wait...',
                              spinner = True)
      self.dialog.activate()

      # Aquire mame dirs from the command 'mame -showconfig'
      self._rompaths = []
      self._snapshoot_dir = None
      exe = ecore.Exe(MAME_EXE + " -showconfig | grep -e snapshot_directory -e rompath",
                     ecore.ECORE_EXE_PIPE_READ |
                     ecore.ECORE_EXE_PIPE_READ_LINE_BUFFERED)
      exe.on_data_event_add(self.cb_exe_event_showconfig)
      exe.on_del_event_add(self.cb_exe_end_showconfig)

## async mame stuff
   def cb_exe_event_showconfig(self, exe, event):
      """ Data from the command 'mame -showconfig' received.
         Parse the line and fill the class vars """
      for l in event.lines:
         (key, val) = l.split()
         for dir in val.split(';'):
            dir_real = dir.replace('$HOME', os.getenv('HOME'))
            if key == 'rompath':
               self._rompaths.append(dir_real)
            elif key == 'snapshot_directory':
               self._snapshoot_dir = dir_real

   def cb_exe_end_showconfig(self, exe, event):
      """ The command 'mame -showconfig' is done """
      if event.exit_code == 0:
         DBG('mame found')
         DBG('ROM PATHS: ' + str(self._rompaths))
         DBG('SNAP PATH: ' + self._snapshoot_dir)

         # build the full list only the first time
         if self._games:
            self.cb_exe_end_listfull(None, None)
            return

         if len(self._rompaths) > 0:
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
      for l in event.lines:
         id = l[0:l.find(' ')]
         name = l[l.find('"') + 1:l.rfind('"')]
         #~ print "ID '" + id + "' NAME '"+name+"'"
         if id != 'Name:':
            self._games[id] = {'name': name} # TODO add more info now??

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
                             'Favorite Games (TODO)')
      self._browser.item_add('emc://back', "Back")

   def my_games_list(self):
      """ Create the list of personal games """
      self._browser.page_add('my_games', "My Games")

      L = list()
      for dir in self._rompaths:
         for rom in os.listdir(dir):
            id = rom.strip(".zip")
            if id and self._games.has_key(id):
               L.append((id, self._games[id]['name']))

      L.sort(key = operator.itemgetter(1))
      for k, l in L:
         self._browser.item_add(k, l)

      self._browser.item_add('emc://back', "Back")

   def all_games_list(self):
      """ Create the list of all know mame games """
      self._browser.page_add('all_games', "All Games")

      L = list()
      for id, game in self._games.items():
         L.append((id, game['name']))

      L.sort(key = operator.itemgetter(1))
      for k, l in L:
         self._browser.item_add(k, l)

      self._browser.item_add('emc://back', "Back")

   def fav_games_list(self):
      print ' - Favorite Games'


## browser model functions
   def browser_info_get(self, page_url, item_url):
      if not self._games.has_key(item_url): return None
      self.get_more_info(item_url)
      game = self._games[item_url]
      text = '<hilight>Year:</> %s<br>' \
             '<hilight>Manufacturer:</> %s<br>' \
             '<hilight>Players:</> %s<br>' \
             '<hilight>Buttons:</> %s<br>' % \
             (game['year'], game['manufacturer'], game['players'],
              game['buttons'])
      return text

   def getTextFromXml(self, nodelist):
      rc = []
      for node in nodelist:
         for child in node.childNodes:
            if child.nodeType == node.TEXT_NODE:
               rc.append(child.data)
      return ''.join(rc)

   def browser_poster_get(self, page_url, item_url):
      if not self._games.has_key(item_url): return None
      (local, url) = self.get_game_poster(item_url)
      return local if not url else url + ';' + local

   def browser_item_selected(self, page_url, item_url):
      if item_url == "mame://root": self.create_root_page()
      elif item_url == "mame://mygames": self.my_games_list()
      elif item_url == "mame://allgames": self.all_games_list()
      elif item_url == "mame://favgames": self.fav_games_list()
      else: self.show_game_dialog(item_url)

## dialog stuff
   def show_game_dialog(self, id):
      game = self._games[id]

      box = elementary.Box(gui.win)
      box.horizontal_set(1)
      box.homogenous_set(1)
      box.show()

      image = gui.EmcRemoteImage(gui.win)
      image.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      image.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      (local, url) = self.get_game_poster(id)
      image.url_set(url, local)
      image.show()
      box.pack_end(image)

      anchorblock = elementary.AnchorView(gui.win)
      anchorblock.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      anchorblock.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
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
             (game['year'], game['manufacturer'], game['players'],
              game['buttons'], game['driver_savestate'], game['driver_status'],
              game['driver_emulation'], game['driver_color'],
              game['driver_sound'], game['driver_graphic'])
      anchorblock.text_set(text)
      anchorblock.show()
      box.pack_end(anchorblock)


      self.dialog = EmcDialog(game['name'], style = 'default', content = box)
      if self.get_game_file(id):
         self.dialog.button_add("Run", (lambda btn: self.run_game(id)))
         self.dialog.button_add("Delete", (lambda btn: self.delete_game(id)))
      else:
         self.dialog.button_add("Download Game", (lambda btn: self.download_game(id)))
      self.dialog.button_add("Close", (lambda btn: self.dialog.delete()))
      self.dialog.activate()

## mame functions
   def count_roms(self):
      tot = 0
      for dir in self._rompaths:
         for f in os.listdir(dir):
            if f.endswith('.zip'):
               tot += 1
      return tot

   def get_more_info(self, id):
      # do this only once
      game = self._games[id]
      if len(game) > 1: return
      
      # get game info from the command: mame -listxml <id>
      # TODO use a better/portable way (but not async)
      os.system(MAME_EXE + ' -listxml ' + id + ' > /tmp/PyEmc__MAME_tmp')

      # parse the xml file
      doc = xml.dom.minidom.parse('/tmp/PyEmc__MAME_tmp')
      game_node = doc.getElementsByTagName('game')[0]
      if game_node.getAttribute('name') != id: return None

      # fill the game infos
      game['year'] = self.getTextFromXml(game_node.getElementsByTagName('year'))
      game['manufacturer'] = self.getTextFromXml(game_node.getElementsByTagName('manufacturer'))

      input_node = game_node.getElementsByTagName('input')[0]
      game['players'] = input_node.getAttribute('players')
      game['buttons'] = input_node.getAttribute('buttons')

      driver_node = game_node.getElementsByTagName('driver')[0]
      game['driver_status'] = driver_node.getAttribute('status')
      game['driver_emulation'] = driver_node.getAttribute('emulation')
      game['driver_color'] = driver_node.getAttribute('color')
      game['driver_sound'] = driver_node.getAttribute('sound')
      game['driver_graphic'] = driver_node.getAttribute('graphic')
      game['driver_savestate'] = driver_node.getAttribute('savestate')
      doc.unlink()

   def get_game_file(self, id):
      for dir in self._rompaths:
         f = os.path.join(dir, id + '.zip')
         if (os.access(f, os.R_OK)):
            return f
      return None

   def get_game_poster(self, id):
      if not self._games.has_key(id): return None

      snap_file = os.path.join(self._snapshoot_dir, id, '0000.png')
      snap_url = 'http://www.progettoemma.net/snap/%s/0000.png' % id

      if os.path.isfile(snap_file):
         return (snap_file, None)
      else:
         return (snap_file, snap_url)

   def run_game(self, id):
      DBG('RUN GAME: ' + id)
      os.system(MAME_EXE + ' ' + id)

   def delete_game(self, id):
      done = False
      for dir in self._rompaths:
         f = os.path.join(dir, id + '.zip')
         if (os.access(f, os.W_OK)):
            os.remove(f)
            done = True
      if done:
         EmcDialog(title = 'Game deleted', style = 'info')
         self.dialog.delete()
      else:
         EmcDialog(title = 'Can not delete game', style = 'error')

   def download_game(self, id):
      # choose a writable folder in rompath
      dest = None
      for dir in self._rompaths:
         if os.path.isdir(dir) and os.access(dir, os.W_OK):
            dest = dir
      if dest is None:
         EmcDialog(title = 'Error, can not find a writable rom directory',
                   text = 'You sould check your mame configuration',
                   style = 'error')
         return
      dest = os.path.join(dest, id + '.zip')
      DBG('DEST: ' + dest)
      
      # create the new download dialog
      self.dialog.delete()
      self.dialog = EmcDialog(title = 'Game download', spinner = True,
                              text = ' ', style= 'minimal')
      self.dialog.button_add('Close', lambda btn: self.dialog.delete()) # TODO abort download well if needed
      self.dialog.activate()

      # try at freeroms.com
      url = 'http://roms3.freeroms.com/mame_roms/%c/%s.zip' % (id[0], id)
      DBG('try freeroms.org: ' + url)
      self.dialog.text_set('Search at freeroms.com...')
      downloader.download_url_async(url, dest, min_size = 2000,
                           complete_cb = self._cb_download_freeromsorg_complete,
                           progress_cb = None)

   def _cb_download_freeromsorg_complete(self, url, dest, header):
      if os.path.exists(dest):
         self.dialog.text_set('Download done :)')
         self.dialog.spinner_stop()
      else:
         self.dialog.text_set('Can not find the game online, sorry.')
         self.dialog.spinner_stop()
         # TODO search on other site
