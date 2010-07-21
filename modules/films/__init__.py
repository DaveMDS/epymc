#!/usr/bin/env python

import os

import elementary

from modules import EpymcModule
from browser import EpymcBrowser
from sdb import EmcDatabase

import mainmenu
import mediaplayer
import ini
import gui


TMDB_API_KEY = "19eef197b81231dff0fd1a14a8d5f863" # Key of the user DaveMDS


class FilmsModule(EpymcModule):
    name = 'film'
    label = 'Films'

    __browser = None
    __exts = ['.avi', '.mpg', '.mpeg'] #TODO needed? fill!!
    __film_db = None
    __person_db = None
    
    def __init__(self):
        print 'Init module 1: FILM'

        # create config ini section if not exists
        ini.add_section('film')

        # open film/person database (they are created if not exists)
        self.__film_db = EmcDatabase('film')
        self.__person_db = EmcDatabase('person')
        
        # add an item in the mainmenu
        mainmenu.item_add('film', 10, 'Films', None, self.cb_mainmenu)

        # create a browser instance
        self.__browser = EpymcBrowser()

        # connect info panel buttons
        gui.part_get('infopanel_button1').callback_clicked_add(self._cb_panel_1)
        gui.part_get('infopanel_button5').callback_clicked_add(self._cb_panel_5)

    def __del__(self):
        print 'Shutdown module 1: FILM'
        # delete mainmenu item
        mainmenu.item_del('film')

        # delete browser
        del self.__browser

        ## close databases
        del self.__film_db
        del self.__person_db

        # disconnect info panel buttons
        gui.part_get('infopanel_button1').callback_clicked_del(self._cb_panel_1)
        gui.part_get('infopanel_button5').callback_clicked_del(self._cb_panel_5)

    def create_root_page(self):
        self.__browser.page_add("film://root", "Films",
                                item_selected_cb = self._cb_url_selected)

        if len(self.__folders) == 1:
            print "TODO skip first page"
        
        for f in self.__folders:
            self.__browser.item_add(f, os.path.basename(f))
        self.__browser.item_add('emc://back', "Back")

    def cb_mainmenu(self, list, list_item):
        # get film folders from config
        self.__folders = ini.get_string_list('film', 'folders', ';')
        if not self.__folders:
            print "NO FOLDERS"
            #TODO alert the user. and instruct how to add folders
            return

        self.create_root_page()
        mainmenu.hide()
        self.__browser.show()


    def _cb_url_selected(self, url):
        print "EYA!!!!! " + url

        if url.startswith("file://"):
            path = url[7:]
            if os.path.isdir(path):
                self.__browser.page_add(url, os.path.basename(path),
                                    item_selected_cb = self._cb_url_selected,
                                    poster_get_cb = self._cb_poster_get)
                for f in os.listdir(path):
                    self.__browser.item_add("file://" + path + "/" + f, f)
                self.__browser.item_add("emc://back", "Back")
            else:
                self.show_film_info(url)
                #~ mediaplayer.play_url(url)

        elif url == "film://root":
            self.create_root_page()

    def _cb_poster_get(self, url):
        print "poster " + url

        if self.__film_db.id_exist('url'):
            print 'Found in DB'
        else:
            print 'Not found'
            #~ self.__tmdb(url)

    def show_film_info(self, url):
        self.update_film_info(url)
        self.__current_url = url
        gui.signal_emit("infopanel,show")

    def update_film_info(self, url):
        print "Update info"
        if self.__film_db.id_exists(url):
            print 'Found: ' + url
            e = self.__film_db.get_data(url)
            import pprint
            pprint.pprint(e)

            director = "Unknow"
            cast = ""
            for person in e['cast']:
                print " CAST: " + person['job']
                if person['job'] == 'Director':
                    director = person['name']
                elif person['job'] == 'Actor':
                    cast += (', ' if cast else '') + person['name']
            info = "<title>" + e['name'] + "</title> <year>(" + e['released'][0:4] + ")</year><br>" + \
                   "<hilight>Director: </hilight>" + director + "<br>" + \
                   "<hilight>Cast: </hilight>" + cast + "<br>" + \
                   "<hilight>Rating: </hilight>" + str(e['rating']) + "/10<br>" + \
                   "<br><hilight>Overview:</hilight><br>" + e['overview']
            gui.part_get('infopanel_text').text_set(info)
        else:
            # TODO print also file size, video len, codecs, streams found, file metadata, etc..
            msg = "Media:<br>" + url + "<br><br>" + \
                  "No info stored for this media<br>" + \
                  "Try the GetInfo button..."
            gui.part_get('infopanel_text').text_set(msg)
            # TODO make thumbnail

    def _cb_panel_1(self, button):
        self.update_film_info(self.__current_url)
        
    def _cb_panel_5(self, button):
        self.tmdb_film_search(self.__current_url)

    def get_film_name_from_url(self, url):
        # remove path
        film = os.path.basename(url)
        # remove extension
        (film, ext) = os.path.splitext(film)
        # TODO remove stuff between '[' and ']'
        return film
        
    def tmdb_film_search(self, url):
        import pprint
        
        film = self.get_film_name_from_url(url)
        print "Search for : " + film
        
        tmdb = TMDB(TMDB_API_KEY, 'json', 'en', True)
        data = tmdb.searchResults(film)

        if len(data) > 1:
            print 'TODO Show a list to choose from'

        movie_info = tmdb.getInfo(data[0]['id'])
        pprint.pprint(movie_info)

        # store the result in db
        self.__film_db.set_data(url, movie_info[0])

        # TODO download cover and fanart
        #~ print movie_info['posters'] # TODO choose the right size
        #~ print movie_info['backdrops'] # TODO choose the right size
        
        #~ for res in data:
            #~ print " * %s [%d]" % (res['name'], res['id'])

