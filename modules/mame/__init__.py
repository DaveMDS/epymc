#!/usr/bin/env python

import os
import xml.dom.minidom
import operator

import ecore

from modules import EmcModule
from browser import EmcBrowser
import mainmenu
import browser
import utils


class MameModule(EmcModule):
    name = 'mame'
    label = 'M.A.M.E'

    __rompaths = []
    __snapshoot_dir = None
    __games = {} # key = game_id<str>  value = game_info<dict>

    def __init__(self):
        print 'Init module 2: MAME'
        mainmenu.item_add("mame", 50, "M.A.M.E", None, self.__cb_mainmenu)

        self.__browser = EmcBrowser()
        # Aquire mame dirs from the command 'sdlmame -showconfig' TODO this shuold be done later...
        exe = ecore.Exe("sdlmame -showconfig | grep -e snapshot_directory -e rompath",
                        ecore.ECORE_EXE_PIPE_READ |
                        ecore.ECORE_EXE_PIPE_READ_LINE_BUFFERED)
        exe.on_data_event_add(self.__showconfig_event_cb)

    def __shutdown__(self):
        print "Shutdown module: M.A.M.E."
        mainmenu.item_del("mame")
        del self.__browser

    def __showconfig_event_cb(self, exe, event):
        """ Data from the command 'sdlmame -showconfig' received.
            Parse the line and fill the class vars """
        for l in event.lines:
            (key, val) = l.split()
            for dir in val.split(';'):
                dir_real = dir.replace('$HOME', os.getenv('HOME'))
                if key == 'rompath':
                    self.__rompaths.append(dir_real)
                elif key == 'snapshot_directory':
                    self.__snapshoot_dir = dir_real

    def __listfull_event_cb(self, exe, event):
        """ Data from the command 'sdlmame -listfull' received.
            Parse the line and fill the games list """
        for l in event.lines:
            id = l[0:l.find(' ')]
            name = l[l.find('"') + 1:l.rfind('"')]
            #~ print "ID '" + id + "' NAME '"+name+"'"
            if id != 'Name:':
                self.__games[id] = {'name': name} # TODO add more info now??

    def __listfull_end_event_cb(self, exe, event):
        """ The command 'sdlmame -listfull' is done, create the root page """
        self.create_root_page()
        self.__browser.show()

    def __cb_mainmenu(self):
        """ Mainmnu clicked, build the root page """

        # Is mame present ?
        if not self.__rompaths:
            print "No mame found"
            #TODO alert the user
            return

        # Aquire the list of all games from the command 'sdlmame -listfull'
        if not self.__games:
            exe = ecore.Exe("sdlmame -listfull",
                            ecore.ECORE_EXE_PIPE_READ |
                            ecore.ECORE_EXE_PIPE_READ_LINE_BUFFERED)
            exe.on_data_event_add(self.__listfull_event_cb)
            exe.on_del_event_add(self.__listfull_end_event_cb)
            #TODO show a popup while loading ??
        else:
            self.create_root_page()
            self.__browser.show()

        mainmenu.hide()


    def create_root_page(self):
        self.__browser.page_add('mame://root', "M.A.M.E",
                                item_selected_cb = self.__cb_root_selected)
        self.__browser.item_add('mame://mygames', "My Games")
        self.__browser.item_add('mame://allgames', "All Games")
        self.__browser.item_add('mame://favgames', "Favorite Games")
        self.__browser.item_add('emc://back', "Back")


    def __cb_root_selected(self, url):
        """ Item selected in root page """
        if url == "mame://root": self.create_root_page()
        elif url == "mame://mygames": self.my_games_list()
        elif url == "mame://allgames": self.all_games_list()
        elif url == "mame://favgames": self.fav_games_list()

    def my_games_list(self):
        """ Create the list of personal games """
        self.__browser.page_add('my_games', "My Games",
                       item_selected_cb = self.__cb_game_selected,
                       poster_get_cb = self.__cb_poster_get,
                       info_get_cb = self.__cb_info_get)

        print "ROMS " + str(self.__rompaths)
        L = list()
        for dir in self.__rompaths:
            for rom in os.listdir(dir):
                print "ROM" + rom
                id = rom.strip(".zip")
                if id and self.__games.has_key(id):
                    L.append((id, self.__games[id]['name']))

        L.sort(key = operator.itemgetter(1))
        for k, l in L:
            self.__browser.item_add(k, l)

        self.__browser.item_add('emc://back', "Back")

    def all_games_list(self):
        """ Create the list of all know mame games """
        self.__browser.page_add('all_games', "All Games",
                         item_selected_cb = self.__cb_game_selected,
                         poster_get_cb = self.__cb_poster_get,
                         info_get_cb = self.__cb_info_get)

        L = list()
        for id, game in self.__games.items():
            L.append((id, game['name']))

        L.sort(key = operator.itemgetter(1))
        for k, l in L:
            self.__browser.item_add(k, l)

        self.__browser.item_add('emc://back', "Back")

    def fav_games_list(self):
        print ' - Favorite Games'

    def __cb_info_get(self, url):
        if not self.__games.has_key(url): return None
        game = self.__games[url]
        if len(game) < 2: # at the start only one element in the dict (the name)
            # get game info from the command: sdlmame -listxml <id>
            # TODO use a better/portable way (but not async)
            os.system('sdlmame -listxml ' + url + ' > /tmp/PyEmc__MAME_tmp')

            # parse the xml file
            doc = xml.dom.minidom.parse('/tmp/PyEmc__MAME_tmp')
            game_node = doc.getElementsByTagName('game')[0]
            if game_node.getAttribute('name') != url: return None

            game['year'] = self.__getTextFromXml(game_node.getElementsByTagName('year'))
            game['manufacturer'] = self.__getTextFromXml(game_node.getElementsByTagName('manufacturer'))

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

        text = 'Year: %s<br>' \
               'Manufacturer: %s<br>' \
               'Players: %s<br>' \
               'Buttons: %s<br>' \
               'Savestate: %s<br>' \
               'Driver status: %s<br>' \
               '   emulation: %s<br>' \
               '   color: %s<br>' \
               '   sound: %s<br>' \
               '   graphic: %s<br>' % \
               (game['year'], game['manufacturer'], game['players'],
                game['buttons'], game['driver_savestate'], game['driver_status'],
                game['driver_emulation'], game['driver_color'],
                game['driver_sound'], game['driver_graphic'])
        return text

    def __getTextFromXml(self, nodelist):
        rc = []
        for node in nodelist:
            for child in node.childNodes:
                if child.nodeType == node.TEXT_NODE:
                    rc.append(child.data)
        return ''.join(rc)

    def __cb_poster_get(self, url):
        if not self.__games.has_key(url): return None

        # check local snapshot...
        snap_file = os.path.join(self.__snapshoot_dir, url, '0000.png')
        if os.path.isfile(snap_file):
            return snap_file

        # ...or donwload the file from progettoemma.it #TODO give credits
        snap_url = 'http://www.progettoemma.net/snap/%s/0000.png' % url
        return snap_url + ';' + snap_file

    def __cb_game_selected(self, id):
        """ A game has been selected, run it """
        print "GAME RUN: " + id

        zip = None
        for dir in self.__rompaths:
            print "DIR" + dir
            path = os.path.join(dir, id) + '.zip'
            if os.path.isfile(path):
                zip = path
            #~ id = rom.strip(".zip")
                #~ if id and self.__games.has_key(id):
                    #~ self.__browser.item_add(id, self.__games[id]['name'])

        if zip:
            os.system('sdlmame ' + zip)
        else:
            self.download_game(id)

    def download_game(self, id):
        print 'Download ' + id
        url = 'http://roms3.freeroms.com/mame_roms/%c/%s.zip' % (id[0], id)

        dest = None
        for dir in self.__rompaths:
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
