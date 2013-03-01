#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2012 Davide Andreoli <dave@gurumeditation.it>
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


import os, re, time
import threading, Queue

try:
   from efl import ecore, evas, elementary
   from efl.elementary.image import Image
   from efl.elementary.list import List
except:
   import ecore, evas, elementary
   from elementary import Image, List

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.sdb import EmcDatabase
from epymc.widgets import EmcDialog, EmcRemoteImage, EmcSourceSelector
from epymc.widgets import EmcVKeyboard, EmcNotify

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.ini as ini
import epymc.utils as utils
import epymc.gui as gui
import epymc.events as events
import epymc.config_gui as config_gui


# debuggin stuff
from pprint import pprint
import pdb
def DBG(msg):
   print('FILM: %s' % (msg))
   # pass


TMDB_API_KEY = '19eef197b81231dff0fd1a14a8d5f863' # Key of the user DaveMDS
DEFAULT_INFO_LANG = 'en'
DEFAULT_EXTENSIONS = 'avi mpg mpeg ogv mkv' #TODO fill better (uppercase ??)
DEFAULT_BADWORDS = 'dvdrip AAC x264 cd1 cd2'
DEFAULT_BADWORDS_REGEXP = '\[.*?\] {.*?} \. -'
""" in a more readable form:
\[.*?\]   # match all stuff between [ and ]
\{.*?\}   # match all stuff between { and }
\.        # points become spaces
-         # dashes become spaces (tmdb dont like dashes)
"""
DEFAULT_MOVIE_REGEXP = '^(?P<name>.*?)(\((?P<year>[0-9]*)\))?$'
""" in a more readable form:
^                            # start of the string
(?P<name>.*?)                # the name of the film  -  captured
(?:\((?P<year>[0-9]*)\))?    # the year, must be within ( and )  -  captured
$                            # end of the string
"""


class AddSourceItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      EmcSourceSelector(done_cb=self.selector_cb, cb_data=mod)

   def selector_cb(self, fullpath, mod):
      mod._folders.append(fullpath)
      ini.set_string_list('film', 'folders', mod._folders, ';')
      mod._browser.refresh(hard=True)

   def label_get(self, url, mod):
      return 'Add source'

   def icon_get(self, url, mod):
      return 'icon/plus'

class FilmItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod.show_film_info(url)

   def label_get(self, url, mod):
      try:
         assert ini.get('film', 'db_names_in_list') == 'True'
         return mod._film_db.get_data(url)['name']
      except:
         return os.path.basename(url)

   def icon_end_get(self, url, mod):
      counts = mediaplayer.play_counts_get(url)
      if counts['finished'] > 0:
         return 'icon/check_on'
      if counts['stop_at'] > 0:
         return 'icon/check_off'

   def icon_get(self, url, mod):
      return self.poster_get(url, mod)

   def poster_get(self, url, mod):
      if mod._film_db.id_exists(url):
         e = mod._film_db.get_data(url)
         poster = get_poster_filename(e['id'])
         if os.path.exists(poster):
            return poster

   def fanart_get(self, url, mod):
      if mod._film_db.id_exists(url):
         e = mod._film_db.get_data(url)
         fanart = get_backdrop_filename(e['id'])
         if os.path.exists(fanart):
            return fanart

   def info_get(self, url, mod):
      if mod._film_db.id_exists(url):
         e = mod._film_db.get_data(url)
         country = ''
         if len(e['countries']) > 0:
            country = e['countries'][0]['code']
         text = '<title>%s (%s %s)</><br>' \
                '<hilight>Rating:</> %.0f/10<br>' \
                '<hilight>Director:</> %s<br>' \
                '<hilight>Cast:</> %s<br>' % \
                (e['name'], country, e['released'][:4],
                e['rating'], mod._get_director(e),
                mod._get_cast(e, 4))
      else:
         name, year = get_film_name_from_url(url)
         text = '<title>%s</><br>' \
                '<hilight>Size:</> %s<br>' \
                '<hilight>Name:</> %s<br>' \
                '<hilight>Year:</> %s<br>' % \
                (os.path.basename(url),
                 utils.hum_size(os.path.getsize(utils.url2path(url))),
                 name, year if year else 'Unknown')
         
      # return "test1: κόσμε END" # should see the Greek word 'kosme'
      return text.encode('utf-8')

class FolderItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add(url, os.path.basename(url), None, mod.populate_url)

   def label_get(self, url, mod):
      return os.path.basename(url)

   def icon_get(self, url, mod):
      return 'icon/folder'


class FilmsModule(EmcModule):
   name = 'film'
   label = 'Films'
   icon = 'icon/film'
   info = """Long info for the film module, explain what it does and what it 
need to work well, can also use markup like <title>this</> or <b>this</>"""

   _browser = None
   _exts = None        # list of allowed extensions
   _film_db = None     # key: film_url  data: dictionary as of the tmdb api
   _person_db = None   # key: ?????     data: dictionary as of the tmdb api

   _generator = None
   _idler = None      # EcoreIdler
   _idler_url = None  # also used as a semaphore
   _idler_db = None   # key: file_url  data: timestamp of the last unsuccessfull tmdb query
   _idler_retry_after = 3 * 24 * 60 * 60

   def __init__(self):
      DBG('Init module')

      # create config ini section if not exists, with defaults
      ini.add_section('film')
      if not ini.has_option('film', 'enable_scanner'):
         ini.set('film', 'enable_scanner', 'False')
      if not ini.has_option('film', 'extensions'):
         ini.set('film', 'extensions', DEFAULT_EXTENSIONS)
      if not ini.has_option('film', 'badwords'):
         ini.set('film', 'badwords', DEFAULT_BADWORDS)
      if not ini.has_option('film', 'badwords_regexp'):
         ini.set('film', 'badwords_regexp', DEFAULT_BADWORDS_REGEXP)
      if not ini.has_option('film', 'tmdb_retry_days'):
         ini.set('film', 'tmdb_retry_days', '3')
      if not ini.has_option('film', 'movie_regexp'):
         ini.set('film', 'movie_regexp', DEFAULT_MOVIE_REGEXP)
      if not ini.has_option('film', 'info_lang'):
         ini.set('film', 'info_lang', DEFAULT_INFO_LANG)
      if not ini.has_option('film', 'db_names_in_list'):
         ini.set('film', 'db_names_in_list', 'True')

      # get allowed exensions from config
      self._exts = ini.get_string_list('film', 'extensions')
      self._idler_retry_after = ini.get_int('film', 'tmdb_retry_days')
      self._idler_retry_after *= 24 * 60 * 60

      # open film/person database (they are created if not exists)
      self._film_db = EmcDatabase('film')
      self._person_db = EmcDatabase('person')
      self._idler_db = EmcDatabase('filmidlercache')

      # add an item in the mainmenu
      img = os.path.join(os.path.dirname(__file__), 'menu_bg.png')
      mainmenu.item_add('film', 10, 'Movies', img, self.cb_mainmenu)

       # add an entry in the config gui
      config_gui.root_item_add('film', 50, 'Movie Collection', icon = 'icon/film',
                               callback = config_panel_cb)

      # create a browser instance
      self._browser = EmcBrowser('Films', 'List')

      # listen to emc events
      events.listener_add('films', self._events_cb)

   def __shutdown__(self):
      DBG('Shutdown module')

      # stop listening for events
      events.listener_del('films')

      # kill the idler
      if self._idler:
         self._idler.delete()
         self._idler = None
         self._idler_url = None
      # TODO clean better the idler? abort if a download in process?

      # delete mainmenu item
      mainmenu.item_del('film')

      # delete config menu item
      config_gui.root_item_del('film')

      # delete browser
      self._browser.delete()

      ## close databases
      del self._film_db
      del self._person_db
      del self._idler_db

   def idle_cb(self):
      # DBG('Mainloop idle')
      
      if self._idler_url is not None:
         # DBG('im busy')
         return ecore.ECORE_CALLBACK_RENEW
         
      # the first time build the generator object 
      if self._generator is None:
         folders = ini.get_string_list('film', 'folders', ';')
         self._generator = utils.grab_files(folders)
         EmcNotify("Film scanner started")

      # get the next file from the generator
      try:
         filename = self._generator.next()
      except StopIteration:
         EmcNotify("Film scanner done")
         DBG("Film scanner done")
         self._generator = None
         return ecore.ECORE_CALLBACK_CANCEL

      url = 'file://' + filename

      if self._film_db.id_exists(url):
         DBG('I know this film (skipping):' + url)
         return ecore.ECORE_CALLBACK_RENEW

      if self._idler_db.id_exists(url):
         elapsed = time.time() - self._idler_db.get_data(url)
         if elapsed < self._idler_retry_after:
            DBG('I scanned this %d seconds ago (skipping): %s' % (elapsed, url))
            return ecore.ECORE_CALLBACK_RENEW
         self._idler_db.del_data(url)

      ext = os.path.splitext(filename)[1]
      if ext[1:] in self._exts:
         tmdb = TMDB(lang = ini.get('film', 'info_lang'))
         name, year = get_film_name_from_url(url)
         if year:
            search = name + ' (' + year + ')'
         else:
            search = name
         tmdb.movie_search(search, self.idle_tmdb_complete)
         self._idler_url = url
      
      return ecore.ECORE_CALLBACK_RENEW

   def idle_tmdb_complete(self, tmdb, movie_info):
      if movie_info is None:
         # store the current time in the cache db
         self._idler_db.set_data(self._idler_url, time.time())
      else:
         # store the result in film db
         try:
            url = self._idler_url
            self._film_db.set_data(url, movie_info)
            text = '<title>New movie:</><br>%s (%s)' % (movie_info['name'], movie_info['released'][:4])
            EmcNotify(text, icon = get_poster_filename(movie_info['id']))
         except:
            pass

      # clear the 'semaphore', now another file can be processed
      self._idler_url = None

      # update the browser view
      self._browser.refresh()

      # delete TMDB2 object
      del tmdb

   def play_film(self, url):
      counts = mediaplayer.play_counts_get(url)
      if counts['stop_at'] > 0:
         pos = counts['stop_at']
         h = int(pos / 3600)
         m = int(pos / 60) % 60
         s = int(pos % 60)
         txt = "Continue from %d:%.2d:%.2d ?" % (h, m, s)
         EmcDialog(text = txt, style = 'yesno', user_data = url,
                   done_cb = self._dia_yes_cb,
                   canc_cb = self._dia_no_cb)
      else:
         self.play_film_real(url, 0)

   def _dia_yes_cb(self, dialog):
      counts = mediaplayer.play_counts_get(dialog.data_get())
      self.play_film_real(dialog.data_get(), counts['stop_at'])
      dialog.delete()

   def _dia_no_cb(self, dialog):
      self.play_film_real(dialog.data_get(), 0)
      dialog.delete()

   def play_film_real(self, url, start_from):
      mediaplayer.play_url(url, start_from = start_from)
      if self._film_db.id_exists(url):
         e = self._film_db.get_data(url)
         try:
            mediaplayer.title_set(e['name'])
         except:
            mediaplayer.title_set(os.path.basename(url))
         try:
            mediaplayer.poster_set(get_poster_filename(e['id']))
         except:
            mediaplayer.poster_set(None)
      else:
         mediaplayer.title_set(os.path.basename(url))
         mediaplayer.poster_set(None)

