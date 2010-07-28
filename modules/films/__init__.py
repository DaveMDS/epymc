#!/usr/bin/env python

import os

import evas
import elementary

from modules import EpymcModule
from browser import EpymcBrowser
from sdb import EmcDatabase
from gui import EmcDialog
from gui import EmcRemoteImage

import mainmenu
import mediaplayer
import ini
import utils
import downloader
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

        # connect info panel buttons callback
        gui.part_get('infopanel_button1').callback_clicked_add(self._cb_panel_1)
        gui.part_get('infopanel_button5').callback_clicked_add(self._cb_panel_5)
        gui.part_get('infopanel_button6').callback_clicked_add(self._cb_panel_6)

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
        gui.part_get('infopanel_button6').callback_clicked_del(self._cb_panel_6)

    def create_root_page(self):
        self.__browser.page_add("film://root", "Films",
                                item_selected_cb = self._cb_url_selected)

        if len(self.__folders) == 1:
            print "TODO skip first page"
        
        for f in self.__folders:
            self.__browser.item_add(f, os.path.basename(f))
        self.__browser.item_add('emc://back', "Back")

    def cb_mainmenu(self, list, list_item):
        #### TESTING
        #~ mediaplayer.play_video('/home/dave/Films/Alien.avi')
        #~ return
        #####
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
        if self.__film_db.id_exists(url):
            e = self.__film_db.get_data(url)
            poster = self.get_poster_filename(e['id'])
            if os.path.exists(poster):
                return poster
        else:
            print 'Not found'
            #~ self.__tmdb(url)

    def show_film_info(self, url):
        self.update_film_info(url)
        self.__current_url = url
        gui.signal_emit("infopanel,show")

    def hide_film_info(self):
        gui.signal_emit("infopanel,hide")

    def update_film_info(self, url):
        print "Update info"
        if self.__film_db.id_exists(url):
            print 'Found: ' + url
            e = self.__film_db.get_data(url)
            import pprint
            pprint.pprint(e)

            # update text info
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
            gui.part_get('infopanel_text').text_set(info.encode('utf-8'))

            # update poster
            poster = self.get_poster_filename(e['id'])
            if os.path.exists(poster):
                gui.part_get('infopanel_image').file_set(poster)
            else:
                print 'TODO show a dummy image'
                gui.part_get('infopanel_image').file_set('')
        else:
            # TODO print also file size, video len, codecs, streams found, file metadata, etc..
            msg = "Media:<br>" + url + "<br><br>" + \
                  "No info stored for this media<br>" + \
                  "Try the GetInfo button..."
            gui.part_get('infopanel_text').text_set(msg)
            # TODO make thumbnail
            gui.part_get('infopanel_image').file_set('')

    def _cb_panel_1(self, button):
        mediaplayer.play_video(self.__current_url)
        self.hide_film_info()

    def _cb_panel_5(self, button):
        self.tmdb_film_search(self.__current_url)
        
    def _cb_panel_6(self, button):
        self.hide_film_info()

    def get_film_name_from_url(self, url):
        # remove path
        film = os.path.basename(url)
        # remove extension
        (film, ext) = os.path.splitext(film)
        # TODO remove stuff between '[' and ']'
        return film

    def get_poster_filename(self, tmdb_id):
        return os.path.join(utils.config_dir_get(), 'film',
                            str(tmdb_id), 'poster.jpg')

    def get_backdrop_filename(self, tmdb_id):
        return os.path.join(utils.config_dir_get(), 'film',
                            str(tmdb_id), 'backdrop.jpg')
    
    def tmdb_film_search(self, url):
        film = self.get_film_name_from_url(url)
        print "Search for : " + film

        tmdb = TMDB(TMDB_API_KEY, 'json', 'en', True)
        data = tmdb.searchResults(film)

        if len(data) == 1:
            # just one result, use that
            self.tmdb_film_get_info(data[0]['id'])

        elif len(data) > 1:
            # Create a list dialog to choose from results
            li = elementary.List(gui._win)
            for res in data:
                icon = None
                for image in res['posters']:
                    if image['image']['size'] == 'thumb' and image['image']['url']:
                        icon = EmcRemoteImage(li)
                        icon.url_set(image['image']['url'])
                        icon.size_hint_min_set(100, 100) # TODO fixme
                        break
                label = res['name'] + ' (' + res['released'][:4] + ')'
                li.item_append(label, icon, None, None, res['id'])
            li.show()
            li.go()
            li.size_hint_min_set(300, 300) #TODO FIXME
            
            dialog = EmcDialog(title = 'Found ' + str(len(data))+' results, please choose the right one.',
                               content = li)
            dialog.button_add('Cancel', self._cb_search_cancel, dialog)
            dialog.button_add('Ok', self._cb_search_ok, dialog)
            dialog.activate()

    def _cb_search_cancel(self, button, dialog):
        dialog.delete()
        del dialog

    def _cb_search_ok(self, button, dialog):
        li = dialog.content_get()
        item = li.selected_item_get()
        id = item.data_get()[0][0]
        self.tmdb_film_get_info(id)

    def tmdb_film_get_info(self, tmdb_id):
        print tmdb_id
        print self.__current_url

        tmdb = TMDB(TMDB_API_KEY, 'json', 'en', True)

        movie_info = tmdb.getInfo(tmdb_id)
        movie_info = movie_info[0]

        # store the result in db
        self.__film_db.set_data(self.__current_url, movie_info)

        # download the first poster image found
        for image in movie_info['posters']:
            if image['image']['size'] == 'mid': # TODO make default size configurable
                dest = self.get_poster_filename(movie_info['id'])
                downloader.download_url_async(image['image']['url'], dest)
                break

        # download the first backdrop image found
        for image in movie_info['backdrops']:
            if image['image']['size'] == 'original': # TODO make default size configurable
                dest = self.get_backdrop_filename(movie_info['id'])
                downloader.download_url_async(image['image']['url'], dest)
                break
    
    

###############################################################################
#    themoviedb.org  client implementation taken from:
#  http://forums.themoviedb.org/topic/1092/my-contribution-tmdb-api-wrapper-python/
#  With a little modification by me to support json decode.
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
