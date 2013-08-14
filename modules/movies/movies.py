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


import os, re, time, threading
from operator import itemgetter

try:
   import queue as Queue
except:
   import Queue

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
from epymc.gui import EmcDialog, EmcRemoteImage, EmcSourceSelector, \
   EmcVKeyboard, EmcNotify, EmcRemoteImage2

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.ini as ini
import epymc.utils as utils
import epymc.gui as gui
import epymc.events as events
import epymc.config_gui as config_gui


# debuggin stuff
def DBG(msg):
   print('MOVIES: %s' % (msg))
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
(?P<name>.*?)                # the name of the movie  -  captured
(?:\((?P<year>[0-9]*)\))?    # the year, must be within ( and )  -  captured
$                            # end of the string
"""


class AddSourceItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      EmcSourceSelector(done_cb=self.selector_cb, cb_data=mod)

   def selector_cb(self, fullpath, mod):
      mod._folders.append(fullpath)
      ini.set_string_list('movies', 'folders', mod._folders, ';')
      mod._browser.refresh(hard=True)

   def label_get(self, url, mod):
      return 'Add source'

   def icon_get(self, url, mod):
      return 'icon/plus'

class MovieItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod.show_movie_info(url)

   def label_get(self, url, mod):
      try:
         assert ini.get('movies', 'db_names_in_list') == 'True'
         return mod._movie_db.get_data(url)['title']
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
      if mod._movie_db.id_exists(url):
         e = mod._movie_db.get_data(url)
         poster = get_poster_filename(e['id'])
         if os.path.exists(poster):
            return poster

   def fanart_get(self, url, mod):
      if mod._movie_db.id_exists(url):
         e = mod._movie_db.get_data(url)
         fanart = get_backdrop_filename(e['id'])
         if os.path.exists(fanart):
            return fanart

   def info_get(self, url, mod):
      if mod._movie_db.id_exists(url):
         e = mod._movie_db.get_data(url)
         text = '<title>%s (%s %s)</><br>' \
                '<hilight>Rating:</> %.0f/10<br>' \
                '<hilight>Director:</> %s<br>' \
                '<hilight>Cast:</> %s<br>' % \
                (e['title'], e['country'], e['release_date'][:4],
                e['rating'], e['director'],
                mod._get_cast(e, 4))
      else:
         name, year = get_movie_name_from_url(url)
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


class MoviesModule(EmcModule):
   name = 'movies'
   label = 'Movies'
   icon = 'icon/movie'
   info = """Long info for the movies module, explain what it does and what it 