###### BROWSER STUFF
   def cb_mainmenu(self):
      # get film folders from config
      self._folders = ini.get_string_list('film', 'folders', ';')

      # if not self._folders:
         #TODO alert the user. and instruct how to add folders

      self._browser.page_add('film://root', 'Films', None, self.populate_root_page)
      self._browser.show()
      mainmenu.hide()

      # on idle scan all files (one shoot every time the activity start)
      if not self._generator and ini.get_bool('film', 'enable_scanner'):
         self._idler = ecore.Idler(self.idle_cb)

   def populate_root_page(self, browser, page_url):
      for f in self._folders:
         self._browser.item_add(FolderItemClass(), f, self)

      self._browser.item_add(AddSourceItemClass(), 'film://add_source', self);

   def populate_url(self, browser, url):
      dirs, files = [], []
      for fname in sorted(os.listdir(url[7:]), key=str.lower):
         if fname[0] != '.':
            if os.path.isdir(os.path.join(url[7:], fname)):
               dirs.append(fname)
            else:
               files.append(fname)

      for fname in dirs:
         self._browser.item_add(FolderItemClass(), url + '/' + fname, self)
      for fname in files:
         self._browser.item_add(FilmItemClass(), url + '/' + fname, self)

   def _get_director(self,e):
      for person in e['cast']:
         if person['job'] == 'Director':
            return person['name']
      return 'Unknow'

   def _get_cast(self, e, max_num = 999):
      cast = ''
      for person in e['cast']:
         if person['job'] == 'Actor':
            cast = cast + (', ' if cast else '') + person['name']
            max_num -= 1
            if max_num < 1:
               break
      return cast

   def _events_cb(self, event):
      # TODO: check that we are active and visible
      #       atm, this is fired also when a song end... 
      if event == 'PLAYBACK_FINISHED':
         # refresh the page (maybe an unwatched film becomes watched)
         if self._browser is not None:
            self._browser.refresh()

