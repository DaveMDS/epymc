#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2014 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of EpyMC, an EFL based Media Center written in Python.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os, re, time
from operator import itemgetter

from efl import ecore, evas, elementary, emotion
from efl.elementary.image import Image

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.sdb import EmcDatabase
from epymc.gui import EmcDialog, EmcRemoteImage, EmcSourcesManager, \
   EmcVKeyboard, EmcNotify

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

MOVIE_DB_VERSION = 1
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

_mod = None


class AddSourceItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      EmcSourcesManager('movies', done_cb=self._manager_cb)

   def _manager_cb(self, sources):
      _mod._folders = sources
      _mod._browser.refresh(hard=True)

   def label_get(self, url, mod):
      return 'Manage sources'

   def icon_get(self, url, mod):
      return 'icon/plus'

class RescanItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      if not mod._scanner:
         mod._scanner = BackgroundScanner(mod._browser, mod._movie_db, mod._idler_db)

   def label_get(self, url, mod):
      return 'Rescan library'

   def icon_get(self, url, mod):
      return 'icon/refresh'

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
      # return text.encode('utf-8')
      return text.replace('&', '&amp;') # :/

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
   _idler_db = None    # key: file_url  data: timestamp of the last unsuccessfull tmdb query
   _scanner = None     # BackgroundScanner instance

   def __init__(self):
      global _mod
      
      DBG('Init module')
      _mod = self
      
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

      # add an item in the mainmenu
      mainmenu.item_add('movies', 10, 'Movies', 'icon/movie', self.cb_mainmenu)

       # add an entry in the config gui
      config_gui.root_item_add('movies', 50, 'Movie Collection',
                               icon = 'icon/movie', callback = config_panel_cb)

      # create a browser instance
      self._browser = EmcBrowser('Movies', 'List')

      # listen to emc events
      events.listener_add('movies', self._events_cb)

   def __shutdown__(self):
      DBG('Shutdown module')

      # stop listening for events
      events.listener_del('movies')

      # kill the idler
      if self._scanner:
         self._scanner.abort()
         self._scanner = None

      # delete mainmenu item
      mainmenu.item_del('movies')

      # delete config menu item
      config_gui.root_item_del('movies')

      # delete browser
      self._browser.delete()

      # close databases
      if self._movie_db is not None: del self._movie_db
      if self._idler_db is not None: del self._idler_db

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
            mediaplayer.title_set(e['title'])
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

      # open movie/idler databases (they are created if not exists)
      if self._movie_db is None:
         self._movie_db = EmcDatabase('movies', MOVIE_DB_VERSION)
      if self._idler_db is None:
         self._idler_db = EmcDatabase('movieidlercache', MOVIE_DB_VERSION)

      # on idle scan all files (one shot every time the activity start)
      if not self._scanner and ini.get_bool('movies', 'enable_scanner'):
         self._scanner = BackgroundScanner(self._browser, self._movie_db, self._idler_db)

   def populate_root_page(self, browser, page_url):
      for f in self._folders:
         self._browser.item_add(FolderItemClass(), f, self)

      self._browser.item_add(RescanItemClass(), 'movies://rescan_library', self);
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
         self._dialog.button_add('Posters', self._cb_panel_3)
         self._dialog.button_add('Backdrops', self._cb_panel_4)
      self._dialog.button_add('Search Info', self._cb_panel_5)

      o_image = self._dialog.content_get()

      if self._movie_db.id_exists(url):
         e = self._movie_db.get_data(url)

         # update text info
         self._dialog.title_set(e['title'].replace('&', '&amp;'))
         info = '<hilight>Director: </hilight> %s <br>' \
                '<hilight>Cast: </hilight> %s <br>' \
                '<hilight>Released: </hilight> %s <br>' \
                '<hilight>Country: </hilight> %s <br>' \
                '<hilight>Rating: </hilight> %s <br>' \
                '<br><hilight>Overview:</hilight> %s' \
                  % (e['director'], self._get_cast(e), e['release_date'],
                     e['countries'], e['rating'], e['overview'])
         # self._dialog.text_set("test2: κόσμε END") # should see the Greek word 'kosme')
         self._dialog.text_set(info.replace('&', '&amp;'))

         # update poster
         poster = get_poster_filename(e['id'])
         if os.path.exists(poster):
            o_image.file_set(poster)
         else:
            # TODO show a dummy image
            o_image.file_set('')
      else:
         name, year = get_movie_name_from_url(url)
         self._dialog.title_set(name)
         # TODO print also file size, video len, codecs, streams found, file metadata, etc..
         msg = 'Media:<br>' + url + '<br><br>' + \
               'No info stored for this media<br>' + \
               'Try the Search info button...'
         self._dialog.text_set(msg)
         # TODO make thumbnail
         # o_image.file_set('')


