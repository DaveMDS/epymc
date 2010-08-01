#!/usr/bin/env python

import os
#~ 
import ecore
#~ import evas
#~ import elementary
#~ 
from modules import EpymcModule
from browser import EpymcBrowser
#~ from sdb import EmcDatabase
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
        #~ self.__film_db = EmcDatabase('film')
        
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
        #~ del self.__film_db


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
        thread = UpdateDBThread(self.__folders)
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
        self.__browser.item_add('music://albums', 'Albums (TODO)')
        self.__browser.item_add('music://songs', 'Songs (TODO)')
        self.__browser.item_add('music://generes', 'Generes (TODO)')
        self.__browser.item_add('music://playlists', 'Playlists (TODO)')
        self.__browser.item_add('emc://back', 'Back')

    def cb_root_selected(self, url):
        print "ROOT SEL: " + url




from mutagen.easyid3 import EasyID3

class UpdateDBThread(threading.Thread):

    def __init__(self, folders):
        threading.Thread.__init__(self)
        self.folders = folders

    def run(self):
        global _audio_extensions
        
        print 'This is thread  speaking.'
        print 'Hello and good bye.'
        print self.folders
        for folder in self.folders:
            # strip url
            if folder.find('://', 0, 16) > 0:
                folder = folder[folder.find('://')+3:]

            print 'Scanning dir ' + folder + ' ...'
            count = 5
            for root, dirs, files in os.walk(folder):
                #~ print '##################'
                #~ print root
                #~ print dirs
                #~ print files
                for file in files:
                    (filename, ext) = os.path.splitext(file)
                    if ext in _audio_extensions:
                        path = os.path.join(root, file)
                        #~ print "FILE: " + path
                        print ''
                        print count
                        self.read_metadata(path)
                        
                        count -= 1 # TODO REMOVE ME
                        if count < 1:# TODO REMOVE ME
                            return # TODO REMOVE ME
                    else:
                        print "INVALID: " + file

    def read_metadata(self, full_path):
        print "GET METADATA FOR: " + full_path

        meta = EasyID3(full_path)

        import pprint
        pprint.pprint(meta)
        print meta['title'][0]
        #~ print meta['album']
        print meta['artist'][0]
        
        #~ print EasyID3.valid_keys.keys()