###### INFO PANEL STUFF
   def show_film_info(self, url):
      image = Image(gui.win)
      image.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      image.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      image.show()
      dialog = EmcDialog(style = 'panel', text = ' ', content = image)

      self._dialog = dialog
      self._current_url = url
      self.update_film_info(url)

   def hide_film_info(self):
      self._dialog.delete()
      del self._dialog

   def update_film_info(self, url):

      # update buttons
      self._dialog.buttons_clear()
      self._dialog.button_add('Play', self._cb_panel_1)
      if self._film_db.id_exists(url):
         self._dialog.button_add('Cast', self._cb_panel_2)
         self._dialog.button_add('Poster', self._cb_panel_3)
         self._dialog.button_add('Fanart', self._cb_panel_4)
      self._dialog.button_add('Search Info', self._cb_panel_5)

      o_image = self._dialog.content_get()

      if self._film_db.id_exists(url):
         print('Found: ' + url)
         e = self._film_db.get_data(url)

         # update text info
         self._dialog.title_set(e['name'].encode('utf-8'))
         info = '<hilight>Director: </hilight> %s <br>' \
                '<hilight>Cast: </hilight> %s <br>' \
                '<hilight>Released: </hilight> %s <br>' \
                '<hilight>Rating: </hilight> %s <br>' \
                '<br><hilight>Overview:</hilight> %s' \
                  % (self._get_director(e), self._get_cast(e), e['released'],
                     e['rating'], e['overview'])
         # self._dialog.text_set("test2: κόσμε END") # should see the Greek word 'kosme')
         self._dialog.text_set(info.encode('utf-8'))

         # update poster
         poster = get_poster_filename(e['id'])
         if os.path.exists(poster):
            o_image.file_set(poster)
         else:
            # TODO show a dummy image
            o_image.file_set('')
      else:
         # TODO print also file size, video len, codecs, streams found, file metadata, etc..
         msg = 'Media:<br>' + url + '<br><br>' + \
               'No info stored for this media<br>' + \
               'Try the Search info button...'
         self._dialog.text_set(msg)
         # TODO make thumbnail
         o_image.file_set('')



   def _cb_panel_1(self, button):
      self.play_film(self._current_url)
      self.hide_film_info()

   def _cb_panel_2(self, button):
      if self._film_db.id_exists(self._current_url):
         film_info = self._film_db.get_data(self._current_url)

         dia = EmcDialog(title = 'Cast', style = 'list')
         for person in film_info['cast']:
            if person['job'] == 'Actor':
               label = person['name'] + ' as ' + person['character']
               dia.list_item_append(label)


