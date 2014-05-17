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

from efl import ecore, evas
from efl.elementary.image import Image

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.sdb import EmcDatabase
from epymc.gui import EmcDialog, EmcSourceSelector, EmcNotify, EmcRemoteImage

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.ini as ini
import epymc.gui as gui
import epymc.utils as utils
import epymc.events as events
import epymc.config_gui as config_gui


# debuggin stuff
from pprint import pprint
def DBG(msg):
   print('TVSHOWS: %s' % (msg))
   # pass

TVSHOWS_DB_VERSION = 3
TVDB_API_KEY = 'A5B4979B52BF8797' # Key of the user DaveMDS
DEFAULT_INFO_LANG = 'en'
DEFAULT_EPISODE_REGEXP = '[Ss]*(?P<season>[0-9]+)[Xx]*[Ee]*(?P<episode>[0-9]+)'
""" in a more readable form:
[Ss]*               # match an 'S' or 's' or nothing
(?P<season>[0-9]+)  # the season number - captured
[Xx]*               # an optional 'X' or 'x'
[Ee]*               # match an 'E' or 'e' or nothing
(?P<episode>[0-9]+) # the episode number - captured
"""

mod_instance = None


class AddSourceItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      EmcSourceSelector(done_cb = self.selector_cb, cb_data = mod)

   def selector_cb(self, fullpath, mod):
      mod._folders.append(fullpath)
      ini.set_string_list('tvshows', 'folders', mod._folders, ';')
      mod._browser.refresh(hard=True)

   def label_get(self, url, mod):
      return 'Add source'

   def icon_get(self, url, mod):
      return 'icon/plus'


class RescanItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      if not mod._scanner:
         mod._scanner = BackgroundScanner(mod._browser, mod._tvshows_db, mod._idler_db)

   def label_get(self, url, mod):
      return 'Rescan library'

   def icon_get(self, url, mod):
      return 'icon/refresh'


class SerieInfoItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      InfoPanel(mod._current_serie_name)

   def label_get(self, url, mod):
      return 'Serie info'

   def icon_get(self, url, mod):
      return 'icon/tv'


class FileItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod_instance.play_url(url)

   def label_get(self, url, mod):
      return os.path.basename(url)

   def icon_end_get(self, url, mod):
      counts = mediaplayer.play_counts_get(url)
      if counts['finished'] > 0:
         return 'icon/check_on'
      if counts['stop_at'] > 0:
         return 'icon/check_off'


class FolderItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod_instance._browser.page_add(url, os.path.basename(url),
                                     None, mod_instance.populate_url)

   def label_get(self, url, mod):
      return os.path.basename(url)

   def icon_get(self, url, mod):
      return 'icon/folder'

   def fanart_get(self, url, mod):
      if mod_instance._tvshows_db.id_exists(mod._current_serie_name):
         e = mod_instance._tvshows_db.get_data(mod._current_serie_name)
         return get_backdrop_filename(e['id'])

class SerieItemClass(EmcItemClass):
   def item_selected(self, url, serie_name):
      mod_instance._current_serie_name = serie_name
      mod_instance._current_base_path = os.path.split(url)[0]
      mod_instance._browser.page_add(url, serie_name,
                                     None, mod_instance.populate_url)

   def label_get(self, url, serie_name):
      return serie_name

   def info_get(self, url, serie_name):
      if mod_instance._tvshows_db.id_exists(serie_name):
         e = mod_instance._tvshows_db.get_data(serie_name)
         return '<title>%s</><br>%s' % (e['name'], e['overview'])

   def icon_get(self, url, serie_name):
      if mod_instance._tvshows_db.id_exists(serie_name):
         e = mod_instance._tvshows_db.get_data(serie_name)
         return get_poster_filename(e['id']) # TODO !!!!!!!!!!!! thumbnail
      else:
         return 'icon/folder'

   def poster_get(self, url, serie_name):
      if mod_instance._tvshows_db.id_exists(serie_name):
         e = mod_instance._tvshows_db.get_data(serie_name)
         return get_poster_filename(e['id'])

   def fanart_get(self, url, serie_name):
      if mod_instance._tvshows_db.id_exists(serie_name):
         e = mod_instance._tvshows_db.get_data(serie_name)
         return get_backdrop_filename(e['id'])


