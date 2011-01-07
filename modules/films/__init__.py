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

import evas
import elementary

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser
from epymc.sdb import EmcDatabase
from epymc.gui import EmcDialog
from epymc.gui import EmcRemoteImage

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.ini as ini
import epymc.utils as utils
import epymc.gui as gui


def DBG(msg):
   #~ print('FILM: ' + msg)
   pass

TMDB_API_KEY = "19eef197b81231dff0fd1a14a8d5f863" # Key of the user DaveMDS


class FilmsModule(EmcModule):
   name = 'film'
   label = 'Films'
   icon = 'icon/module'
   info = """Long info for the film module, explain what it does and what it 
need to work well, can also use markup like <title>this</> or <b>this</>"""

   __browser = None
   __exts = ['.avi', '.mpg', '.mpeg'] #TODO needed? fill!!
   __film_db = None
   __person_db = None

   def __init__(self):
      DBG('Init module')

      # create config ini section if not exists
      ini.add_section('film')

      # open film/person database (they are created if not exists)
      self.__film_db = EmcDatabase('film')
      self.__person_db = EmcDatabase('person')

      # add an item in the mainmenu
      mainmenu.item_add('film', 10, 'Films', None, self.cb_mainmenu)

      # create a browser instance
      self.__browser = EmcBrowser('Films', 'List',
                              item_selected_cb = self.cb_url_selected,
                              icon_get_cb = self.cb_icon_get,
                              poster_get_cb = self.cb_poster_get,
                              fanart_get_cb = self.cb_fanart_get,
                              info_get_cb = self.cb_info_get)

   def __shutdown__(self):
      DBG('Shutdown module')
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

      # if not self.__folders:
         #TODO alert the user. and instruct how to add folders

      self.create_root_page()
      mainmenu.hide()
      self.__browser.show()

   def create_root_page(self):
      self.__browser.page_add("film://root", "Films")

      if len(self.__folders) == 1:
         print "TODO skip first page"

      for f in self.__folders:
         self.__browser.item_add(f, os.path.basename(f))
      
      self.__browser.item_add('film://add_source', 'Add source');

   def cb_url_selected(self, page_url, item_url):
      if item_url.startswith("file://"):
         path = item_url[7:]
         if os.path.isdir(path):
            self.__browser.page_add(item_url, os.path.basename(path))
            for f in os.listdir(path):
               self.__browser.item_add("file://" + path + "/" + f, f)
         else:
            self.show_film_info(item_url)

      elif item_url == "film://root":
         self.create_root_page()
      elif item_url == "film://add_source":
         EmcDialog(text="Source Browser").activate()

   def cb_icon_get(self, page_url, item_url):
      if item_url.startswith("file://"):
         if self.__film_db.id_exists(item_url):
            return None
      elif (item_url == 'film://add_source'):
         return 'icon/plus'
      return "icon/folder"

   def cb_poster_get(self, page_url, item_url):
      if self.__film_db.id_exists(item_url):
         e = self.__film_db.get_data(item_url)
         poster = get_poster_filename(e['id'])
         if os.path.exists(poster):
            return poster
      else:
         return None

   def cb_fanart_get(self, page_url, item_url):
      if self.__film_db.id_exists(item_url):
         e = self.__film_db.get_data(item_url)
         fanart = get_backdrop_filename(e['id'])
         if os.path.exists(fanart):
            return fanart
      else:
         return None

   def cb_info_get(self, page_url, item_url):
      if self.__film_db.id_exists(item_url):
         e = self.__film_db.get_data(item_url)
         text = '<title>%s (%s %s)</><br>' \
                '<hilight>Rating:</> %.0f/10<br>' \
                '<hilight>Director:</> %s<br>' \
                '<hilight>Cast:</> %s<br>%s' % \
                (e['name'], e['countries'][0]['code'], e['released'][:4],
                e['rating'], self._get_director(e), self._get_cast(e, 3),
                e['overview'])
                # TODO genres
         return text
      else:
         return 'Not found'

   def _get_director(self,e):
      for person in e['cast']:
         if person['job'] == 'Director':
            return person['name']
      return "Unknow"
      
   def _get_cast(self, e, max_num = 99): # TODO make max_num works
      cast = ''
      for person in e['cast']:
         if person['job'] == 'Actor':
            cast = cast + (', ' if cast else '') + person['name']
      return cast
      