######## Play
   def _cb_panel_1(self, button):
      self.play_movie(self._current_url)
      self.hide_movie_info()


######## Cast
   def _cb_panel_2(self, button):
      if self._movie_db.id_exists(self._current_url):
         movie_info = self._movie_db.get_data(self._current_url)

         dia = EmcDialog(title = 'Cast', style = 'list',
                         done_cb = lambda d, pid: CastPanel(pid))
         dia.button_add('Info', self._cb_cast_info, dia)

         for person in sorted(movie_info['cast'], key=itemgetter('order')):
            label = '%s as %s' % (person['name'], person['character'])
            icon = EmcRemoteImage(person['profile_path']) # TODO use 'dest' to cache the img
            icon.size_hint_min_set(100, 100) # TODO FIXME
            dia.list_item_append(label, icon, None, person['id'])

   def _cb_cast_info(self, button, list_dia):
      item = list_dia.list_item_selected_get()
      pid = item.data_get()[0][0]
      CastPanel(pid)


######## Choose poster
   def _cb_panel_3(self, button):
      if self._movie_db.id_exists(self._current_url):
         movie_info = self._movie_db.get_data(self._current_url)
         tmdb = TMDBv3()
         tmdb.get_posters(movie_info['tmdb_id'], self._cb_posters_list_complete)

   def _cb_posters_list_complete(self, tmdb, posters):
      title = '%d posters available' % (len(posters))
      dialog = EmcDialog(style = 'image_list_horiz', title = title,
                         done_cb = self._cb_posters_list_ok)
      for poster in posters:
         icon = EmcRemoteImage(poster['thumb_url'])
         dialog.list_item_append(None, icon, poster = poster)

   def _cb_posters_list_ok(self, dialog, poster):
      dest = get_poster_filename(poster['movie_id'])
      utils.download_url_async(poster['url'], dest,
                               complete_cb = self._cb_image_done,
                               progress_cb = self._cb_image_progress)

      # kill the list dialog
      dialog.delete()
      del dialog

      # show a progress dialog
      self._poster_dialog = EmcDialog(title = 'Downloading Image',
                                      style = 'progress')

   def _cb_image_progress(self, dest, tot, done):
      if tot > 0: self._poster_dialog.progress_set(float(done) / float(tot))

   def _cb_image_done(self, dest, status):
      # kill the dialog
      self._poster_dialog.delete()
      del self._poster_dialog
      # update browser and info panel
      self.update_movie_info(self._current_url)
      self._browser.refresh()


######## Choose fanart
   def _cb_panel_4(self, button):
      if self._movie_db.id_exists(self._current_url):
         movie_info = self._movie_db.get_data(self._current_url)
         tmdb = TMDBv3()
         tmdb.get_backdrops(movie_info['tmdb_id'], self._cb_backdrops_list_complete)

   def _cb_backdrops_list_complete(self, tmdb, backdrops):

      title = '%d backdrops available' % (len(backdrops))
      dialog = EmcDialog(style = 'image_list_vert', title = title,
                         done_cb = self._cb_backdrops_list_ok)
      for backdrop in backdrops:
         img = EmcRemoteImage(backdrop['thumb_url'])
         dialog.list_item_append(None, img, backdrop = backdrop)

   def _cb_backdrops_list_ok(self, dialog, backdrop):
      # download the selected backdrop
      dest = get_backdrop_filename(backdrop['movie_id'])
      utils.download_url_async(backdrop['url'], dest,
                               complete_cb = self._cb_image_done,
                               progress_cb = self._cb_image_progress)

      # kill the list dialog
      dialog.delete()
      del dialog

      # show a progress dialog
      self._poster_dialog = EmcDialog(title = 'Downloading Image',
                                      style = 'progress')