class EpisodeItemClass(EmcItemClass):
   
   def item_selected(self, url, episode_data):
      mod_instance.play_url(url)

   def icon_end_get(self, url, episode_data):
      counts = mediaplayer.play_counts_get(url)
      if counts['finished'] > 0:
         return 'icon/check_on'
      if counts['stop_at'] > 0:
         return 'icon/check_off'

   def label_get(self, url, episode_data):
      return '%s. %s' % (episode_data['episode_num'], episode_data['title'])

   def poster_get(self, url, episode_data):
      series_id = episode_data['series_id']
      episode_id = episode_data['id']
      return (episode_data['thumb_url'], get_episode_filename(series_id, episode_id))

   def fanart_get(self, url, episode_data):
      if mod_instance._tvshows_db.id_exists(mod_instance._current_serie_name):
         e = mod_instance._tvshows_db.get_data(mod_instance._current_serie_name)
         return get_backdrop_filename(e['id'])

   def info_get(self, url, episode_data):
      return '<title>Episode %d: %s</><br>' \
             '<hilight>Director:</> %s<br>' \
             '<hilight>Writer:</> %s<br>' \
             '<hilight>Overview:</> %s</><br>' \
             '<hilight>First aired: %s</><br>' \
             '<hilight>Guest stars: %s</><br>' % \
               (episode_data['episode_num'], episode_data['title'],
                ', '.join(episode_data['director']),
                ', '.join(episode_data['writer']),
                episode_data['overview'], episode_data['first_aired'],
                ', '.join(episode_data['guest_stars']))


class TvShowsModule(EmcModule):
   name = 'tvshows'
   label = 'Tv Shows'
   icon = 'icon/tv'
   info = """Long info for the tvshows module, explain what it does and what it
need to work well, can also use markup like <title>this</> or <b>this</>"""

   _browser = None            # the Browser widget instance
   _scanner = None            # the BackgroundScanner instance
   _tvshows_db = None         # key: show_name  data: a BIG dict
   _idler_db = None           # key: show_name  data: dict
   _current_base_path = None  # the current base folder (the user source dir)
   _current_serie_name = None # the current show name

   def __init__(self):
      DBG('Init module')

      global mod_instance
      mod_instance = self

      # create config ini section if not exists, with defaults
      ini.add_section('tvshows')
      if not ini.has_option('tvshows', 'episode_regexp'):
         ini.set('tvshows', 'episode_regexp', DEFAULT_EPISODE_REGEXP)
      if not ini.has_option('tvshows', 'info_lang'):
         ini.set('tvshows', 'info_lang', DEFAULT_INFO_LANG)
      # if not ini.has_option('tvshows', 'enable_scanner'):
         # ini.set('tvshows', 'enable_scanner', 'False')
      # if not ini.has_option('tvshows', 'badwords'):
         # ini.set('tvshows', 'badwords', DEFAULT_BADWORDS)
      # if not ini.has_option('tvshows', 'badwords_regexp'):
         # ini.set('tvshows', 'badwords_regexp', DEFAULT_BADWORDS_REGEXP)
      # if not ini.has_option('tvshows', 'tmdb_retry_days'):
         # ini.set('tvshows', 'tmdb_retry_days', '3')
      # if not ini.has_option('tvshows', 'db_names_in_list'):
         # ini.set('tvshows', 'db_names_in_list', 'True')

      # add an item in the mainmenu
      img = os.path.join(os.path.dirname(__file__), 'menu_bg.png')
      mainmenu.item_add('tvshows', 11, 'Tv Shows', img, self.cb_mainmenu)

      # add an entry in the config gui
      config_gui.root_item_add('tvshows', 51, 'Tv Shows Collection',
                               icon = 'icon/tv', callback = config_panel_cb)

      # create a browser instance
      self._browser = EmcBrowser('TvShows', 'List')

      # listen to emc events
      events.listener_add('tvshows', self._events_cb)

   def __shutdown__(self):
      DBG('Shutdown module')

      # stop listening for events
      events.listener_del('tvshows')

      # kill the idler
      if self._scanner:
         self._scanner.abort()
         self._scanner = None

      # delete mainmenu item
      mainmenu.item_del('tvshows')

      # delete config menu item
      config_gui.root_item_del('tvshows')

      # delete browser
      self._browser.delete()

      # close databases
      if self._tvshows_db is not None:
         del self._tvshows_db
      if self._idler_db is not None:
         del self._idler_db

   def play_url(self, url):
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
         self.play_url_real(url, 0)

   def _dia_yes_cb(self, dialog):
      counts = mediaplayer.play_counts_get(dialog.data_get())
      self.play_url_real(dialog.data_get(), counts['stop_at'])
      dialog.delete()

   def _dia_no_cb(self, dialog):
      self.play_url_real(dialog.data_get(), 0)
      dialog.delete()

   def play_url_real(self, url, start_from):
      mediaplayer.play_url(url, start_from = start_from)
      title = os.path.basename(url)
      poster = None
      try: 
         e = self._tvshows_db.get_data(self._current_serie_name)
         relative = url.replace(self._current_base_path, '')
         (show_name, s_num, e_num) = get_serie_from_relative_url(relative)
         title = "%s. %s" % (e_num, e['seasons'][s_num]['episodes'][e_num]['title'])
         poster = get_poster_filename(e['id'])
      except:
         pass
      mediaplayer.title_set(title)
      mediaplayer.poster_set(poster)