need to work well, can also use markup like <title>this</> or <b>this</>"""

   _browser = None     # the browser widget instance
   _exts = None        # list of allowed extensions
   _movie_db = None    # key: movie_url  data: dictionary as of the tmdb api
   _person_db = None   # key: ?????      data: dictionary as of the tmdb api

   _generator = None
   _idler = None      # EcoreIdler
   _idler_url = None  # also used as a semaphore
   _idler_db = None   # key: file_url  data: timestamp of the last unsuccessfull tmdb query

   def __init__(self):
      DBG('Init module')

      # create config ini section if not exists, with defaults
      ini.add_section('movies')
      if not ini.has_option('movies', 'enable_scanner'):
         ini.set('movies', 'enable_scanner', 'False')
      if not ini.has_option('movies', 'extensions'):
         ini.set('movies', 'extensions', DEFAULT_EXTENSIONS)
      if not ini.has_option('movies', 'badwords'):
         ini.set('movies', 'badwords', DEFAULT_BADWORDS)
      if not ini.has_option('movies', 'badwords_regexp'):
         ini.set('movies', 'badwords_regexp', DEFAULT_BADWORDS_REGEXP)
      if not ini.has_option('movies', 'tmdb_retry_days'):
         ini.set('movies', 'tmdb_retry_days', '3')
      if not ini.has_option('movies', 'movie_regexp'):
         ini.set('movies', 'movie_regexp', DEFAULT_MOVIE_REGEXP)
      if not ini.has_option('movies', 'info_lang'):
         ini.set('movies', 'info_lang', DEFAULT_INFO_LANG)
      if not ini.has_option('movies', 'db_names_in_list'):
         ini.set('movies', 'db_names_in_list', 'True')

      # get allowed exensions from config
      self._exts = ini.get_string_list('movies', 'extensions')
      self._idler_retry_after = ini.get_int('movies', 'tmdb_retry_days')
      self._idler_retry_after *= 24 * 60 * 60

      # open movie/person database (they are created if not exists)
      self._movie_db = EmcDatabase('movies')
      self._person_db = EmcDatabase('person')
      self._idler_db = EmcDatabase('movieidlercache')

      # add an item in the mainmenu
      img = os.path.join(os.path.dirname(__file__), 'menu_bg.png')
      mainmenu.item_add('movies', 10, 'Movies', img, self.cb_mainmenu)

       # add an entry in the config gui
      config_gui.root_item_add('movies', 50, 'Movie Collection', icon = 'icon/movie',
                               callback = config_panel_cb)

      # create a browser instance
      self._browser = EmcBrowser('Movies', 'List')

      # listen to emc events
      events.listener_add('movies', self._events_cb)

   def __shutdown__(self):
      DBG('Shutdown module')

      # stop listening for events
      events.listener_del('movies')

      # kill the idler
      if self._idler:
         self._idler.delete()
         self._idler = None
         self._idler_url = None
      # TODO clean better the idler? abort if a download in process?

      # delete mainmenu item
      mainmenu.item_del('movies')

      # delete config menu item
      config_gui.root_item_del('movies')

      # delete browser
      self._browser.delete()

      ## close databases
      del self._movie_db
      del self._person_db
      del self._idler_db

   def idle_cb(self):
      # DBG('Mainloop idle')
      
      if self._idler_url is not None:
         # DBG('im busy')
         return ecore.ECORE_CALLBACK_RENEW
         
      # the first time build the generator object 
      if self._generator is None:
         folders = ini.get_string_list('movies', 'folders', ';')
         self._generator = utils.grab_files(folders)
         EmcNotify("Movies scanner started")

      # get the next file from the generator
      try:
         filename = next(self._generator)
      except StopIteration:
         EmcNotify("Movies scanner done")
         DBG("Movies scanner done")
         self._generator = None
         return ecore.ECORE_CALLBACK_CANCEL

      url = 'file://' + filename

      if self._movie_db.id_exists(url):
         DBG('I know this movie (skipping):' + url)
         return ecore.ECORE_CALLBACK_RENEW

      if self._idler_db.id_exists(url):
         elapsed = time.time() - self._idler_db.get_data(url)
         if elapsed < self._idler_retry_after:
            DBG('I scanned this %d seconds ago (skipping): %s' % (elapsed, url))
            return ecore.ECORE_CALLBACK_RENEW
         self._idler_db.del_data(url)

      ext = os.path.splitext(filename)[1]
      if ext[1:] in self._exts:
         tmdb = TMDBv3(lang = ini.get('movies', 'info_lang'))
         name, year = get_movie_name_from_url(url)
         tmdb.movie_search(name, year, self.idle_tmdb_complete)
         self._idler_url = url

      return ecore.ECORE_CALLBACK_RENEW

   def idle_tmdb_complete(self, tmdb, movie_info):
      if movie_info is None:
         # store the current time in the cache db
         self._idler_db.set_data(self._idler_url, time.time())
      else:
         # store the result in movie db
         try:
            url = self._idler_url
            self._movie_db.set_data(url, movie_info)
            text = '<title>Found movie:</><br>%s (%s)' % (movie_info['title'], movie_info['release_date'][:4])
            EmcNotify(text, icon = get_poster_filename(movie_info['id']))
         except:
            pass

      # clear the 'semaphore', now another file can be processed
      self._idler_url = None

      # update the browser view
      self._browser.refresh()

      # delete TMDB2 object
      del tmdb

   def play_movie(self, url):
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
         self.play_movie_real(url, 0)

   def _dia_yes_cb(self, dialog):
      counts = mediaplayer.play_counts_get(dialog.data_get())
      self.play_movie_real(dialog.data_get(), counts['stop_at'])
      dialog.delete()

   def _dia_no_cb(self, dialog):
      self.play_movie_real(dialog.data_get(), 0)
      dialog.delete()

   def play_movie_real(self, url, start_from):
      mediaplayer.play_url(url, start_from = start_from)
      if self._movie_db.id_exists(url):
         e = self._movie_db.get_data(url)
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
      # get movies folders from config
      self._folders = ini.get_string_list('movies', 'folders', ';')

      # if not self._folders:
         #TODO alert the user. and instruct how to add folders

      self._browser.page_add('movies://root', 'Movies', None, self.populate_root_page)
      self._browser.show()
      mainmenu.hide()

      # on idle scan all files (one shot every time the activity start)
      if not self._generator and ini.get_bool('movies', 'enable_scanner'):
         self._idler = ecore.Idler(self.idle_cb)

   def populate_root_page(self, browser, page_url):
      for f in self._folders:
         self._browser.item_add(FolderItemClass(), f, self)

      self._browser.item_add(AddSourceItemClass(), 'movies://add_source', self);

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
         self._browser.item_add(MovieItemClass(), url + '/' + fname, self)

   def _get_cast(self, e, max_num = 999):
      cast = ''
      for person in sorted(e['cast'], key=itemgetter('order')):
         cast = cast + (', ' if cast else '') + person['name']
         max_num -= 1
         if max_num < 1:
            break
      return cast

   def _events_cb(self, event):
      # TODO: check that we are active and visible
      #       atm, this is fired also when a song end... 
      if event == 'PLAYBACK_FINISHED':
         # refresh the page (maybe an unwatched movie becomes watched)
         if self._browser is not None:
            self._browser.refresh()

###### INFO PANEL STUFF
   def show_movie_info(self, url):
      image = Image(gui.win)
      image.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      image.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      image.show()
      dialog = EmcDialog(style = 'panel', text = ' ', content = image)

      self._dialog = dialog
      self._current_url = url
      self.update_movie_info(url)

   def hide_movie_info(self):
      self._dialog.delete()
      del self._dialog

   def update_movie_info(self, url):

      # update buttons
      self._dialog.buttons_clear()
      self._dialog.button_add('Play', self._cb_panel_1)
      if self._movie_db.id_exists(url):
         self._dialog.button_add('Cast', self._cb_panel_2)
         self._dialog.button_add('Poster', self._cb_panel_3)
         self._dialog.button_add('Fanart', self._cb_panel_4)
      self._dialog.button_add('Search Info', self._cb_panel_5)

      o_image = self._dialog.content_get()

      if self._movie_db.id_exists(url):
         e = self._movie_db.get_data(url)

         # update text info
         self._dialog.title_set(e['title'].encode('utf-8'))
         info = '<hilight>Director: </hilight> %s <br>' \
                '<hilight>Cast: </hilight> %s <br>' \
                '<hilight>Released: </hilight> %s <br>' \
                '<hilight>Country: </hilight> %s <br>' \
                '<hilight>Rating: </hilight> %s <br>' \
                '<br><hilight>Overview:</hilight> %s' \
                  % (e['director'], self._get_cast(e), e['release_date'],
                     e['countries'], e['rating'], e['overview'])
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
      self.play_movie(self._current_url)
      self.hide_movie_info()

   def _cb_panel_2(self, button):
      if self._movie_db.id_exists(self._current_url):
         movie_info = self._movie_db.get_data(self._current_url)

         dia = EmcDialog(title = 'Cast', style = 'list')
         for person in sorted(movie_info['cast'], key=itemgetter('order')):
            label = person['name'] + ' as ' + person['character']
            dia.list_item_append(label)

######## Choose poster
   def _cb_panel_3(self, button):
      if self._movie_db.id_exists(self._current_url):
         movie_info = self._movie_db.get_data(self._current_url)
         tmdb = TMDBv3()
         tmdb.all_posters_list(movie_info['tmdb_id'], self._cb_panel_3_complete)

   def _cb_panel_3_complete(self):
      self.update_movie_info(self._current_url)
      self._browser.refresh()

######## Choose fanart
   def _cb_panel_4(self, button):
      if self._movie_db.id_exists(self._current_url):
         movie_info = self._movie_db.get_data(self._current_url)
         tmdb = TMDBv3()
         tmdb.all_backdrops_list(movie_info['tmdb_id'], self._cb_panel_3_complete)


######## Get movie info from themoviedb.org
   def _cb_panel_5(self, button):
      tmdb = TMDBv3(interactive=True, lang = ini.get('movies', 'info_lang'))
      name, year = get_movie_name_from_url(self._current_url)
      tmdb.movie_search(name, year, self._cb_search_complete)

   def _cb_search_complete(self, tmdb, movie_info):
      # store the result in db
      self._movie_db.set_data(self._current_url, movie_info)
      # update browser
      self._browser.refresh()
      # update info panel
      self.update_movie_info(self._current_url)
      # delete TMDB object
      del tmdb


###### UTILS
def get_poster_filename(tmdb_id):
   return os.path.join(utils.config_dir_get(), 'movies',
                       str(tmdb_id), 'poster.jpg')

def get_backdrop_filename(tmdb_id):
   return os.path.join(utils.config_dir_get(), 'movies',
                       str(tmdb_id), 'backdrop.jpg')

def get_movie_name_from_url(url):
   # remove path & extension
   movie = os.path.basename(url)
   (movie, ext) = os.path.splitext(movie)

   # remove blacklisted words (case insensitive)
   for word in ini.get_string_list('movies', 'badwords'):
      movie = re.sub('(?i)' + word, ' ', movie)

   # remove blacklisted regexp
   for rgx in ini.get_string_list('movies', 'badwords_regexp'):
      movie = re.sub(rgx, ' ', movie)

   # apply the user regexp (must capure 'name' and 'year')
   p = re.compile(ini.get('movies', 'movie_regexp'))
   m = p.match(movie)
   if m:
      name = m.group('name')
      year = m.group('year')
   else:
      name = movie
      year = None

   return (name.strip(), year)


###### Config Panel stuff ######

def config_panel_cb():
   bro = config_gui.browser_get()
   bro.page_add('config://movies/', 'Movie Collection', None, populate_config)

def populate_config(browser, url):

   config_gui.standard_item_string_add('movies', 'info_lang',
                                       'Preferred language for contents')

   config_gui.standard_item_bool_add('movies', 'enable_scanner',
                                     'Enable background scanner')

   config_gui.standard_item_bool_add('movies', 'db_names_in_list',
                                     'Prefer movie titles in lists')

   
###### TMDB API v3 ######
import json
try:
   from urllib.parse import quote as urllib_quote
except:
   from urllib import quote as urllib_quote


class TMDBv3(object):
   """ TMDB API v3 """
   def __init__(self, api_key=TMDB_API_KEY, lang='en', interactive=False):
      self.key = api_key
      self.lang = lang
      self.interactive = interactive
      self.base_url = 'http://api.themoviedb.org/3'
      self.complete_cb = None
      self.dialog = None
      self.dwl_handler = None
      self.query_str = None

   def movie_search(self, query, year, complete_cb):
      self.query_str = query
      self.year = year
      self.complete_cb = complete_cb
      if self.interactive:
         self.dialog = EmcDialog(title = 'themoviedb.org',
                                 style = 'progress',
                                 text = '<b>Searching for:</>')
         self.dialog.button_add('Change name', self._change_name_cb)
      self._do_movie_search_query(query)

   def _change_name_cb(self, button):
      if self.dwl_handler:
         utils.download_abort(self.dwl_handler)
         self.dwl_handler = None

      EmcVKeyboard(text = self.query_str,
               accept_cb = (lambda vkb, txt: self._do_movie_search_query(txt)))

   def _cb_downloads_progress(self, dest, tot, done):
      if self.dialog and tot > 0:
         self.dialog.progress_set(float(done) / float(tot))

   def _build_img_url(self, final_part, size):
      # TODO base url and sizes should be queryed with: /3/configuration
      return 'http://d3gtl9l2a4fn1j.cloudfront.net/t/p/w' + str(size) + final_part

   # /3/search/movie
   def _do_movie_search_query(self, query):
      url = '%s/search/movie?api_key=%s&language=%s&query=%s' % \
            (self.base_url, self.key, self.lang, urllib_quote(query))
      if self.year:
         url += '&year=' + str(self.year)
      DBG('TMDB Movie query: ' + url)
      self.dwl_handler = utils.download_url_async(url, 'tmp', urlencode = False,
                              complete_cb = self._movie_search_done_cb,
                              progress_cb = self._cb_downloads_progress)
      if self.interactive:
         self.dialog.text_set('<b>Searching for:</><br>' + query + '<br>')

   def _movie_search_done_cb(self, dest, status):
      self.dwl_handler = None

      if status != 200:
         if self.interactive: self.dialog.text_append('<b>ERROR</b><br>')
         self.complete_cb(self, None)
         return

      f = open(dest, 'r')
      data = json.loads(f.read())
      f.close()
      os.remove(dest)

      # no result found :(
      if data['total_results'] == 0:
         if self.interactive:
            self.dialog.text_append('<br>nothing found, please try with a better name')#TODO explain better the format
         self.complete_cb(self, None)
         return

      # one result found, yhea! now request the full movie info
      elif data['total_results'] == 1 or not self.interactive:
         self._do_movie_info_query(data['results'][0]['id'])

      # more matching results, show a list to choose from
      elif self.interactive:
         self.dialog.text_append('<b>Found %d results</b><br>' % (data['total_results']))

         title = 'Found %d results, which one?' % (data['total_results'])
         dialog2 = EmcDialog(title = title, style = 'list',
                             done_cb = self._cb_list_ok,
                             canc_cb = self._cb_list_cancel)
         for res in data['results']:
            icon = None
            if 'poster_path' in res and res['poster_path'] is not None:
               complete_url = self._build_img_url(res['poster_path'], 154)
               icon = EmcRemoteImage(complete_url)
               icon.size_hint_min_set(100, 100) # TODO fixme
            if 'release_date' in res:
               label = '%s (%s)' % (res['title'], res['release_date'][:4])
            else:
               label = res['title']
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
      self._do_movie_info_query(tid)

   # 3/movie/{id}
   def _do_movie_info_query(self, tid):
      if self.interactive:
         self.dialog.text_append('<b>Downloading movie data, </b>')
      url = '%s/movie/%s?api_key=%s&language=%s&append_to_response=casts' % \
             (self.base_url, tid, self.key, self.lang)
      DBG('TMDB Movie query: ' + url)
      self.dwl_handler = utils.download_url_async(url, 'tmp', urlencode = False,
                           complete_cb = self._movie_info_done_cb,
                           progress_cb = self._cb_downloads_progress)

   def _movie_info_done_cb(self, dest, status):
      self.dwl_handler = None

      if status != 200:
         if self.interactive: self.dialog.text_append('<b>ERROR</b><br>')
         return
   
      f = open(dest, 'r')
      data = json.loads(f.read())
      f.close()
      os.remove(dest)

      if len(data) < 1:
         if self.interactive: self.dialog.text_append('<b>ERROR</b><br>')
         self.complete_cb(self, None)
         return

      # store the movie data for later "parse"
      self.movie_info = data

      # download the first poster image found
      if self.interactive: self.dialog.text_append('<b>poster, </b>')

      if 'poster_path' in data and data['poster_path'] is not None:
         dest = get_poster_filename(data['id'])
         complete_url = self._build_img_url(data['poster_path'], 342)
         self.dwl_handler = utils.download_url_async(complete_url, dest,
                              complete_cb = self._movie_poster_done_cb,
                              progress_cb = self._cb_downloads_progress)
      else:
         # no poster found, go to next step
         self._movie_poster_done_cb(dest, 200)

   def _movie_poster_done_cb(self, dest, status):
      self.dwl_handler = None

      # download the first backdrop image found
      if self.interactive: self.dialog.text_append('<b>fanart, </b>')
      
      if 'backdrop_path' in self.movie_info and self.movie_info['backdrop_path'] is not None:
         dest = get_backdrop_filename(self.movie_info['id'])
         complete_url = self._build_img_url(self.movie_info['backdrop_path'], 780)
         self.dwl_handler = utils.download_url_async(complete_url, dest,
                              complete_cb = self._movie_backdrop_done_cb,
                              progress_cb = self._cb_downloads_progress)
      else:
         # no backdrop found, go to next step
         self._movie_backdrop_done_cb(dest, 200)

   def _movie_backdrop_done_cb(self, dest, status):
      self.dwl_handler = None

      # kill the main dialog
      if self.interactive: self.dialog.delete()

      # build the movie info dict
      tmdb = self.movie_info

      try:
         director = [d['name'] for d in tmdb['casts']['crew'] if d['job'] == 'Director'][0]
      except:
         director = 'missing'

      try:
         country = tmdb['production_countries'][0]['iso_3166_1']
      except:
         country = ''

      try:
         countries = ', '.join([c['iso_3166_1'] for c in tmdb['production_countries']])
      except:
         countries = ''

      info = {
         'id':             tmdb['id'],
         'tmdb_id':        tmdb['id'],
         'imdb_id':        tmdb['imdb_id'],
         'title':          tmdb['title'],
         'adult':          tmdb['adult'],
         'original_title': tmdb['original_title'],
         'release_date':   tmdb['release_date'],
         'budget':         tmdb['budget'],
         'overview':       tmdb['overview'],
         'tagline':        tmdb['tagline'],
         'rating':         tmdb['vote_average'],
         'country':        country,
         'countries':      countries,
         'director':       director,
         'cast':           tmdb['casts']['cast'],
         'crew':           tmdb['casts']['crew'],
      }

      # call the complete callback
      self.complete_cb(self, info)

   ## all_posters_list
   def all_posters_list(self, tid, complete_cb):
      self.complete_cb = complete_cb
      url = '%s/movie/%s/images?api_key=%s' % \
            (self.base_url, tid, self.key)
      DBG('TMDB images query: ' + url)
      self.dwl_handler = utils.download_url_async(url, 'tmp', urlencode = False,
                              complete_cb = self._poster_list_done_cb)

   def _poster_list_done_cb(self, dest, status):
      if status != 200:
         # self.complete_cb(self, None)
         return

      f = open(dest, 'r')
      data = json.loads(f.read())
      f.close()
      os.remove(dest)

      # show the list in a dialog
      li = List(gui.win)
      li.horizontal = True
      li.style_set('image_list')
      li.focus_allow_set(False)
         
      for poster in data['posters']:
         thumb_url = self._build_img_url(poster['file_path'], 154)
         big_url = self._build_img_url(poster['file_path'], 500)
         img = EmcRemoteImage(thumb_url)
         li.item_append('', img, None, None, (big_url, data['id']))

      li.items_get()[0].selected_set(1)
      li.show()
      li.go()

      title = '%d posters available' % (len(data['posters']))
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
      self._poster_dialog = EmcDialog(title = 'Downloading Image',
                                      style = 'progress')
   
   def _cb_poster_progress(self, dest, tot, done):
      if tot > 0: self._poster_dialog.progress_set(float(done) / float(tot))

   def _cb_poster_done(self, dest, status):
      # kill the dialog
      self._poster_dialog.delete()
      del self._poster_dialog
      self.complete_cb()

   ## all_backdrops_list
   def all_backdrops_list(self, tid, complete_cb):
      self.complete_cb = complete_cb
      url = '%s/movie/%s/images?api_key=%s' % \
            (self.base_url, tid, self.key)
      DBG('TMDB images query: ' + url)
      self.dwl_handler = utils.download_url_async(url, 'tmp', urlencode = False,
                              complete_cb = self._backdrop_list_done_cb)

   def _backdrop_list_done_cb(self, dest, status):
      if status != 200:
         # self.complete_cb(self, None)
         return

      f = open(dest, 'r')
      data = json.loads(f.read())
      f.close()
      os.remove(dest)

      # show the list in a dialog
      li = List(gui.win)
      li.horizontal = False
      li.style_set('image_list')
      li.focus_allow_set(False)
         
      for backdrop in data['backdrops']:
         thumb_url = self._build_img_url(backdrop['file_path'], 300)
         big_url = self._build_img_url(backdrop['file_path'], 1280)
         img = EmcRemoteImage(thumb_url)
         li.item_append('', img, None, None, (big_url, data['id']))

      li.items_get()[0].selected_set(1)
      li.show()
      li.go()

      title = '%d fanarts available' % (len(data['backdrops']))
      dialog = EmcDialog(title = title, content = li,
                         done_cb = self._cb_backdrop_ok)
      li.callback_clicked_double_add((lambda l,i: self._cb_backdrop_ok(dialog)))

   def _cb_backdrop_ok(self, dialog):
      li = dialog.content_get()
      item = li.selected_item_get()
      if not item: return

      self._poster_dialog = dialog
      (url, id) = item.data_get()[0][0]
      dest = get_backdrop_filename(id)
      utils.download_url_async(url, dest, complete_cb = self._cb_poster_done,
                                          progress_cb = self._cb_poster_progress)

      # kill the dialog
      self._poster_dialog.delete()
      del self._poster_dialog

      # make a progress dialog
      self._poster_dialog = EmcDialog(title = 'Downloading Fanart',
                                      style = 'progress')



""" TMDB APIv3 response for the movie Alien (plus casts)

