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

    def __del__(self):
        print 'Shutdown module 1: FILM'
        # delete mainmenu item
        mainmenu.item_del('film')

        # delete browser
        del self.__browser

        ## close databases
        del self.__film_db
        del self.__person_db


###### BROWSER STUFF
    def cb_mainmenu(self):
        # get film folders from config
        self.__folders = ini.get_string_list('film', 'folders', ';')
        if not self.__folders:
            print "NO FOLDERS"
            #TODO alert the user. and instruct how to add folders
            return

        self.create_root_page()
        mainmenu.hide()
        self.__browser.show()

    def create_root_page(self):
        self.__browser.page_add("film://root", "Films",
                                item_selected_cb = self.cb_url_selected)

        if len(self.__folders) == 1:
            print "TODO skip first page"
        
        for f in self.__folders:
            self.__browser.item_add(f, os.path.basename(f))
        self.__browser.item_add('emc://back', "Back")

    def cb_url_selected(self, url):
        if url.startswith("file://"):
            path = url[7:]
            if os.path.isdir(path):
                self.__browser.page_add(url, os.path.basename(path),
                                    item_selected_cb = self.cb_url_selected,
                                    poster_get_cb = self.cb_poster_get)
                for f in os.listdir(path):
                    self.__browser.item_add("file://" + path + "/" + f, f)
                self.__browser.item_add("emc://back", "Back")
            else:
                self.show_film_info(url)
                #~ mediaplayer.play_url(url)

        elif url == "film://root":
            self.create_root_page()

    def cb_poster_get(self, url):
        if self.__film_db.id_exists(url):
            e = self.__film_db.get_data(url)
            poster = get_poster_filename(e['id'])
            if os.path.exists(poster):
                return poster
        else:
            print 'Not found'


###### INFO PANEL STUFF
    def show_film_info(self, url):
        self.update_film_info(url)
        self.__current_url = url

        # connect info panel buttons callbacks
        gui.part_get('infopanel_button1').callback_clicked_add(self._cb_panel_1)
        gui.part_get('infopanel_button2').callback_clicked_add(self._cb_panel_2)
        gui.part_get('infopanel_button3').callback_clicked_add(self._cb_panel_3)
        gui.part_get('infopanel_button4').callback_clicked_add(self._cb_panel_4)
        gui.part_get('infopanel_button5').callback_clicked_add(self._cb_panel_5)
        gui.part_get('infopanel_button6').callback_clicked_add(self._cb_panel_6)

        gui.signal_emit("infopanel,show")

    def hide_film_info(self):
         # disconnect info panel buttons callbacks
        gui.part_get('infopanel_button1').callback_clicked_del(self._cb_panel_1)
        gui.part_get('infopanel_button2').callback_clicked_del(self._cb_panel_2)
        gui.part_get('infopanel_button3').callback_clicked_del(self._cb_panel_3)
        gui.part_get('infopanel_button4').callback_clicked_del(self._cb_panel_4)
        gui.part_get('infopanel_button5').callback_clicked_del(self._cb_panel_5)
        gui.part_get('infopanel_button6').callback_clicked_del(self._cb_panel_6)

        gui.signal_emit("infopanel,hide")

    def update_film_info(self, url):
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
            poster = get_poster_filename(e['id'])
            if os.path.exists(poster):
                gui.part_get('infopanel_image').file_set('') # this is to force a reload also if the filename is the same
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

    def get_film_name_from_url(self, url):
        # remove path
        film = os.path.basename(url)
        # remove extension
        (film, ext) = os.path.splitext(film)
        # TODO remove stuff between '[' and ']'
        return film
        
    def _cb_panel_1(self, button):
        mediaplayer.play_video(self.__current_url)
        self.hide_film_info()

    def _cb_panel_2(self, button):
        if self.__film_db.id_exists(self.__current_url):
            film_info = self.__film_db.get_data(self.__current_url)

            # create the cast list
            li = elementary.List(gui._win)
            for person in film_info['cast']:
                if person['job'] == 'Actor':
                    label = person['name'] + ' as ' + person['character']
                    li.item_append(label, None, None, None, None)

            li.show()
            li.go()
            li.size_hint_min_set(300, 300) #TODO FIXME

            # put the list ia a dialog
            dialog = EmcDialog(title = 'Cast', content = li)
            dialog.button_add('Close', self._cb_cast_close, dialog)
            dialog.activate()

    def _cb_cast_close(self, button, dialog):
        # kill the dialog
        dialog.delete()
        del dialog