###### BROWSER STUFF
   def cb_mainmenu(self):
      # get folders from config
      self._folders = ini.get_string_list('tvshows', 'folders', ';')

      # if not self._folders:
         #TODO alert the user. and instruct how to add folders

      self._browser.page_add('tvshows://root', 'Tv Shows', None, self.populate_root_page)
      self._browser.show()
      mainmenu.hide()

      # open movie/idler databases (they are created if not exists)
      if self._tvshows_db is None:
         self._tvshows_db = EmcDatabase('tvshows', TVSHOWS_DB_VERSION)
      if self._idler_db is None:
         self._idler_db = EmcDatabase('tvidlercache', TVSHOWS_DB_VERSION)

      # on idle scan all files (one shot every time the activity start)
      # if not self._scanner and ini.get_bool('movies', 'enable_scanner'):
         # self._scanner = BackgroundScanner(self._browser, self._movie_db, self._idler_db)


   def populate_root_page(self, browser, page_url):
      for folder in self._folders:
         if folder.startswith('file://'):
            folder = folder[7:]
         for fname in sorted(os.listdir(folder), key=str.lower):
            if fname[0] == '.': continue
            full_path = os.path.join(folder, fname)
            if os.access(full_path, os.R_OK) and os.path.isdir(full_path):
               item_url = 'file://' + full_path
               self._browser.item_add(SerieItemClass(), item_url, fname)

      self._browser.item_add(RescanItemClass(), 'tvshows://rescan_library', self)
      self._browser.item_add(AddSourceItemClass(), 'tvshows://add_source', self)

   def populate_url(self, browser, url):
      # build ordered list of files and dirs (relative to the show base dir)
      dirs, files = [], []
      for fname in sorted(os.listdir(url[7:]), key=str.lower):
         if fname[0] == '.': continue
         relative = url.replace(self._current_base_path, '')
         if os.path.isdir(os.path.join(url[7:], fname)):
            dirs.append(os.path.join(relative, fname))
         else:
            files.append(os.path.join(relative, fname))

      # populate directories
      for relative in dirs:
         item_url = self._current_base_path + relative
         # TODO 
         # try:
            # (show_name, s_num, e_num) = get_serie_from_relative_url(relative)
            # DBG([show_name, s_num, e_num])
         # except:
         self._browser.item_add(FolderItemClass(), item_url, self)

      # then populate files
      for relative in files:
         item_url = self._current_base_path + relative
         try:
            (show_name, s_num, e_num) = get_serie_from_relative_url(relative)
            DBG([show_name, s_num, e_num])
            e = self._tvshows_db.get_data(show_name)
            episode_data = e['seasons'][s_num]['episodes'][e_num]
            self._browser.item_add(EpisodeItemClass(), item_url, episode_data)
         except:
            self._browser.item_add(FileItemClass(), item_url, self)

      self._browser.item_add(SerieInfoItemClass(), 'tvshows://rescan_library', self)


   def _events_cb(self, event):
      # TODO: check that we are active and visible
      #       atm, this is fired also when a song end...
      if event == 'PLAYBACK_FINISHED':
         # refresh the page (maybe an unwatched movie becomes watched)
         if self._browser is not None:
            self._browser.refresh()