######## Choose poster
   def _cb_panel_3(self, button):
      if self._film_db.id_exists(self._current_url):
         film_info = self._film_db.get_data(self._current_url)

         # create a list of posters
         images_thumb = []
         images_big = []
         pprint(film_info['posters'])
         for image in film_info['posters']:
            if image['image']['size'] == 'mid':
               images_thumb.append(image['image'])
            if image['image']['size'] == 'original':
               images_big.append(image['image'])

         # show the list in a dialog
         li = List(gui.win)
         li.horizontal = True
         li.style_set('image_list')
         li.focus_allow_set(False)

         count = 0 
         for (image_thumb, image_big) in zip(images_thumb, images_big):
            img = EmcRemoteImage(image_thumb['url'])
            li.item_append('', img, None, None, (image_big['url'], film_info['id']))
            count += 1

         li.items_get()[0].selected_set(1)
         li.show()
         li.go()

         title = '%d posters available' % (count)
         dialog = EmcDialog(title = title, content = li,
                            done_cb = self._cb_poster_ok)
         li.callback_clicked_double_add((lambda l,i: self._cb_poster_ok(dialog)))

   def _cb_poster_ok(self, dialog):
      li = dialog.content_get()
      item = li.selected_item_get()
      if not item: return

      self._poster_dialog = dialog
      (url, id) = item.data_get()[0][0]
      dest = get_poster_filename(id)
      utils.download_url_async(url, dest, complete_cb = self._cb_poster_done,
                                          progress_cb = self._cb_poster_progress)

      # kill the dialog
      self._poster_dialog.delete()
      del self._poster_dialog

      # make a progress dialog
      self._poster_dialog = EmcDialog(title = 'Downloading Poster',
                                       style = 'progress')

   def _cb_poster_progress(self, dest, tot, done):
      if tot > 0: self._poster_dialog.progress_set(float(done) / float(tot))

   def _cb_poster_done(self, dest, status):
      # kill the dialog
      self._poster_dialog.delete()
      del self._poster_dialog

      self.update_film_info(self._current_url)
      self._browser.refresh()

######## Choose fanart
   def _cb_panel_4(self, button):
      if self._film_db.id_exists(self._current_url):
         film_info = self._film_db.get_data(self._current_url)

         # create a list of backdrops
         images_thumb = []
         images_big = []
         for image in film_info['backdrops']:
            if image['image']['size'] == 'thumb':
               images_thumb.append(image['image'])
            elif image['image']['size'] == 'original': # TODO choose better the wanted size
               images_big.append(image['image'])

         # show the list in a dialog
         li = List(gui.win)
         li.focus_allow_set(False)
         li.style_set('image_list')
         count = 0
         for (image_thumb, image_big) in zip(images_thumb, images_big):
            img = EmcRemoteImage(image_thumb['url'])
            li.item_append('', img, None, None, (image_big['url'], film_info['id']))
            count += 1

         li.items_get()[0].selected_set(1)
         li.show()
         li.go()

         title = '%d images available' % (count)
         dialog = EmcDialog(title = title, content = li,
                            done_cb = self._cb_backdrop_ok)
         li.callback_clicked_double_add((lambda l,i: self._cb_backdrop_ok(dialog)))

   def _cb_backdrop_ok(self, dialog):
      li = dialog.content_get()
      item = li.selected_item_get()
      if not item: return

      self._backdrop_dialog = dialog
      (url, id) = item.data_get()[0][0]
      dest = get_backdrop_filename(id)
      utils.download_url_async(url, dest, complete_cb = self._cb_backdrop_done,
                                          progress_cb = self._cb_backdrop_progress)

      # kill the dialog
      self._backdrop_dialog.delete()
      del self._backdrop_dialog

      # make a spinner dialog
      self._backdrop_dialog = EmcDialog(title = 'Downloading Fanart',
                                         style = 'progress')

   def _cb_backdrop_progress(self, dest, tot, done):
      if tot > 0: self._backdrop_dialog.progress_set(float(done) / float(tot))

   def _cb_backdrop_done(self, dest, status):
      # kill the dialog
      self._backdrop_dialog.delete()
      del self._backdrop_dialog
      if status == 200:
          self._browser.refresh()
      else:
         EmcDialog(title = 'Download error !!', style = 'error')

######## Get film info from themoviedb.org
   def _cb_panel_5(self, button):
      tmdb = TMDB_WithGui(lang = ini.get('film', 'info_lang'))
      name, year = get_film_name_from_url(self._current_url)
      if year:
         search = name + ' (' + year + ')'
      else:
         search = name
      tmdb.movie_search(search, self._cb_search_complete)

   def _cb_search_complete(self, tmdb, movie_info):
      # store the result in db
      self._film_db.set_data(self._current_url, movie_info)
      # update browser
      self._browser.refresh()
      # update info panel
      self.update_film_info(self._current_url)
      # delete TMDB object
      del tmdb