###### INFO PANEL STUFF
   def show_film_info(self, url):
      self.__current_url = url

      box = elementary.Box(gui.win)
      box.horizontal_set(1)
      box.homogenous_set(1)
      box.show()

      image = elementary.Image(gui.win)
      image.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      image.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      image.show()
      box.pack_end(image)

      sentry = elementary.ScrolledEntry(gui.win)
      sentry.style_set("dialog")
      sentry.editable_set(False)
      sentry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      sentry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      sentry.show()
      box.pack_end(sentry)

      dialog = EmcDialog(style = 'default', content = box)
      dialog.button_add('Play', self._cb_panel_1)
      dialog.button_add('Cast', self._cb_panel_2)
      dialog.button_add('Choose Poster', self._cb_panel_3)
      dialog.button_add('Choose Fanart', self._cb_panel_4)
      dialog.button_add('Search Info', self._cb_panel_5)
      dialog.button_add('Close', self._cb_panel_6)

      dialog.data['o_image'] = image
      dialog.data['o_sentry'] = sentry
      self._dialog = dialog

      dialog.activate()

      self.update_film_info(url)

   def hide_film_info(self):
      self._dialog.delete()
      del self._dialog

   def update_film_info(self, url):
      o_image = self._dialog.data['o_image']
      o_sentry = self._dialog.data['o_sentry']

      if self.__film_db.id_exists(url):
         print 'Found: ' + url
         e = self.__film_db.get_data(url)
         #~ import pprint
         #~ pprint.pprint(e)

         # update text info
         info = "<title>" + e['name'] + "</title> <year>(" + e['released'][0:4] + ")</year><br>" + \
                  "<hilight>Director: </hilight>" + self._get_director(e) + "<br>" + \
                  "<hilight>Cast: </hilight>" + self._get_cast(e) + "<br>" + \
                  "<hilight>Rating: </hilight>" + str(e['rating']) + "/10<br>" + \
                  "<br><hilight>Overview:</hilight><br>" + e['overview']
         o_sentry.entry_set(info.encode('utf-8'))

         # update poster
         poster = get_poster_filename(e['id'])
         if os.path.exists(poster):
            o_image.file_set('') # this is to force a reload also if the filename is the same
            o_image.file_set(poster)
            o_image.show() # TODO why this is needed ? probably a bug somwhere... :/
         else:
            print 'TODO show a dummy image'
            o_image.file_set('')
      else:
         # TODO print also file size, video len, codecs, streams found, file metadata, etc..
         msg = "Media:<br>" + url + "<br><br>" + \
               "No info stored for this media<br>" + \
               "Try the GetInfo button..."
         o_sentry.entry_set(msg)
         # TODO make thumbnail
         o_image.file_set('')

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
         li = elementary.List(gui.win)
         for person in film_info['cast']:
            if person['job'] == 'Actor':
               label = person['name'] + ' as ' + person['character']
               li.item_append(label, None, None, None, None)

         li.items_get()[0].selected_set(1)
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

######## Choose poster
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
         li = elementary.List(gui.win)
         for image in images:
            icon = EmcRemoteImage(li)
            icon.url_set(image['url'])
            icon.size_hint_min_set(100, 100) # TODO fixme
            #~ label = res['name'] + ' (' + res['released'][:4] + ')'
            mid = image['url'][:-9]
            mid = mid + 'mid.jpg'
            li.item_append(" ", icon, None, None, (mid, film_info['id']))

         li.items_get()[0].selected_set(1)
         li.show()
         li.go()
         li.size_hint_min_set(300, 300) #TODO FIXME

         dialog = EmcDialog(title = 'Choose a poster.', content = li)
         dialog.button_add('Ok', self._cb_poster_ok, dialog)
         dialog.button_add('Cancel', self._cb_poster_cancel, dialog)
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
      utils.download_url_async(url, dest, complete_cb = self._cb_poster_done)

      # kill the dialog
      self.__poster_dialog.delete()
      del self.__poster_dialog

      # make a spinner dialog
      self.__poster_dialog = EmcDialog(title = "Downloading Poster",
                                         spinner = True, style = 'cancel')

   def _cb_poster_done(self, dest, status):
      # kill the dialog
      self.__poster_dialog.delete()
      del self.__poster_dialog

      self.update_film_info(self.__current_url)