class InfoPanel(EmcDialog):
   def __init__(self, serie_name):
      self._serie_name = serie_name
      if mod_instance._tvshows_db.id_exists(serie_name):
         self._db_data = mod_instance._tvshows_db.get_data(serie_name)
      else:
         self._db_data = None

      self._image = Image(gui.win)
      EmcDialog.__init__(self, style = 'panel', title = serie_name,
                         text = ' ', content = self._image)
      self.button_add('Posters', self._posters_button_cb)
      self.button_add('Backdrops', self._backdrop_button_cb)
      self.button_add('Banners', self._banners_button_cb)
      self.button_add('Actors (TODO)', self._actors_button_cb)
      self.button_add('Refresh info', self._refresh_info_button_cb)
      self.update()

   def update(self):
      if self._db_data:
         d = self._db_data
         info = '<hilight>First aired: </hilight> %s <br>' \
                '<hilight>Network:</hilight> %s<br>' \
                '<hilight>Seasons:</hilight> %s<br>' \
                '<hilight>Genres:</hilight> %s<br>' \
                '<hilight>Runtime:</hilight> %s min<br>' \
                '<hilight>Rating:</hilight> %s<br>' \
                '<hilight>Status:</hilight> %s<br>' \
                '<br><hilight>Overview:</hilight><br>%s<br>' \
                '<br><hilight>Actors:</hilight> %s<br>' \
                  % (d['first_aired'], d['network'], len(d['seasons']),
                     ', '.join(d['genres']), d['runtime'], d['rating'],
                     d['status'], d['overview'], ', '.join(d['casts']))

         self._image.file = get_poster_filename(self._db_data['id'])
         self.text_set(info)
      else:
         text = 'No info stored for this serie.<br>' \
                'Please try the "refresh info" button.'
         self.text_set(text)

   ### images
   def _posters_button_cb(self, button):
      title = '%s posters found' % len(self._db_data['posters'])
      dia = EmcDialog(style = 'image_list_horiz', title = title,
                      done_cb = self._image_choosed_cb)
      for poster in self._db_data['posters']:
         icon = EmcRemoteImage(poster['thumb_url'])
         dia.list_item_append(None, icon, dwnl_url = poster['url'],
                     dest_path = get_poster_filename(self._db_data['id']))

   def _backdrop_button_cb(self, button):
      title = '%s backdrops found' % len(self._db_data['backdrops'])
      dia = EmcDialog(style = 'image_list_vert', title = title,
                      done_cb = self._image_choosed_cb)
      for backdrop in self._db_data['backdrops']:
         icon = EmcRemoteImage(backdrop['thumb_url'])
         dia.list_item_append(None, icon, dwnl_url = backdrop['url'],
                     dest_path = get_backdrop_filename(self._db_data['id']))

   def _banners_button_cb(self, button):
      title = '%s banners found' % len(self._db_data['banners'])
      dia = EmcDialog(style = 'image_list_vert', title = title,
                      done_cb = self._image_choosed_cb)
      for banner in self._db_data['banners']:
         icon = EmcRemoteImage(banner['url'])
         dia.list_item_append(None, icon, dwnl_url = banner['url'],
                     dest_path = get_banner_filename(self._db_data['id']))

   def _image_choosed_cb(self, dia, dwnl_url, dest_path):
      dia.delete()
      dia = EmcDialog(style = 'progress', title = 'Downloading image')
      utils.download_url_async(dwnl_url, dest_path,
                               complete_cb = self._cb_image_done,
                               progress_cb = self._cb_image_progress,
                               dia = dia)

   def _cb_image_progress(self, dest, tot, done, dia):
      if tot > 0: dia.progress_set(float(done) / float(tot))

   def _cb_image_done(self, dest, status, dia):
      if os.path.basename(dest) == 'poster.jpg':
         self._image.file = dest
      mod_instance._browser.refresh()
      dia.delete()

   ### actors
   def _actors_button_cb(self, button):
      DBG("TODO")

   ### refresh infos
   def _refresh_info_button_cb(self, button):
      tvdb = TVDB(lang = ini.get('tvshows', 'info_lang'))
      tvdb.search_series_by_name(self._serie_name, self._search_done_cb)

   def _search_done_cb(self, tvdb, results, status):
      if status == 200 and len(results) > 0:
         title = 'Found %d results, which one?' % len(results)
         dia = EmcDialog(style = 'image_list_vert', title = title,
                         done_cb = self._result_choosed_cb,
                         user_data = tvdb)
         for item in results:
            if item['banner']:
               img = EmcRemoteImage(item['banner'])
               dia.list_item_append(None, img, serie_id = item['id'])
      else:
         text = 'The search for "%s" did not make any results.<br>' \
                'If your show is listed on thetvdb.com please rename ' \
                'your folder to match the title on the site.<br>' \
                'If otherwise it is not in the online database please ' \
                'contribute and add it yourself.' % self._serie_name
         EmcDialog(style = 'minimal', title = 'Nothing found', text = text)

   def _result_choosed_cb(self, dia, serie_id):
      tvdb = dia.data_get()
      tvdb.fetch_all_data_for_serie(serie_id, self._refresh_done_cb)

      dia.delete()
      # TODO give credits here
      self._prog_dia = EmcDialog(style = 'minimal', spinner = True,
                                 title = 'Fetching updated info',
                                 text = 'Please wait...')

   def _refresh_done_cb(self, tvdb, data, status):
      self._prog_dia.delete()
      if status == 200 and data:
         mod_instance._tvshows_db.set_data(self._serie_name, data)
         self._db_data = data
         self.update()
      
   