########
    def _cb_panel_3(self, button):
        if self.__film_db.id_exists(self.__current_url):
            film_info = self.__film_db.get_data(self.__current_url)

            # create a list of posters
            images = []
            for image in film_info['posters']:
                if image['image']['size'] == 'thumb':
                    print image['image']['url']
                    images.append(image['image'])

            # show the list in a dialog
            li = elementary.List(gui._win)
            for image in images:
                icon = EmcRemoteImage(li)
                icon.url_set(image['url'])
                icon.size_hint_min_set(100, 100) # TODO fixme
                #~ label = res['name'] + ' (' + res['released'][:4] + ')'
                mid = image['url'][:-9]
                mid = mid + 'mid.jpg'
                li.item_append(" ", icon, None, None, (mid, film_info['id']))

            li.show()
            li.go()
            li.size_hint_min_set(300, 300) #TODO FIXME
            
            dialog = EmcDialog(title = 'Choose a poster.', content = li)
            dialog.button_add('Cancel', self._cb_poster_cancel, dialog)
            dialog.button_add('Ok', self._cb_poster_ok, dialog)
            dialog.activate()
    
    def _cb_poster_cancel(self, button, dialog):
        # kill the dialog
        dialog.delete()
        del dialog
    
    def _cb_poster_ok(self, button, dialog):
        li = dialog.content_get()
        item = li.selected_item_get()
        if not item: return

        self.__poster_dialog = dialog
        (url, id) = item.data_get()[0][0]
        dest = get_poster_filename(id)
        downloader.download_url_async(url, dest, self._cb_poster_done)

        # kill the dialog
        self.__poster_dialog.delete()
        del self.__poster_dialog

        # make a spinner dialog
        self.__poster_dialog = EmcDialog(title = "Downloading Poster",
                                         spinner = True)
        self.__poster_dialog.activate()

    def _cb_poster_done(self, url, dest, headers):
        # kill the dialog
        self.__poster_dialog.delete()
        del self.__poster_dialog

        self.update_film_info(self.__current_url)

########
    def _cb_panel_4(self, button):
        if self.__film_db.id_exists(self.__current_url):
            film_info = self.__film_db.get_data(self.__current_url)

            # create a list of backdrops
            images = []
            for image in film_info['backdrops']:
                if image['image']['size'] == 'thumb':
                    #~ print image['image']['url']
                    images.append(image['image'])

            # show the list in a dialog
            li = elementary.List(gui._win)
            for image in images:
                icon = EmcRemoteImage(li)
                icon.url_set(image['url'])
                icon.size_hint_min_set(100, 100) # TODO fixme
                #~ label = res['name'] + ' (' + res['released'][:4] + ')'
                mid = image['url'][:-9]
                mid = mid + 'mid.jpg'
                li.item_append(" ", icon, None, None, (mid, film_info['id']))

            li.show()
            li.go()
            li.size_hint_min_set(300, 300) #TODO FIXME
            
            dialog = EmcDialog(title = 'Choose a Fanart.', content = li)
            dialog.button_add('Cancel', self._cb_backdrop_cancel, dialog)
            dialog.button_add('Ok', self._cb_backdrop_ok, dialog)
            dialog.activate()
    
    def _cb_backdrop_cancel(self, button, dialog):
        # kill the dialog
        dialog.delete()
        del dialog
    
    def _cb_backdrop_ok(self, button, dialog):
        li = dialog.content_get()
        item = li.selected_item_get()
        if not item: return

        self.__backdrop_dialog = dialog
        (url, id) = item.data_get()[0][0]
        dest = get_backdrop_filename(id)
        downloader.download_url_async(url, dest, self._cb_backdrop_done)

        # kill the dialog
        self.__backdrop_dialog.delete()
        del self.__backdrop_dialog

        # make a spinner dialog
        self.__backdrop_dialog = EmcDialog(title = "Downloading Fanart",
                                           spinner = True)
        self.__backdrop_dialog.activate()

    def _cb_backdrop_done(self, url, dest, headers):
        # kill the dialog
        self.__backdrop_dialog.delete()
        del self.__backdrop_dialog
        #~ self.update_film_info(self.__current_url)

