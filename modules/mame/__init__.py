#!/usr/bin/env python

import os
import xml.dom.minidom
import operator

import ecore

from modules import EmcModule
from browser import EmcBrowser
from gui import EmcDialog
import mainmenu
import browser
import utils


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
      game = self._games[item_url]
      if len(game) < 2: # at the start only one element in the dict (the name)
         # get game info from the command: mame -listxml <id>
         # TODO use a better/portable way (but not async)
         os.system(MAME_EXE + ' -listxml ' + item_url + ' > /tmp/PyEmc__MAME_tmp')

         # parse the xml file
         doc = xml.dom.minidom.parse('/tmp/PyEmc__MAME_tmp')
         game_node = doc.getElementsByTagName('game')[0]
         if game_node.getAttribute('name') != item_url: return None

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

      # check local snapshot...
      snap_file = os.path.join(self._snapshoot_dir, item_url, '0000.png')
      if os.path.isfile(snap_file):
         return snap_file

      # ...or donwload the file from progettoemma.it #TODO give credits
      snap_url = 'http://www.progettoemma.net/snap/%s/0000.png' % url
      return snap_url + ';' + snap_file

   def browser_item_selected(self, page_url, item_url):
      if item_url == "mame://root": self.create_root_page()
      elif item_url == "mame://mygames": self.my_games_list()
      elif item_url == "mame://allgames": self.all_games_list()
      elif item_url == "mame://favgames": self.fav_games_list()
      else: self.run_game(item_url)

## mame functions
   def count_roms(self):
      tot = 0
      for dir in self._rompaths:
         for f in os.listdir(dir):
            if f.endswith('.zip'):
               tot += 1
      return tot

   def run_game(self, id):
      DBG('RUN GAME: ' + id)
      os.system(MAME_EXE + ' ' + id)

   def download_game(self, id):
      print 'Download ' + id
      url = 'http://roms3.freeroms.com/mame_roms/%c/%s.zip' % (id[0], id)

      dest = None
      for dir in self._rompaths:
         if os.path.isdir(dir) and os.access(dir, os.W_OK):
            dest = dir

      if dest:
         dest = os.path.join(dest, id + '.zip')
      else:
         print 'Error: can not find a writable rom directory'
         return

      print 'URL: ' + url
      print 'DEST: ' + dest
      headers = utils.download_url_sync(url, dest, 2000)
      if not headers:
         print 'ERROR DOWNLOADING ' + url