###### Utils
def get_serie_from_relative_url(url):
   """
   TESTCASES:
   /Prison Break/Season 1/PrisonBreak - 1x01 - Pilot.avi
   /Prison Break/Season 1/1x01 - Pilot.avi
   /Prison Break/Season 1/01 - Pilot.avi              # TODO this is not supported ATM....
   /Prison Break/PrisonBreak - 1x01 - Pilot.avi
   /Prison Break/1x01 - Pilot.avi
   /Prison Break/s1e01 - Pilot.avi
   /Prison Break/s01e01 - Pilot.avi
   """

   # split the url in a list
   parts = utils.splitpath(url)
   if len(parts) < 2:
      return None

   # the serie name is always the first folder name
   serie = parts[0]

   # now search a season/episode number in the filename
   # 01x13 or s1e13
   regexp = re.compile(ini.get('tvshows', 'episode_regexp'))
   m = regexp.search(parts[-1])
   if m is not None:
      season = int(m.group('season'))
      episode = int(m.group('episode'))
      return (serie, season, episode)

def get_poster_filename(tvshows_id):
   return os.path.join(utils.user_conf_dir, 'tvshows',
                       str(tvshows_id), 'poster.jpg')

def get_backdrop_filename(tvshows_id):
   return os.path.join(utils.user_conf_dir, 'tvshows',
                       str(tvshows_id), 'backdrop.jpg')

def get_banner_filename(tvshows_id):
   return os.path.join(utils.user_conf_dir, 'tvshows',
                       str(tvshows_id), 'banner.jpg')

def get_episode_filename(tvshows_id, episode_id):
   return os.path.join(utils.user_conf_dir, 'tvshows',
                       str(tvshows_id), episode_id + '.jpg')


###### Config Panel stuff
def config_panel_cb():
   bro = config_gui.browser_get()
   bro.page_add('config://tvshows/', 'Tv Shows', None, populate_config)

def populate_config(browser, url):
   config_gui.standard_item_string_add('tvshows', 'info_lang',
                                       'Preferred language for contents')