######## Get movie info from themoviedb.org
   def _cb_panel_5(self, button):
      name, year = get_movie_name_from_url(self._current_url)
      self._do_movie_search(name, year)

   def _do_movie_search(self, name, year):
      tmdb = TMDBv3(lang = ini.get('movies', 'info_lang'))
      tmdb.movie_search(name, year, self._cb_search_done)
      if year:
         text = '<b>Searching for:</><br>%s (%s)<br>' % (name, year)
      else:
         text = '<b>Searching for:</><br>%s<br>' % (name)

      self.tmdb_dialog = EmcDialog(title = 'themoviedb.org',
                                   style = 'progress', text = text,
                                   user_data = tmdb)
      self.tmdb_dialog.button_add('Change name',
                  lambda b: EmcVKeyboard(text=name, accept_cb=self._vkbd_cb))

   def _vkbd_cb(self, vkbd, txt):
      if self.tmdb_dialog: self.tmdb_dialog.delete()
      self._do_movie_search(txt, None)

   def _cb_search_done(self, tmdb, results, status):
      if len(results) == 0:
         self.tmdb_dialog.text_append('<br>nothing found, please try with a better name')#TODO explain better the format
      elif len(results) == 1:
         tmdb.get_movie_info(results[0]['tmdb_id'],
                             self._cb_info_done, self._cb_info_progress)
         self.tmdb_dialog.text_append('<b>Downloading movie info...</b>')
      else:
         self.tmdb_dialog.text_append('<b>Found %d results</b><br>' % (len(results)))
         title = 'Found %d results, which one?' % (len(results))
         dialog2 = EmcDialog(title = title, style = 'list',
                             done_cb = self._cb_list_ok,
                             canc_cb = self._cb_list_cancel)
         for res in results:
            icon = EmcRemoteImage(res['poster_url'])
            icon.size_hint_min_set(100, 100) # TODO fixme
            label = '%s (%s)' % (res['title'], res['year'])
            dialog2.list_item_append(label, icon, None, res['tmdb_id'])

   def _cb_list_cancel(self, dialog2):
      dialog2.delete()
      self.tmdb_dialog.delete()
      self.tmdb_dialog = None

   def _cb_list_ok(self, dialog2, tid):
      # kill the list dialog
      dialog2.delete()

      # download selected movie info + images
      tmdb = self.tmdb_dialog.data_get()
      tmdb.get_movie_info(tid, self._cb_info_done, self._cb_info_progress)
      self.tmdb_dialog.text_append('<b>Downloading movie info...</b>')

   def _cb_info_progress(self, tmdb, progress, stage):
      self.tmdb_dialog.progress_set(progress)

   def _cb_info_done(self, tmdb, movie_info):
      # store the result in db
      self._movie_db.set_data(self._current_url, movie_info)
      # update browser and info panel
      self._browser.refresh()
      self.update_movie_info(self._current_url)
      # clean up
      self.tmdb_dialog.delete()
      self.tmdb_dialog = None
      del tmdb