###### UTILS
def get_poster_filename(tmdb_id):
   return os.path.join(utils.config_dir_get(), 'film',
                       str(tmdb_id), 'poster.jpg')

def get_backdrop_filename(tmdb_id):
   return os.path.join(utils.config_dir_get(), 'film',
                       str(tmdb_id), 'backdrop.jpg')

def get_film_name_from_url(url):
   # remove path & extension
   film = os.path.basename(url)
   (film, ext) = os.path.splitext(film)

   # remove blacklisted words (case insensitive)
   for word in ini.get_string_list('film', 'badwords'):
      film = re.sub('(?i)' + word, ' ', film)

   # remove blacklisted regexp
   for rgx in ini.get_string_list('film', 'badwords_regexp'):
      film = re.sub(rgx, ' ', film)

   # apply the user regexp (must capure 'name' and 'year')
   p = re.compile(ini.get('film', 'movie_regexp'))
   m = p.match(film)
   if m:
      name = m.group('name')
      year = m.group('year')
   else:
      name = film
      year = None

   return (name.strip(), year)


###### Config Panel stuff

def config_panel_cb():
   bro = config_gui.browser_get()
   bro.page_add('config://films/', 'Movie Collection', None, populate_config)

def populate_config(browser, url):

   config_gui.standard_item_string_add('film', 'info_lang',
                                       'Preferred language for contents')

   config_gui.standard_item_bool_add('film', 'enable_scanner',
                                     'Enable background scanner')

   config_gui.standard_item_bool_add('film', 'db_names_in_list',
                                     'Prefer movie titles in lists')

   
###############################################################################
import json

class TMDB():
   """ TMDB async client """
   def __init__(self, api_key=TMDB_API_KEY, lang='en'):
      self.key = api_key
      self.lang = lang
      self.server = 'http://api.themoviedb.org/2.1'
      self.dwl_handler = None
      self.complete_cb = None

   def movie_search(self, query, complete_cb):
      DBG('TMDB  ===== Movie search: ' + query)
      self.complete_cb = complete_cb
      query = query.strip().replace("'", "' ") # the api don't like "L'ultimo", must be "L' ultimo"... :/
      url = '%s/Movie.search/%s/json/%s/%s' % \
            (self.server, self.lang, self.key, query)
      self.dwl_handler = utils.download_url_async(url, 'tmp',
                              complete_cb = self._movie_search_done_cb,
                              progress_cb = None)

   def _movie_search_done_cb(self, dest, status):
      self.dwl_handler = None

      if status != 200:
         DBG('TMDB  download error(status: %d) aborting...' % (status))
         self.complete_cb(self,None)
         return

      try:
         f = open(dest, 'r')
         data = json.loads(f.read())
         f.close()
         os.remove(dest)
      except:
         DBG('TMDB  Error decoding json')
         self.complete_cb(self, None)

      # no result found :(
      if len(data) == 0 or data[0] == 'Nothing found.':
         DBG('TMDB  No results found ')
         self.complete_cb(self, None)

      # found, yhea! get the full movie data
      elif len(data) >= 1:
         DBG('TMDB  Found one: %s (%s)' % (data[0]['name'], data[0]['released'][:4]))
         # text = 'Found film:<br>%s (%s)' % (data[0]['name'], data[0]['released'][:4])
         # EmcNotify(text)
         self._do_movie_getinfo_query(data[0]['id'])

   def _do_movie_getinfo_query(self, tid):
      DBG('TMDB  Downloading movie info for id: ' + str(tid))
      url = '%s/Movie.getInfo/%s/json/%s/%s' % \
            (self.server, self.lang, self.key, tid)
      self.dwl_handler = utils.download_url_async(url, 'tmp',
                           complete_cb = self._movie_getinfo_done_cb,
                           progress_cb = None)

   def _movie_getinfo_done_cb(self, dest, status):
      self.dwl_handler = None

      if status != 200:
         DBG('TMDB  download error(status: %d) aborting...' % (status))
         self.complete_cb(self, None)
         return
   
      f = open(dest, 'r')
      data = json.loads(f.read())
      f.close()
      os.remove(dest)

      if len(data) < 1:
         # TODO here ??
         DBG('TMDB  Zero length result.. :/')
         self.complete_cb(self, None)
         return

      # store the movie data
      self.movie_info = data[0]

      # download the first poster image found
      for image in self.movie_info['posters']:
         if image['image']['size'] == 'mid': # TODO make default size configurable
            dest = get_poster_filename(self.movie_info['id'])
            DBG('TMDB  Downloading poster url: ' + str(image['image']['url']))
            self.dwl_handler = utils.download_url_async(image['image']['url'],
                               dest, complete_cb = self._movie_poster_done_cb,
                               progress_cb = None)
            return

      # if no poster found go to next step
      self._movie_poster_done_cb(dest, 200)

   def _movie_poster_done_cb(self, dest, status):
      DBG('TMDB  poster done: ' + str(dest))
      self.dwl_handler = None
      # download the first backdrop image found
      for image in self.movie_info['backdrops']:
         if image['image']['size'] == 'original': # TODO make default size configurable
            dest = get_backdrop_filename(self.movie_info['id'])
            DBG('TMDB  Downloading fanart url: ' + str(image['image']['url']))
            self.dwl_handler = utils.download_url_async(image['image']['url'],
                              dest, complete_cb = self._movie_backdrop_done_cb,
                              progress_cb = None)
            return

      # if no backdrop found go to next step
      self._movie_backdrop_done_cb(dest, 200)

   def _movie_backdrop_done_cb(self, dest, status):
      DBG('TMDB  fanart done: ' + str(dest))
      self.dwl_handler = None

      # call the complete callback
      DBG('TMDB  done!')
      self.complete_cb(self, self.movie_info)