###############################################################################
#    themoviedb.org  client implementation taken from:
#  http://forums.themoviedb.org/topic/1092/my-contribution-tmdb-api-wrapper-python/
#
#  Credits goes to globald
###############################################################################
import urllib
import json

class TMDB(object):

    def __init__(self, api_key, view='xml', lang='en', decode = False):
        ''' TMDB Client '''
        #view = yaml json xml
        self.lang = lang
        self.view = view
        self.decode = decode if view == 'json' else False
        self.key = api_key
        self.server = 'http://api.themoviedb.org'

    def socket(self, url):
        ''' Return URL Content '''
        print url
        data = None
        try:
            client = urllib.urlopen(url)
            data = client.read()
            client.close()
        except: pass

        if data and self.decode:
            #~ return json.dumps(data, indent = 4)
            return json.loads(data)
        else:
            return data

    def method(self, look, term):
        ''' Methods => search, imdbLookup, getInfo, getImages'''
        print "look: %s  term: %s" % (look, term)
        do = 'Movie.'+look
        term = str(term) # int conversion
        run = self.server+'/2.1/'+do+'/'+self.lang+'/'+self.view+'/'+self.key+'/'+term
        return run
        
    def method_people(self, look, term):
        ''' Methods => search, getInfo '''

        do = 'Person.'+look
        term = str(term) # int conversion
        run = self.server+'/2.1/'+do+'/'+self.lang+'/'+self.view+'/'+self.key+'/'+term
        return run

    def personResults(self, term):
        ''' Person Search Wrapper '''
        return self.socket(self.method_people('search',term))

    def person_getInfo(self, personId):
        ''' Person GetInfo Wrapper '''
        return self.socket(self.method_people('getInfo',personId))

    def searchResults(self, term):
        ''' Search Wrapper '''
        return self.socket(self.method('search',term))

    def getInfo(self, tmdb_Id):
        ''' GetInfo Wrapper '''
        return self.socket(self.method('getInfo',tmdb_Id))

    def imdbResults(self, titleTTid):
        ''' IMDB Search Wrapper '''
        return self.socket(self.method('imdbLookup',titleTTid))

    def imdbImages(self, titleTTid):
        ''' IMDB Search Wrapper '''
        titleTTid = 'tt0'+str(titleTTid)
        return self.socket(self.method('getImages',titleTTid))

    def tmdbImages(self, tmdb_Id):
        ''' GetInfo Wrapper '''
        return self.socket(self.method('getImages',tmdb_Id))