class CastPanel(EmcDialog):
   def __init__(self, pid):
      self.pid = pid
      self.info = None

      tmdb = TMDBv3(lang = ini.get('movies', 'info_lang'))
      tmdb.get_cast_info(self.pid, self._fetch_done_cb, self._fetch_progress_cb)
      self._dia = EmcDialog(style = 'progress', title = 'Fetching info',
                            text = 'please wait...')

   def _fetch_progress_cb(self, tmdb, progress):
      self._dia.progress_set(progress)

   def _fetch_done_cb(self, tmdb, result):
      self.info = result
      self._dia.delete()
      del tmdb

      text = '<hilight>%s</><br>' % self.info['name']
      if self.info['biography']:
         text += '%s<br><br>' % self.info['biography'].replace('\n', '<br>')
      if self.info['birthday']:
         text += '<hilight>Birthday:</> %s<br>' % (self.info['birthday'])
      if self.info['deathday']:
         text += '<hilight>Deathday:</> %s<br>' % (self.info['deathday'])
      if self.info['place_of_birth']:
         text += '<hilight>Place of birth:</> %s<br>' % (self.info['place_of_birth'])

      image = EmcRemoteImage(self.info['profile_path'])
      EmcDialog.__init__(self, title = self.info['name'], style = 'panel',
                               content = image, text = text)

      c = len(self.info['credits']['cast'])
      self.button_add('Movies (%s)' % c, lambda b: self.movies_dialog())
      c = len(self.info['images']['profiles'])
      self.button_add('Photos (%s)' % c, lambda b: self.photos_dialog())

   def photos_dialog(self):
      dia = EmcDialog(style = 'image_list_horiz', title = self.info['name'])
      for image in self.info['images']['profiles']:
         img = EmcRemoteImage(image['file_path'])
         dia.list_item_append(None, img)

   def movies_dialog(self):
      dia = EmcDialog(style = 'list', title = self.info['name'])
      for movie in self.info['credits']['cast']:
         label = '%s as %s' % (movie['title'], movie['character'])
         icon = EmcRemoteImage(movie['poster_path'])
         icon.size_hint_min_set(100, 100) # TODO FIXME
         dia.list_item_append(label, icon)


class BackgroundScanner(ecore.Idler):
   def __init__(self, browser, movie_db, idler_db):
      self._browser = browser
      self._movie_db = movie_db
      self._idler_db = idler_db
      self._current_url = None  # also used as a semaphore
      self._generator = None
      self._tmdb = None # TMDBv3 instance
      self._retry_after = ini.get_int('movies', 'tmdb_retry_days')
      self._retry_after *= 24 * 60 * 60

      ecore.Idler.__init__(self, self._idle_cb)

   def abort(self):
      # stop the idler
      self.delete()
      # abort any tmdb operations
      if self._tmdb:
         self._tmdb.abort()
         del self._tmdb
         self._tmdb = None
         
   def _idle_cb(self):
      # DBG('Mainloop idle')
      
      if self._current_url is not None:
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
         if elapsed < self._retry_after:
            DBG('I scanned this %d seconds ago (skipping): %s' % (elapsed, url))
            return ecore.ECORE_CALLBACK_RENEW
         self._idler_db.del_data(url)

      if emotion.extension_may_play_get(filename):
         self._tmdb = TMDBv3(lang = ini.get('movies', 'info_lang'))
         name, year = get_movie_name_from_url(url)
         self._tmdb.movie_search(name, year, self._search_done_cb)
         self._current_url = url

      return ecore.ECORE_CALLBACK_RENEW

   def _search_done_cb(self, tmdb_obj, results, status):
      if status == 200 and len(results) > 0:
         self._tmdb.get_movie_info(results[0]['tmdb_id'], self._tmdb_complete)
      else:
         # store the current time in the cache db
         self._idler_db.set_data(self._current_url, time.time())
         # clear the 'semaphore', now another file can be processed
         del self._tmdb
         self._tmdb = None
         self._current_url = None

   def _tmdb_complete(self, tmdb, movie_info):
      if movie_info is None:
         # store the current time in the cache db
         self._idler_db.set_data(self._idler_url, time.time())
      else:
         # store the result in movie db
         try:
            self._movie_db.set_data(self._current_url, movie_info)
            text = '<title>Found movie:</><br>%s (%s)' % \
                   (movie_info['title'], movie_info['release_date'][:4])
            EmcNotify(text, icon = get_poster_filename(movie_info['id']))
         except:
            pass

      # clear the 'semaphore', now another file can be processed
      self._current_url = None

      # update the browser view
      self._browser.refresh()

      # delete TMDBv3 object
      del self._tmdb
      self._tmdb = None