class BackgroundScanner(ecore.Idler):
   def __init__(self, browser, tvshows_db, idler_db): #, browser):
      self._browser = browser         # the module browser instance
      self._tvshows_db = tvshows_db   # tvshow db instance
      self._idler_db = idler_db       # idler db instance
      self._step_func = self._step1   # start with step1
      self._series_to_update = []     # list of series names to update
      self._dwl_h = {}                # all the download in progress
      self._generator = None          # the file generator instance
      self._tvdb = None               # the TVDB instance
      self._current_serie_name = None # also used as a semaphore
      self._current_serie_data = None # the whole data (for the notification)
      self._retry_after = 1 * 24 * 60 * 60

      ecore.Idler.__init__(self, lambda: self._step_func())

   def abort(self):
      # stop the idler
      self.delete()
      # abort any download in progress
      for handler in self._dwl_h.values():
         utils.download_abort(handler)
      self._dwl_h.clear()
      # abort any tmdb operations
      if self._tvdb:
         self._tvdb.abort()
         del self._tvdb
         self._tvdb = None

   ### Step 1
   def _step1(self):
      """ Step 1: Build a list of all the tv shows. """

      # the first time create the generator
      if self._generator is None:
         EmcNotify("TvShows scanner started")
         sources = ini.get_string_list('tvshows', 'folders', ';')
         folders = [f.replace('file://', '') for f in sources]
         self._generator = utils.grab_files(folders, recursive = False)

      # get the next filename from the generator
      try:
         full_path = next(self._generator)
         if os.path.isdir(full_path):
            filename = os.path.basename(full_path)
            if not filename in self._series_to_update:
               self._series_to_update.append(filename)
      except StopIteration:
         self._generator = None
         self._step_func = self._step2

      return ecore.ECORE_CALLBACK_RENEW

   ### Step 
   def _step2(self):
      """ Step 2: Check and eventually fetch updated info for all the series """

      # do not process more than one series at a time
      if self._current_serie_name is not None:
         return ecore.ECORE_CALLBACK_RENEW

      # get the next serie title, or finish all when no more items available
      try:
         serie_name = self._series_to_update.pop()
      except IndexError:
         EmcNotify("TvShows scanner done")
         DBG("scanner done")
         return ecore.ECORE_CALLBACK_CANCEL

      DBG("UPDATING: " + serie_name)

      # check the last time we searched for this serie
      if self._idler_db.id_exists(serie_name):
         cache = self._idler_db.get_data(serie_name)
         elapsed = time.time() - cache['last_search_time']
         if elapsed < self._retry_after:
            DBG('I searched "%s" %d seconds ago...skipping' % (serie_name, elapsed))
            return ecore.ECORE_CALLBACK_RENEW

      # perform a tvdb search by title
      self._current_serie_name = serie_name
      if self._tvdb is None:
         self._tvdb = TVDB(lang = ini.get('tvshows', 'info_lang'))
      self._tvdb.search_series_by_name(serie_name, self._search_done_cb)
      return ecore.ECORE_CALLBACK_RENEW

   def _search_done_cb(self, tvdb, results, status):
      if status == 200 and len(results) > 0:
         tvdb.fetch_all_data_for_serie(results[0]['id'], self._fetch_data_done_cb)
      else:
         self._fetch_data_done_cb(tvdb, None, 1)

   def _fetch_data_done_cb(self, tvdb, result, status):
      # store result info into the idler-db
      self._idler_db.set_data(self._current_serie_name, {
         'last_search_time': time.time(),
         'last_search_success': True if (status == 200 and result) else False
      })

      if status == 200 and result:
         # store the data into tvshow-db
         self._tvshows_db.set_data(self._current_serie_name, result)

         # remember the data to show the notificationa at the end
         self._current_serie_data = result

         # now download the backdrop/poster/banner default images
         self._dwl_h['bd'] = utils.download_url_async(result['backdrop_url'],
                                       get_backdrop_filename(result['id']),
                                       complete_cb = self._images_done_cb,
                                       img_type = 'bd')
         self._dwl_h['po'] = utils.download_url_async(result['poster_url'],
                                       get_poster_filename(result['id']),
                                       complete_cb = self._images_done_cb,
                                       img_type = 'po')
         self._dwl_h['ba'] = utils.download_url_async(result['banner_url'],
                                       get_banner_filename(result['id']),
                                       complete_cb = self._images_done_cb,
                                       img_type = 'ba')
      else:
         # clear the "semaphore", now another serie can be processed
         self._current_serie_name = None
         self._current_serie_data = None

   def _images_done_cb(self, dest, status, img_type):
      del self._dwl_h[img_type]
      if not self._dwl_h: # dict empty, all downloads done
         # show a cool notification
         data = self._current_serie_data
         text = '<title>Found serie:</><br>%s<br>%s seasons' % \
                (data['name'], len(data['seasons']))
         EmcNotify(text, icon = get_poster_filename(data['id']))
         # refresh the browser view
         self._browser.refresh()
         
         # clear the "semaphore", now another serie can be processed
         self._current_serie_name = None
         self._current_serie_data = None