###############
    def _cb_panel_5(self, button):
        tmdb = TMDB2(TMDB_API_KEY)
        film = self.get_film_name_from_url(self.__current_url)
        tmdb.film_search(film, self._cb_search_complete)

    def _cb_search_complete(self, tmdb, movie_info):
        # free TMDB2 object
        del tmdb
        # store the result in db
        self.__film_db.set_data(self.__current_url, movie_info)
        # update info panel
        self.update_film_info(self.__current_url)

    def _cb_panel_6(self, button):
        self.hide_film_info()


###### UTILS
def get_poster_filename(tmdb_id):
    return os.path.join(utils.config_dir_get(), 'film',
                        str(tmdb_id), 'poster.jpg')

def get_backdrop_filename(tmdb_id):
    return os.path.join(utils.config_dir_get(), 'film',
                        str(tmdb_id), 'backdrop.jpg')
    

###############################################################################
import urllib
import json

class TMDB2(object):

    def __init__(self, api_key):
        ''' TMDB2 Client '''
        self.key = api_key
        self.lang = 'en'
        self.server = 'http://api.themoviedb.org/2.1/'
## FILM SEARCH
    def film_search(self, film, complete_cb = None):
        print "Search2 for : " + film

        self.complete_cb = complete_cb
        query = self.server+'Movie.search/'+self.lang+'/json/'+self.key+'/'+film

        self.dialog = EmcDialog(title = "Searching for: " + film,
                                spinner = True)
        self.dialog.activate()

        print "query: " + query
        downloader.download_url_async(query, None, self._cb_search_done)
    
    def _cb_search_done(self, url, dest, headers):
        data = json.loads(dest)

        # kill spinner dialog
        self.dialog.delete()
        del self.dialog

        if len(data) == 1:
            # just one result, assume is the correct one
            self.film_get_info(data[0]['id'])

        elif len(data) > 1:
            # create a list dialog to choose from results
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
        # get selected item id
        li = dialog.content_get()
        item = li.selected_item_get()
        id = item.data_get()[0][0]
        if not item or not id: return

        # kill the dialog
        dialog.delete()
        del dialog
        
        # download film info + images
        self.film_get_info(id)

## FILM GET INFO
    def film_get_info(self, id):
        print "Get Film Info: " + str(id)

        query = self.server+'Movie.getInfo/'+self.lang+'/json/'+self.key+'/'+str(id)

        self.dialog = EmcDialog(title = "Downloading film info",
                                spinner = True)
        self.dialog.activate()

        downloader.download_url_async(query, None, self._cb_film_info_done)

    def _cb_film_info_done(self, url, dest, headers):
        data = json.loads(dest)
        self.movie_info = data[0]

        # download the first poster image found
        for image in self.movie_info['posters']:
            if image['image']['size'] == 'mid': # TODO make default size configurable
                dest = get_poster_filename(self.movie_info['id'])
                downloader.download_url_async(image['image']['url'], dest,
                                              self._cb_film_poster_done)
                return

        # if no poster found go to next step
        self._cb_film_poster_done(url, dest, headers)
        
    def _cb_film_poster_done(self, url, dest, headers):
        # download the first backdrop image found
        for image in self.movie_info['backdrops']:
            if image['image']['size'] == 'original': # TODO make default size configurable
                dest = get_backdrop_filename(self.movie_info['id'])
                downloader.download_url_async(image['image']['url'], dest,
                                              self._cb_film_backdrop_done)
                return

        # if no backdrop found go to next step
        self._cb_film_backdrop_done(url, dest, headers)

    def _cb_film_backdrop_done(self, url, dest, headers):
        # kill the spinner dialog
        self.dialog.delete()
        del self.dialog

        if self.complete_cb:
            self.complete_cb(self, self.movie_info)

    
###############################################################################
#    themoviedb.org  client implementation taken from:
#  http://forums.themoviedb.org/topic/1092/my-contribution-tmdb-api-wrapper-python/
#  With a little modification by me to support json decode.
#
#  Credits goes to globald
#  Unused atm (in favor of the async one 
###############################################################################


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