{
 "id": 348,
 "adult": false,
 "title": "Alien",
 "original_title": "Alien",
 "release_date": "1979-05-25",
 "poster_path": "/ytcDmXUXOLhqiXbWOpZOMOAdnz2.jpg",
 "backdrop_path": "/vMNl7mDS57vhbglfth5JV7bAwZp.jpg",
 "budget": 11000000,
 "imdb_id": "tt0078748",
 "homepage": "",
 "popularity": 5.28431392227447,
 "revenue": 104931801,
 "runtime": 117,
 "status": "Released",
 "vote_average": 7.0,
 "vote_count": 1111,
 "tagline": "Nello spazio nessuno può sentirti urlare",
 "overview": "L’astronave Nostromo sbarca su un pianeta da cui proviene un SOS,
              ma la colonia sembra essere disabitata. I coloni sono stati in
              realtà sterminati da una razza aliena che ha trasformato la base
              in una gigantesca covata.",
 "belongs_to_collection":
  {
   "id": 8091,
   "name": "Alien Collection",
   "poster_path": "/aSIsDu77vYlHjPWPpaOBO3072U8.jpg",
   "backdrop_path": "/kB0Y3uGe9ohJa59Lk8UO9cUOxGM.jpg"
  },
 "genres":
  [
   {"id": 28, "name": "Azione"},
   {"id": 27, "name": "Horror"},
   {"id": 878, "name": "Fantascienza"},
   {"id": 53, "name": "Thriller"}
  ],
 "production_companies":
  [
   {"name": "20th Century Fox", "id": 25},
   {"name": "Brandywine Productions Ltd.", "id": 401}
  ],
 "production_countries":
  [
   {"iso_3166_1": "US", "name": "United States of America"},
   {"iso_3166_1": "GB", "name": "United Kingdom"}
  ],
 "spoken_languages":
  [
   {"iso_639_1": "en", "name": "English"},
   {"iso_639_1": "es", "name": "Español"}
  ],
 "casts":
  {
   'cast':
    [
     {'name': 'Tom Skerritt', 'character': 'Dallas', 'id': 4139, 'cast_id': 3, 'profile_path': '/c0QJNRu6QPKPB2abCNNw70gPVUC.jpg', 'order': 1},
     {'name': 'Sigourney Weaver', 'character': 'Ripley', 'id': 10205, 'cast_id': 4, 'profile_path': '/uXUxgbWWdHnUDLYFNg4jviTjTnq.jpg', 'order': 0},
     {'name': 'Veronica Cartwright', 'character': 'Lambert', 'id': 5047, 'cast_id': 5, 'profile_path': '/7LEj6ln5Fq6Hdg2wMKRxsvWoU2z.jpg', 'order': 2},
     {'name': 'Harry Dean Stanton', 'character': 'Brett', 'id': 5048, 'cast_id': 6, 'profile_path': '/vlfKwhCimC1N42VPNM9iRYBpW0b.jpg', 'order': 3},
     {'name': 'John Hurt', 'character': 'Kane', 'id': 5049, 'cast_id': 7, 'profile_path': '/zUQ7WL3xg9C532Aa8hftcJUnk9j.jpg', 'order': 4},
     {'name': 'Ian Holm', 'character': 'Ash', 'id': 65, 'cast_id': 8, 'profile_path': '/yD3bGWErMQPaAe1ZKdzvWi7hLsY.jpg', 'order': 5},
     {'name': 'Yaphet Kotto', 'character': 'Parker', 'id': 5050, 'cast_id': 9, 'profile_path': '/vjQOWuoig5b2b7JZ8caN4vuFxsg.jpg', 'order': 6},
     {'name': 'Bolaji Badejo', 'character': 'Alien', 'id': 5051, 'cast_id': 10, 'profile_path': '/83NFKY9rgC5Pnx5hRJtHj0KkpnT.jpg', 'order': 7},
     {'name': 'Helen Horton', 'character': 'Mother (voice)', 'id': 5052, 'cast_id': 11, 'profile_path': '/90ruMVGVYNS6dUYj6zCa7XIw8eG.jpg', 'order': 8},
     {'name': 'Eddie Powell', 'character': 'Alien', 'id': 1077325, ucast_id': 30, 'profile_path': None, 'order': 9}
    ],
   'crew':
    [
     {'department': 'Directing', 'job': 'Director', 'profile_path': '/46XCMVEYedwsqagc3kjrPmvAKmP.jpg', 'id': 578, 'name': 'Ridley Scott'},
     {'department': 'Writing', 'job': 'Screenplay', 'profile_path': '/slLZWXZ1lmdF763166ATRRI200n.jpg', 'id': 5045, 'name': u"Dan O'Bannon"},
     {'department': 'Production', 'job': 'Producer', 'profile_path': None, 'id': 5053, 'name': 'Gordon Carroll'},
     {'department': 'Production', 'job': 'Producer', 'profile_path': None, 'id': 915, 'name': 'David Giler'},
     {'department': 'Production', 'job': 'Producer', 'profile_path': None, 'id': 1723, 'name': 'Walter Hill'},
     {'department': 'Production', 'job': 'Producer', 'profile_path': None, 'id': 5054, 'name': 'Ivor Powell'},
     {'department': 'Production', 'job': 'Executive Producer', 'profile_path': None, 'id': 5046, 'name': 'Ronald Shusett'},
     {'department': 'Sound', 'job': 'Original Music Composer', ''profile_path': None, 'id': 1760, 'name': 'Jerry Goldsmith'},
     {'department': 'Camera', 'job': 'Director of Photography', 'profile_path': None, 'id': 5055, 'name': 'Derek Vanlint'},
     {'department': 'Editing', 'job': 'Editor', 'profile_path': None, 'id': 5056, 'name': 'Terry Rawlings'},
     {'department': 'Editing', 'job': 'Editor', 'profile_path': None, 'id': 5057, ''name': 'Peter Weatherley'},
     {'department': 'Art', 'job': 'Production Design', 'profile_path': None, 'id': 4616, 'name': 'Michael Seymour'},
     {'department': 'Art', 'job': 'Production Design', 'profile_path': None, 'id': 5058, 'name': 'Roger Christian'},
     {'department': 'Art', 'job': 'Art Direction', 'profile_path': None, 'id': 5058, 'name': 'Roger Christian'},
     {'department': 'Art', 'job': 'Art Direction', 'profile_path': None, 'id': 5059, 'name': 'Leslie Dilley'},
     {'department': 'Art', 'job': 'Set Decoration', 'profile_path': None, 'id': 5060, 'name': 'Ian Whittaker'},
     {'department': 'Costume & Make-Up', 'job': 'Costume Design', 'profile_path': None, 'id': 5061, 'name': 'John Mollo'},
     {'department': ''Sound', 'job': 'Sound Editor', 'profile_path': None, 'id': 5062, 'name': 'Robert Hathaway'},
     {'department': 'Art', 'job': 'Production Design', 'profile_path': None, 'id': 9136, 'name': 'H.R. Giger'},
     {'department': 'Crew', 'job': 'Special Effects', 'profile_path': None, 'id': 9402, 'name': 'Brian Johnson'},
     {'department': 'Production', 'job': 'Casting', 'profile_path': None, 'id': 23349, 'name': 'Mary Goldberg'},
     {'department': 'Production', 'job': 'Casting', 'profile_path': None, 'id': 668, 'name': 'Mary Selway'}
    ]
  }
}

"""
