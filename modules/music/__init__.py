#!/usr/bin/env python

import os
#~ 
import ecore
#~ import evas
#~ import elementary
#~ 
from modules import EpymcModule
from browser import EpymcBrowser
from sdb import EmcDatabase
from gui import EmcDialog

import mainmenu
import ini
import threading



_audio_extensions = ['.mp3', '.MP3']


class MusicModule(EpymcModule):
    name = 'music'
    label = 'Music'

    __browser = None
    #~ __film_db = None
    
    def __init__(self):
        print 'Init module: MUSIC'

        # create config ini section if not exists
        ini.add_section('music')

        # open film/person database (they are created if not exists)
        self.__songs_db = EmcDatabase('music_songs')
        self.__albums_db = EmcDatabase('music_albums')
        
        # add an item in the mainmenu
        mainmenu.item_add('music', 5, 'Music', None, self.cb_mainmenu)

        # create a browser instance
        self.__browser = EpymcBrowser()

    def __del__(self):
        print 'Shutdown module: MUSIC'
        # delete mainmenu item
        mainmenu.item_del('music')

        # delete browser
        del self.__browser

        ## close databases
        del self.__songs_db
        del self.__albums_db


    def cb_mainmenu(self):
        # get music folders from config
        self.__folders = ini.get_string_list('music', 'sources', ';')
        if not self.__folders:
            print "NO FOLDERS"
            #TODO alert the user. and instruct how to add folders
            return

        self.create_root_page()
        mainmenu.hide()
        self.__browser.show()

        # Update db in a parallel thread
        self.dialog = EmcDialog(title = 'Rebuilding Database, please wait...',
                           spinner = True)
        self.dialog.activate()
        thread = UpdateDBThread(self.__folders, self.__songs_db, self.__albums_db)
        thread.start()
        ecore.Timer(0.5, self.check_thread_done, thread)

    def check_thread_done(self, thread):
        if thread.is_alive():
            return True # renew the timer callback


        print 'Donw'
        self.dialog.delete()
        del self.dialog
        
        return False # kill the timer
        
    def create_root_page(self):
        self.__browser.page_add("music://root", "Music",
                                item_selected_cb = self.cb_root_selected)
        
        #~ for f in self.__folders:
            #~ self.__browser.item_add(f, os.path.basename(f))
        self.__browser.item_add('music://artists', 'Artists (TODO)')
        self.__browser.item_add('music://albums', 'Albums')
        self.__browser.item_add('music://songs', 'Songs')
        self.__browser.item_add('music://generes', 'Generes (TODO)')
        self.__browser.item_add('music://playlists', 'Playlists (TODO)')
        self.__browser.item_add('emc://back', 'Back')

    def cb_root_selected(self, url):
        print "ROOT SEL: " + url

        if url == 'music://root':
            self.create_root_page()

        elif url == 'music://songs':
            self.__browser.page_add(url, "Songs")
                       #~ item_selected_cb = self.__cb_game_selected,
                       #~ poster_get_cb = self.__cb_poster_get,
                       #~ info_get_cb = self.__cb_info_get)

            for key in self.__songs_db.keys():
                print key
                item_data = self.__songs_db.get_data(key)
                print item_data
                self.__browser.item_add(key, item_data['title'])

        elif url == 'music://albums':
            self.__browser.page_add(url, "Albums",
                       item_selected_cb = self.cb_album_selected,
                       poster_get_cb = self.cb_album_poster_get)
                       #~ info_get_cb = self.__cb_info_get)

            for key in self.__albums_db.keys():
                print key
                album_data = self.__albums_db.get_data(key)
                print album_data
                label = album_data['name'] + '  by ' + album_data['artist']
                self.__browser.item_add(key, label)

    def cb_album_selected(self, album):
        print album
        album_data = self.__albums_db.get_data(album)

        import pprint
        pprint.pprint(album_data)

    def cb_album_poster_get(self, album):
        print 'poster get ' + album
        album_data = self.__albums_db.get_data(album)
        print album_data['name']
        print album_data['artist']

        # TODO FIX PATH !!!!!!!!!!!!!!!!!
        ret = '/home/dave/.cache/rhythmbox/covers/%s - %s.jpg' % \
              (album_data['artist'],  album_data['name'])
        if os.path.exists(ret):
            return ret
        else:
            return None

from mutagen.easyid3 import EasyID3

class UpdateDBThread(threading.Thread):

    def __init__(self, folders, songs_db, albums_db):
        threading.Thread.__init__(self)
        self.folders = folders
        self.songs_db = songs_db
        self.albums_db = albums_db

    def run(self):
        global _audio_extensions
        
        print 'This is the thread speaking, HALO'

        for folder in self.folders:
            # strip url
            if folder.find('://', 0, 16) > 0:
                folder = folder[folder.find('://')+3:]

            print 'Scanning dir ' + folder + ' ...'
            count = 50 # TODO REMOVE ME

            for root, dirs, files in os.walk(folder):
                for file in files:
                    (filename, ext) = os.path.splitext(file)
                    if ext in _audio_extensions:
                        path = os.path.join(root, file)

                        print '' # TODO REMOVE ME
                        print count # TODO REMOVE ME

                        if self.songs_db.id_exists(path):
                            print "FOUND IN DB"
                        else:
                            self.read_metadata(path)
                        
                        #~ count -= 1 # TODO REMOVE ME
                        #~ if count < 1:# TODO REMOVE ME
                            #~ return # TODO REMOVE ME
                    else:
                        print "INVALID: " + file

    def read_metadata(self, full_path):
        print "GET METADATA FOR: " + full_path

        meta = EasyID3(full_path)

        import pprint
        pprint.pprint(meta)

        item_data = dict()

        item_data['url'] = full_path #TODO need to use a real url?

        if meta.has_key('title'):
            item_data['title'] = meta['title'][0].encode('utf-8') # TODO is the encode correct? doesn't evas support unicode now?? 
        else:
            item_data['title'] = full_path # TODO just file name


        if meta.has_key('artist'):
            item_data['artist'] = meta['artist'][0].encode('utf-8')
        else:
            item_data['artist'] = 'Unknow'


        if meta.has_key('tracknumber'):
            item_data['tracknumber'] = meta['tracknumber'][0].encode('utf-8')


        if meta.has_key('album'):
            item_data['album'] = meta['album'][0].encode('utf-8')

            # create album item if necesary
            if not self.albums_db.id_exists(item_data['album']):
                print 'NEW ALBUM: ' + item_data['album']
                album_data = dict()
                album_data['name'] = item_data['album']
                album_data['artist'] = item_data['artist']
                album_data['songs'] = list()
            else:
                print 'ALBUM EXIST'
                album_data = self.albums_db.get_data(item_data['album'])

            # add song to song list (in album), only if not exists yet
            if not full_path in album_data['songs']:
                album_data['songs'].append(full_path)

            # write album to db
            self.albums_db.set_data(item_data['album'], album_data, thread_safe = False) # TODO thread_safe = True

        # write song to db
        self.songs_db.set_data(full_path, item_data, thread_safe = False) # TODO thread_safe = True