###### UTILS
def get_poster_filename(tmdb_id):
   return os.path.join(utils.user_conf_dir, 'movies',
                       str(tmdb_id), 'poster.jpg')

def get_backdrop_filename(tmdb_id):
   return os.path.join(utils.user_conf_dir, 'movies',
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
   """ TMDB API v3

   tmdb = TMDBv3()

   # search for a given movie name + year:
   tmdb.movie_search('Alien', 1979, search_done_cb)
   def search_done_cb(tmdb_obj, results, status):

   # get movie info + poster + backdrop:
   tmdb.get_movie_info(tmdb_id, info_done_cb, info_progress_cb)
   def info_progress_cb(tmdb, progress, stage):
   def info_done_cb(tmdb, movie_info):

   # get list of all available posters:
   tmdb.get_posters(tmdb_id, list_complete_cb)
   def list_complete_cb(tmdb, posters):

   # get list of all available backdrop:
   tmdb.get_backdrops(tmdb_id, list_complete_cb)
   def list_complete_cb(tmdb, backdrops):

   # get info for a list of casts
   tmdb.get_cast_info(cast_ids, cast_done_cb, cast_progress_cb):
   def cast_progress_cb(tmdb, progress):
   def cast_done_cb(tmdb, result):

   # abort the current operation:
   tmdb.abort()

   """
   def __init__(self, api_key=TMDB_API_KEY, lang='en'):
      self.key = api_key
      self.lang = lang
      self.base_url = 'http://api.themoviedb.org/3'
      self.dwl_handler = None
      self.done_cb = None
      self.progress_cb = None
      self.download_stage = 0

   # abort the current operation
   def abort(self):
      if self.dwl_handler:
         utils.download_abort(self.dwl_handler)
         self.dwl_handler = None

   # movie search
   def movie_search(self, name, year, done_cb):
      self.done_cb = done_cb
      self.download_stage = 1

      url = '%s/search/movie?api_key=%s&language=%s&query=%s' % \
            (self.base_url, self.key, self.lang, urllib_quote(name))
      if year: url += '&year=%s' % (year)
      DBG('TMDB Movie search query: ' + url)

      self.dwl_handler = utils.download_url_async(url, 'tmp', urlencode = False,
                              complete_cb = self._movie_search_done_cb)

   def _movie_search_done_cb(self, dest, status):
      self.dwl_handler = None

      results = []
      if status == 200:
         data = self._read_json_file_and_delete_it(dest)
         for result in  data['results']:
            try:
               results.append({
                  'tmdb_id': result['id'],
                  'title': result['title'],
                  'year': result['release_date'][:4],
                  'poster_url': self._build_img_url(result['poster_path'], 154)
               })
            except: pass
      self.done_cb(self, results, status)

   # get movie info
   def get_movie_info(self, tid, done_cb, progress_cb = None):
      self.done_cb = done_cb
      self.progress_cb = progress_cb
      self.download_stage = 2
      url = '%s/movie/%s?api_key=%s&language=%s&append_to_response=casts' % \
             (self.base_url, tid, self.key, self.lang)
      DBG('TMDB Movie query: ' + url)
      self.dwl_handler = utils.download_url_async(url, 'tmp', urlencode = False,
                           complete_cb = self._movie_info_done_cb,
                           progress_cb = self._cb_downloads_progress)

   def _movie_info_done_cb(self, dest, status):
      self.dwl_handler = None
      self.download_stage = 3

      if status != 200:
         # error, go to next step
         self._movie_poster_done_cb(dest, 200)
         return

      # store the movie data for parsing later
      data = self._read_json_file_and_delete_it(dest)
      self.movie_info = data

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
      self.download_stage = 4

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
      self.download_stage = 0

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

      for person in tmdb['casts']['cast']:
         person['profile_path'] = self._build_img_url(person['profile_path'], 154)

      for person in tmdb['casts']['crew']:
         person['profile_path'] = self._build_img_url(person['profile_path'], 154)

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
      self.done_cb(self, info)

   def _cb_downloads_progress(self, dest, tot, done):
      if tot > 0 and self.progress_cb:
         prog = float(done) / float(tot) / 4.0 + self.download_stage * 0.25
         self.progress_cb(self, prog, self.download_stage)

   # posters list
   def get_posters(self, tmdb_id, done_cb):
      self.done_cb = done_cb
      url = '%s/movie/%s/images?api_key=%s' % \
            (self.base_url, tmdb_id, self.key)
      DBG('TMDB images query: ' + url)
      self.dwl_handler = utils.download_url_async(url, 'tmp', urlencode = False,
                              complete_cb = self._poster_list_done_cb)

   def _poster_list_done_cb(self, dest, status):
      self.dwl_handler = None
      results = []
      if status == 200:
         data = self._read_json_file_and_delete_it(dest)
         for poster in data['posters']:
            results.append({
               'movie_id': data['id'],
               'thumb_url': self._build_img_url(poster['file_path'], 154),
               'url': self._build_img_url(poster['file_path'], 500)
            })
      self.done_cb(self, results)

   # backdrops list
   def get_backdrops(self, tmdb_id, done_cb):
      self.done_cb = done_cb
      url = '%s/movie/%s/images?api_key=%s' % \
            (self.base_url, tmdb_id, self.key)
      DBG('TMDB images query: ' + url)
      self.dwl_handler = utils.download_url_async(url, 'tmp', urlencode = False,
                              complete_cb = self._backdrops_list_done_cb)

   def _backdrops_list_done_cb(self, dest, status):
      self.dwl_handler = None
      results = []
      if status == 200:
         data = self._read_json_file_and_delete_it(dest)
         for backdrop in data['backdrops']:
            results.append({
               'movie_id': data['id'],
               'thumb_url': self._build_img_url(backdrop['file_path'], 300),
               'url': self._build_img_url(backdrop['file_path'], 1280)
            })
      self.done_cb(self, results)

   # get cast info
   def get_cast_info(self, cast_id, done_cb, progress_cb):
      self.done_cb = done_cb
      self.progress_cb = progress_cb

      url = '%s/person/%s?api_key=%s&language=%s&append_to_response=credits,images' % \
             (self.base_url, cast_id, self.key, self.lang)
      DBG('TMDB People query: ' + url)
      self.dwl_handler = utils.download_url_async(url, 'tmp', urlencode = False,
                                          complete_cb = self._cast_info_done_cb,
                                          progress_cb = self._cast_info_progress_cb)

   def _cast_info_progress_cb(self, dest, tot, done):
      if tot > 0 and self.progress_cb:
         self.progress_cb(self, float(done) / float(tot))

   def _cast_info_done_cb(self, dest, status):
      if status != 200:
         self.done_cb(self, None)
      else:
         data = self._read_json_file_and_delete_it(dest)
         data['profile_path'] = self._build_img_url(data['profile_path'], 185) # ARGHHHH h632
         for img in data['images']['profiles']:
            img['file_path'] = self._build_img_url(img['file_path'], 185) # ARGHHHH h632
         for movie in data['credits']['cast']:
            movie['poster_path'] = self._build_img_url(movie['poster_path'], 154)
         for movie in data['credits']['crew']:
            movie['poster_path'] = self._build_img_url(movie['poster_path'], 154)
         self.done_cb(self, data)
      
   # utils
   def _build_img_url(self, final_part, size):
      # TODO base url and sizes should be queryed with: /3/configuration
      if final_part:
         return 'http://d3gtl9l2a4fn1j.cloudfront.net/t/p/w' + str(size) + final_part

   def _read_json_file_and_delete_it(self, path):
      f = open(path, 'r')
      data = json.loads(f.read())
      f.close()
      os.remove(path)
      return data


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