###### thetvdb.com XML api implementation
import xml.etree.ElementTree as ElementTree
import zipfile

try:
   from urllib.parse import quote as urllib_quote
except:
   from urllib import quote as urllib_quote

class TVDB(object):
   """ thetvdb.com XML api implementation

   tvdb = TVDB()

   # to search for a serie by name (return list of matching results):
   tvdb.search_series_by_name(serie_name, done_cb)
   def done_cb(tvdb, results, status):

   # to fetch ALL the info for a given series_id:
   tvdb.fetch_all_data_for_serie(serie_id, done_cb)
   def done_cb(tvdb, data, status):

   # abort all the current operations:
   tmdb.abort()

   """
   def __init__(self, apikey = TVDB_API_KEY, lang = 'en'):
      self._apikey = apikey
      self._lang = lang
      self._base_url = 'http://thetvdb.com/api'
      self._dwl_handler = None
      self._done_cb = None

   # abort the current operation
   def abort(self):
      if self._dwl_handler:
         utils.download_abort(self._dwl_handler)
         self._dwl_handler = None

   ## search series by name
   def search_series_by_name(self, serie_name, done_cb):
      self._done_cb = done_cb
      url = '%s/GetSeries.php?seriesname=%s&language=%s' % \
            (self._base_url, urllib_quote(serie_name), self._lang)
      DBG('TVDB: Search serie query: ' + url)
      self._dwl_handler = utils.download_url_async(url, 'tmp',
                              urlencode = False,
                              complete_cb = self._name_search_done_cb)

   def _name_search_done_cb(self, dest, status):
      self._dwl_handler = None
      results = []
      
      if status == 200:
         tree = self._parse_xml_file_and_delete_it(dest)
         for serie in tree.findall('Series'):
            results.append({
               'id': serie.findtext('seriesid'),
               'name': serie.findtext('SeriesName'),
               'banner': self._build_image_url(serie.findtext('banner')),
            })

      self._done_cb(self, results, status)

   # fetch all data for the given serie_id
   def fetch_all_data_for_serie(self, serie_id, done_cb):
      self._done_cb = done_cb
      url = '%s/%s/series/%s/all/%s.zip' % \
            (self._base_url, self._apikey, serie_id, self._lang)
      DBG('TVDB: Fetch data query: ' + url)

      self._dwl_handler = utils.download_url_async(url, 'tmp',
                              urlencode = False,
                              complete_cb = self._fetch_zip_done_cb)

   def _fetch_zip_done_cb(self, dest, status):
      self._dwl_handler = None

      if status != 200:
         self._done_cb(self, None, status)
         return

      data = None
      
      with zipfile.ZipFile(dest, 'r') as Z:
         # read and parse the <lang>.xml file
         with Z.open(self._lang + '.xml') as f:
            data = self._parse_general_info(f)
         # read and parse the banners.xml file
         with Z.open('banners.xml') as f:
            (backdrops, posters, banners) = self._parse_banners(f)
            data['backdrops'] = backdrops
            data['posters'] = posters
            data['banners'] = banners
         # TODO actors.xml
         
      # remove the downloaded zip file
      os.remove(dest)

      # call the complete callback
      self._done_cb(self, data, status)

   def _parse_banners(self, file_obj):
      # read the XML from the file-like object
      tree = ElementTree.parse(file_obj)

      backdrops = []
      posters = []
      banners = []

      for image in tree.findall('Banner'):
         banner_type = image.findtext('BannerType')
         banner_type2 = image.findtext('BannerType2')

         # backdrops
         if banner_type == 'fanart': 
            url = self._build_image_url(image.findtext('BannerPath'))
            thumb_url = self._build_image_url(image.findtext('ThumbnailPath'))
            backdrops.append({
               'url': url,
               'thumb_url': thumb_url,
               'lang': image.findtext('Language'),
            })

         # posters (with optionally the season)
         elif banner_type == 'poster' or \
              (banner_type == 'season' and banner_type2 == 'season'):
            url = self._build_image_url(image.findtext('BannerPath'))
            # UNDOCUMENTED: posters dont have the thumb... guessing one
            thumb_url = url.replace('banners/', 'banners/_cache/')
            posters.append({
               'url': url,
               'thumb_url': thumb_url,
               'lang': image.findtext('Language'),
               'season': image.findtext('Season'),
            })

         # banners (with optionally the season)
         elif banner_type == 'series' or \
             (banner_type == 'season' and banner_type2 == 'seasonwide'):
            url = self._build_image_url(image.findtext('BannerPath'))
            # UNDOCUMENTED: banners dont have the thumb... guessing one
            thumb_url = url.replace('banners/', 'banners/_cache/')
            banners.append({
               'url': url,
               'thumb_url': thumb_url,
               'lang': image.findtext('Language'),
               'season': image.findtext('Season'),
            })

      return (backdrops, posters, banners)
      
   def _parse_general_info(self, file_obj):
      # read the XML from the file-like object
      tree = ElementTree.parse(file_obj)

      # parse general serie info
      serie = tree.find('Series')
      data = {
         'id': serie.findtext('id'),
         'name': serie.findtext('SeriesName'),
         'casts': serie.findtext('Actors').split('|')[1:-1],
         'first_aired': serie.findtext('FirstAired'),
         'genres': serie.findtext('Genre').split('|')[1:-1],
         'network': serie.findtext('Network'),
         'overview': serie.findtext('Overview'),
         'rating': serie.findtext('Rating'),
         'status': serie.findtext('Status'),
         'banner_url': self._build_image_url(serie.findtext('banner')),
         'backdrop_url': self._build_image_url(serie.findtext('fanart')),
         'poster_url': self._build_image_url(serie.findtext('poster')),
         'runtime': serie.findtext('Runtime'),
         'seasons': {},
      }

      # parse seasons/episodes info
      seasons = {}
      for episode in tree.findall('Episode'):
         season_num = int(episode.findtext('SeasonNumber'))
         episode_num = int(episode.findtext('EpisodeNumber'))
         
         if not season_num in seasons:
            seasons[season_num] = {
               'season_num': season_num,
               # TODO season poster
               'episodes': {}
            }

         seasons[season_num]['episodes'][episode_num] = {
            'id': episode.findtext('id'),
            'series_id': data['id'],
            'title': episode.findtext('EpisodeName'),
            'season_num': season_num,
            'episode_num': episode_num,
            'director': episode.findtext('Director', '||').split('|')[1:-1],
            'writer': episode.findtext('Writer', '||').split('|')[1:-1],
            'overview': episode.findtext('Overview'),
            'first_aired': episode.findtext('FirstAired'),
            'guest_stars': episode.findtext('GuestStarts', '||').split('|')[1:-1],
            'thumb_url': self._build_image_url(episode.findtext('filename')),
         }

      data['seasons'] = seasons

      return data

   # utils
   def _build_image_url(self, final_part):
      if final_part is not None:
         return 'http://www.thetvdb.com/banners/' + final_part

   def _parse_xml_file_and_delete_it(self, path):
      tree = ElementTree.parse(path)
      os.remove(path)
      return tree


""" idler_db Reference
{
   MacGyver: {
      last_search_time: local-timestamp,
      last_search_success: bool,
   },
   ...
}
"""


""" tvshows_db Reference
{
   MacGyver: {
      id: 77847
      name: MacGyver
      ...
      seasons: {
         1: {
            season_num: 1,
            episodes: {
               1: {
                  id: 12345,
                  series_id: 45678,
                  title: Pilot,
                  episode_num: 1,
                  season_num: 3,
                  thumb_url: http://...
                  ...
               },
               2: {...},
            }
         },
         2: {
            season_num: 2,
            episodes: {...}
         },
         ...
      },
      backdrops: [
         {
            url: http://... ,
            thumb_url: http://... ,
            lang: en,
         },
         ...
      ],
      posters: [
         {
            url: http://... ,
            thumb_url: http://... ,
            lang: en,
            season: 2 or None
         },
         ...
      ],
      banners: [
         {
            url: http://... ,
            thumb_url: http://... ,
            lang: en,
            season: 2 or None
         },
         ...
      ],
   },
   ...
}
"""