class TMDB_WithGui():
   """ Another try """
   def __init__(self, api_key=TMDB_API_KEY, lang='en'):
      self.key = api_key
      self.lang = lang
      self.server = 'http://api.themoviedb.org/2.1'
      self.complete_cb = None
      self.dialog = None
      self.dwl_handler = None

   def movie_search(self, query, complete_cb = None):
      self.complete_cb = complete_cb
      self.dialog = EmcDialog(title = 'themoviedb.org', style = 'progress',
                              text = '<b>Searching for:</>')
      self.dialog.button_add('Change name', self._change_name_cb, query)
      self._do_movie_search_query(query)

   def _change_name_cb(self, button, query):
      if self.dwl_handler:
         utils.download_abort(self.dwl_handler)
         self.dwl_handler = None

      EmcVKeyboard(text = query,
         accept_cb = (lambda vkb, txt: self._do_movie_search_query(txt)))

   def _cb_downloads_progress(self, dest, tot, done):
      if tot > 0:self.dialog.progress_set(float(done) / float(tot))

   # Movie.search/
   def _do_movie_search_query(self, query):
      query = query.strip().replace("'", "' ") # the api don't like "L'ultimo", must be "L' ultimo"... :/
      DBG('TMDB Film search: ' + query)
      url = '%s/Movie.search/%s/json/%s/%s' % \
            (self.server, self.lang, self.key, query)
      DBG('TMDB Film query: ' + url)
      self.dwl_handler = utils.download_url_async(url, 'tmp',
                              complete_cb = self._movie_search_done_cb,
                              progress_cb = self._cb_downloads_progress)
      self.dialog.text_set('<b>Searching for:</><br>' + query + '<br>')

   def _movie_search_done_cb(self, dest, status):
      self.dwl_handler = None

      if status != 200:
         self.dialog.text_append('<b>ERROR</b><br>')
         return

      f = open(dest, 'r')
      data = json.loads(f.read())
      f.close()
      os.remove(dest)

      # no result found :(
      if len(data) == 0 or data[0] == 'Nothing found.':
         self.dialog.text_append('<br>nothing found, please try with a better name')#TODO explain better the format

      # 1 result found, yhea! get the full movie data
      elif len(data) == 1:
         self._do_movie_getinfo_query(data[0]['id'])

      # more matching results, show a list to choose from
      else:
         self.dialog.text_append('<b>Found %d results</b><br>' % (len(data)))

         title = 'Found %d results, which one?' % (len(data))
         dialog2 = EmcDialog(title = title, style = 'list',
                             done_cb = self._cb_list_ok, canc_cb = self._cb_list_cancel)
         for res in data:
            icon = None
            for image in res['posters']:
               if image['image']['size'] == 'thumb' and image['image']['url']:
                  icon = EmcRemoteImage(image['image']['url'])
                  icon.size_hint_min_set(100, 100) # TODO fixme
                  break
            if res['released']:
               label = '%s (%s)' % (res['name'], res['released'][:4])
            else:
               label = res['name']
            dialog2.list_item_append(label, icon, None, res['id'])

   def _cb_list_cancel(self, dialog2):
      dialog2.delete()
      self.dialog.delete()

   def _cb_list_ok(self, dialog2):
      # get selected item id
      item = dialog2.list_item_selected_get()
      (args, kargs) = item.data_get()
      tid = args[0]
      if not item or not tid: return

      # kill the list dialog
      dialog2.delete()

      # download selected movie info + images
      self._do_movie_getinfo_query(tid)

   ## Movie.getInfo/
   def _do_movie_getinfo_query(self, tid):
      DBG('downloading movie info, id: ' + str(tid))
      self.dialog.text_append('<b>Downloading movie data, </b>')
      url = '%s/Movie.getInfo/%s/json/%s/%s' % \
             (self.server, self.lang, self.key, tid)
      self.dwl_handler = utils.download_url_async(url, 'tmp',
                           complete_cb = self._movie_getinfo_done_cb,
                           progress_cb = self._cb_downloads_progress)

   def _movie_getinfo_done_cb(self, dest, status):
      self.dwl_handler = None

      if status != 200:
         self.dialog.text_append('<b>ERROR</b><br>')
         return
   
      f = open(dest, 'r')
      data = json.loads(f.read())
      f.close()
      os.remove(dest)

      if len(data) < 1:
         self.dialog.text_append('<b>ERROR</b><br>')
         return

      # store the movie data
      self.movie_info = data[0]

      # download the first poster image found
      self.dialog.text_append('<b>poster, </b>')
      for image in self.movie_info['posters']:
         if image['image']['size'] == 'mid': # TODO make default size configurable
            dest = get_poster_filename(self.movie_info['id'])
            self.dwl_handler = utils.download_url_async(image['image']['url'],
                              dest, complete_cb = self._movie_poster_done_cb,
                              progress_cb = self._cb_downloads_progress)
            return

      # if no poster found go to next step
      self._movie_poster_done_cb(dest, 200)

   def _movie_poster_done_cb(self, dest, status):
      DBG('Poster: ' + dest)
      self.dwl_handler = None
      # download the first backdrop image found
      self.dialog.text_append('<b>fanart, </b>')
      for image in self.movie_info['backdrops']:
         if image['image']['size'] == 'original': # TODO make default size configurable
            dest = get_backdrop_filename(self.movie_info['id'])
            self.dwl_handler = utils.download_url_async(image['image']['url'],
                              dest, complete_cb = self._movie_backdrop_done_cb,
                              progress_cb = self._cb_downloads_progress)
            return

      # if no backdrop found go to next step
      self._movie_backdrop_done_cb(dest, 200)

   def _movie_backdrop_done_cb(self, dest, status):
      DBG('Fanart: ' + dest)
      self.dwl_handler = None
      # kill the main dialog
      self.dialog.delete()

      # call the complete callback
      if self.complete_cb:
         self.complete_cb(self, self.movie_info)


"""
###############################################################################
#  Original  themoviedb.org  client implementation taken from:
#  http://forums.themoviedb.org/topic/1092/my-contribution-tmdb-api-wrapper-python/
#  With a little modification by me to support json decode.
#
#  Credits goes to globald
#
#  Unused atm (in favor of the async one)
###############################################################################
import urllib
class TMDB_Original(object):

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
      print 'look: %s  term: %s' % (look, term)
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
"""