######## Choose fanart
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
         li = elementary.List(gui.win)
         for image in images:
            icon = EmcRemoteImage(li)
            icon.url_set(image['url'])
            icon.size_hint_min_set(100, 100) # TODO fixme
            #~ label = res['name'] + ' (' + res['released'][:4] + ')'
            mid = image['url'][:-9]
            mid = mid + 'original.jpg'
            li.item_append(" ", icon, None, None, (mid, film_info['id']))

         li.items_get()[0].selected_set(1)
         li.show()
         li.go()
         li.size_hint_min_set(300, 300) #TODO FIXME

         dialog = EmcDialog(title = 'Choose a Fanart.', content = li)
         dialog.button_add('Ok', self._cb_backdrop_ok, dialog)
         dialog.button_add('Cancel', self._cb_backdrop_cancel, dialog)
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
      
      utils.download_url_async(url, dest, min_size = 2000,
                               complete_cb = self._cb_backdrop_done)

      # kill the dialog
      self.__backdrop_dialog.delete()
      del self.__backdrop_dialog

      # make a spinner dialog
      self.__backdrop_dialog = EmcDialog(title = "Downloading Fanart",
                                         spinner = True, style = 'cancel')

   def _cb_backdrop_done(self, dest, status):
      # kill the dialog
      self.__backdrop_dialog.delete()
      del self.__backdrop_dialog

      if status > 0:
         EmcDialog(title = "Download error !!", style = 'error')

######## Get info
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
                              spinner = True, style = 'cancel')
      print "query: " + query
      utils.download_url_async(query, "tmp", complete_cb = self._cb_search_done)

   def _cb_search_done(self, dest, status):
      f = open(dest, "r")
      data = json.loads(f.read())
      f.close()
      os.remove(dest)

      # kill spinner dialog
      self.dialog.delete()
      del self.dialog

      if len(data) == 1:
         # just one result, assume is the correct one
         self.film_get_info(data[0]['id'])

      elif len(data) > 1:
         # create a list dialog to choose from results
         li = elementary.List(gui.win)
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

         li.items_get()[0].selected_set(1)
         li.show()
         li.go()
         li.size_hint_min_set(300, 300) #TODO FIXME

         dialog = EmcDialog(title = 'Found ' + str(len(data))+' results, please choose the right one.',
                            content = li)
         dialog.button_add('Ok', self._cb_search_ok, dialog)
         dialog.button_add('Cancel', self._cb_search_cancel, dialog)
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
                              spinner = True, style = 'cancel')

      utils.download_url_async(query, "tmp", complete_cb = self._cb_film_info_done)

   def _cb_film_info_done(self, dest, status):
      f = open(dest, "r")
      data = json.loads(f.read())
      f.close()
      os.remove(dest)

      self.movie_info = data[0]

      # download the first poster image found
      for image in self.movie_info['posters']:
         if image['image']['size'] == 'mid': # TODO make default size configurable
            dest = get_poster_filename(self.movie_info['id'])
            utils.download_url_async(image['image']['url'], dest,
                                     complete_cb = self._cb_film_poster_done)
            return

      # if no poster found go to next step
      self._cb_film_poster_done(dest, 1)

   def _cb_film_poster_done(self, dest, status):
      # download the first backdrop image found
      for image in self.movie_info['backdrops']:
         if image['image']['size'] == 'original': # TODO make default size configurable
            dest = get_backdrop_filename(self.movie_info['id'])
            utils.download_url_async(image['image']['url'], dest,
                                     complete_cb = self._cb_film_backdrop_done)
            return

      # if no backdrop found go to next step
      self._cb_film_backdrop_done(dest, 1)

   def _cb_film_backdrop_done(self, dest, status):
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
