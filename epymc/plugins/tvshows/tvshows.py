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
from epymc.gui import EmcDialog, EmcSourcesManager, EmcNotify, EmcRemoteImage
from epymc.themoviedb import TMDBv3, CastPanel, get_tv_backdrop_filename, \
   get_tv_poster_filename, get_tv_icon_filename

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.ini as ini
import epymc.gui as gui
import epymc.utils as utils
import epymc.events as events
import epymc.config_gui as config_gui


# debuggin stuff
def DBG(msg):
   print('TVSHOWS: %s' % (msg))
   # pass

TVSHOWS_DB_VERSION = 4
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
      EmcSourcesManager('tvshows', done_cb=self._manager_cb)

   def _manager_cb(self, sources):
      mod_instance._folders = sources
      mod_instance._browser.refresh(hard=True)

   def label_get(self, url, mod):
      return _('Manage sources')

   def icon_get(self, url, mod):
      return 'icon/plus'


class RescanItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      if not mod._scanner:
         mod._scanner = BackgroundScanner(mod._browser, mod._tvshows_db, mod._idler_db)

   def label_get(self, url, mod):
      return _('Rescan library')

   def icon_get(self, url, mod):
      return 'icon/refresh'


class SerieInfoItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      InfoPanel(mod._current_serie_name)

   def label_get(self, url, mod):
      return _('Serie info')

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
         return get_tv_backdrop_filename(e['id'])


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
         return get_tv_icon_filename(e['id'])
      else:
         return 'icon/folder'

   def poster_get(self, url, serie_name):
      if mod_instance._tvshows_db.id_exists(serie_name):
         e = mod_instance._tvshows_db.get_data(serie_name)
         return get_tv_poster_filename(e['id'])

   def fanart_get(self, url, serie_name):
      if mod_instance._tvshows_db.id_exists(serie_name):
         e = mod_instance._tvshows_db.get_data(serie_name)
         return get_tv_backdrop_filename(e['id'])


class SeasonItemClass(EmcItemClass):
   def item_selected(self, url, season_num):
      mod_instance._browser.page_add(url, os.path.basename(url),
                                     None, mod_instance.populate_url)

   def label_get(self, url, season_num):
      return os.path.basename(url)

   def icon_get(self, url, season_num):
      serie_name = mod_instance._current_serie_name
      if mod_instance._tvshows_db.id_exists(serie_name):
         e = mod_instance._tvshows_db.get_data(serie_name)

         icon_file = get_tv_icon_filename(e['id'], season_num)
         if os.path.exists(icon_file):
            return icon_file

         icon_file = get_tv_icon_filename(e['id'])
         if os.path.exists(icon_file):
            return icon_file

      return 'icon/folder'

   def poster_get(self, url, season_num):
      serie_name = mod_instance._current_serie_name
      if mod_instance._tvshows_db.id_exists(serie_name):
         e = mod_instance._tvshows_db.get_data(serie_name)

         poster_file = get_tv_poster_filename(e['id'], season_num)
         if os.path.exists(poster_file):
            return poster_file

         return get_tv_poster_filename(e['id'])

   def fanart_get(self, url, season_num):
      serie_name = mod_instance._current_serie_name
      if mod_instance._tvshows_db.id_exists(serie_name):
         e = mod_instance._tvshows_db.get_data(serie_name)
         return get_tv_backdrop_filename(e['id'])


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
      season_num = episode_data['season_num']
      episode_id = episode_data['id']
      if episode_data['thumb_url']:
         # episode thumb
         return (episode_data['thumb_url'],
                 get_tv_poster_filename(series_id, episode_id=episode_id))
      else:
         # season poster
         poster_file = get_tv_poster_filename(series_id, season_num)
         if os.path.exists(poster_file):
            return poster_file
         else:
            # serie poster
            return get_tv_poster_filename(series_id)
         

   def fanart_get(self, url, episode_data):
      if mod_instance._tvshows_db.id_exists(mod_instance._current_serie_name):
         e = mod_instance._tvshows_db.get_data(mod_instance._current_serie_name)
         return get_tv_backdrop_filename(e['id'])

   def info_get(self, url, episode_data):
      return _('<title>Episode %d: %s</title><br>' \
               '<hilight>First aired:</hilight> %s<br>'  \
               '<hilight>Overview:</hilight> %s</><br>') % (
                  episode_data['episode_num'], episode_data['title'],
                  episode_data['first_aired'],
                  episode_data['overview'])


class TvShowsModule(EmcModule):
   name = 'tvshows'
   label = _('TV Shows')
   icon = 'icon/tv'
   info = _("""Long info for the tvshows module, explain what it does and what it
need to work well, can also use markup like <title>this</> or <b>this</>""")

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
      mainmenu.item_add('tvshows', 11, _('TV Shows'), 'icon/tv', self.cb_mainmenu)

      # add an entry in the config gui
      config_gui.root_item_add('tvshows', 51, _('Tv Shows Collection'),
                               icon='icon/tv', callback=config_panel_cb)

      # create a browser instance
      self._browser = EmcBrowser(_('TV Shows'), 'List')

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
         EmcDialog(text=_('Continue from %d:%.2d:%.2d ?') % (h, m, s),
                   style='yesno', user_data=url,
                   done_cb=self._dia_yes_cb,
                   canc_cb=self._dia_no_cb)
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
      mediaplayer.play_url(url, start_from=start_from)
      title = os.path.basename(url)
      poster = None
      try: 
         e = self._tvshows_db.get_data(self._current_serie_name)
         relative = url.replace(self._current_base_path, '')
         (show_name, s_num, e_num) = get_serie_from_relative_url(relative)
         title = "%s. %s" % (e_num, e['seasons'][s_num]['episodes'][e_num]['title'])
         poster = get_tv_poster_filename(e['id'])
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

      self._browser.page_add('tvshows://root', _('TV Shows'), None, self.populate_root_page)
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
      for fname in utils.natural_sort(os.listdir(url[7:])):
         if fname[0] == '.': continue
         relative = url.replace(self._current_base_path, '')
         if os.path.isdir(os.path.join(url[7:], fname)):
            dirs.append(os.path.join(relative, fname))
         else:
            files.append(os.path.join(relative, fname))

      # populate directories
      for relative in dirs:
         item_url = self._current_base_path + relative
         try:
            (show_name, s_num) = get_serie_from_relative_dir_url(relative)
            self._browser.item_add(SeasonItemClass(), item_url, s_num)
         except:
            self._browser.item_add(FolderItemClass(), item_url, self)

      # then populate files
      for relative in files:
         item_url = self._current_base_path + relative
         try:
            (show_name, s_num, e_num) = get_serie_from_relative_url(relative)
            e = self._tvshows_db.get_data(show_name)
            episode_data = e['seasons'][s_num]['episodes'][e_num]
            self._browser.item_add(EpisodeItemClass(), item_url, episode_data)
         except:
            self._browser.item_add(FileItemClass(), item_url, self)

      self._browser.item_add(SerieInfoItemClass(), 'tvshows://refresh_serie', self)

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
      EmcDialog.__init__(self, style='panel', title=serie_name,
                         text=' ', content=self._image)
      self.button_add(_('Posters'), self._posters_button_cb)
      self.button_add(_('Backdrops'), self._backdrop_button_cb)
      self.button_add(_('Cast'), self._cast_button_cb)
      self.button_add(_('Refresh info'), self._refresh_info_button_cb)
      self.update()

   def update(self):
      if self._db_data:
         d = self._db_data
         info = _('<hilight>Created by: </hilight> %s <br>' \
                  '<hilight>Network:</hilight> %s<br>' \
                  '<hilight>First aired: </hilight> %s <br>' \
                  '<hilight>Last aired: </hilight> %s <br>' \
                  '<hilight>Seasons:</hilight> %s<br>' \
                  '<hilight>Episodes:</hilight> %s<br>' \
                  '<hilight>Genres:</hilight> %s<br>' \
                  '<hilight>Runtime:</hilight> %s min<br>' \
                  '<hilight>Rating:</hilight> %s/10<br>' \
                  '<hilight>Status:</hilight> %s<br>' \
                  '<br><hilight>Overview:</hilight><br>%s<br>') % (
                     ', '.join(d['created_by']),
                     ', '.join(d['networks']),
                     d['first_air_date'],
                     d['last_air_date'],
                     d['number_of_seasons'],
                     d['number_of_episodes'],
                     ', '.join(d['genres']),
                     d['episode_run_time'],
                     d['vote_average'],
                     d['status'], d['overview'],
                  )
         info = info.replace('&', '&amp;')
         try:
            self._image.file = get_tv_poster_filename(self._db_data['id'])
         except: pass
         self.text_set(info)
      else:
         text = _('No info stored for this serie.<br>' \
                  'Please try the <i>refresh info</i> button.')
         self.text_set(text)

   ### images
   def _posters_button_cb(self, button):
      tmdb = TMDBv3(lang=ini.get('tvshows', 'info_lang'))
      tmdb.get_posters(self._db_data['id'], self._posters_cb, tv=True)

   def _posters_cb(self, tmdb, results):
      title = _('%d posters available') % len(results)
      dia = EmcDialog(style='image_list_horiz', title=title,
                      done_cb=self._image_choosed_cb)
      for poster in results:
         icon = EmcRemoteImage(poster['thumb_url'])
         dia.list_item_append(None, icon, dwnl_url=poster['url'],
                     dest_path=get_tv_poster_filename(poster['movie_id']),
                     icon_url=poster['icon_url'])

   def _backdrop_button_cb(self, button):
      tmdb = TMDBv3(lang=ini.get('tvshows', 'info_lang'))
      tmdb.get_backdrops(self._db_data['id'], self._backdrops_cb, tv=True)

   def _backdrops_cb(self, tmdb, results):
      title = _('%d backdrops available') % len(results)
      dia = EmcDialog(style='image_list_vert', title=title,
                      done_cb=self._image_choosed_cb)
      for backdrop in results:
         icon = EmcRemoteImage(backdrop['thumb_url'])
         dia.list_item_append(None, icon, dwnl_url=backdrop['url'],
                     dest_path=get_tv_backdrop_filename(backdrop['movie_id']))

   def _image_choosed_cb(self, dia, dwnl_url, dest_path, icon_url=None):
      dia.delete()
      dia = EmcDialog(style='progress', title=_('Downloading image'))
      utils.download_url_async(dwnl_url, dest_path,
                               complete_cb=self._cb_image_done,
                               progress_cb=self._cb_image_progress,
                               dia=dia)
      # also download icon for poster
      if icon_url and dest_path.endswith('/poster.jpg'):
         icon_path = dest_path.replace('poster.jpg', 'icon.jpg')
         utils.download_url_async(icon_url, icon_path)

   def _cb_image_progress(self, dest, tot, done, dia):
      if tot > 0: dia.progress_set(float(done) / float(tot))

   def _cb_image_done(self, dest, status, dia):
      if os.path.basename(dest) == 'poster.jpg':
         self._image.file = dest
      mod_instance._browser.refresh()
      dia.delete()

   ### cast
   def _cast_button_cb(self, button):
      dia = EmcDialog(title=_('Cast'), style='list',
                      done_cb=lambda d, pid: CastPanel(pid))
      dia.button_add(_('Info'), self._cast_info_cb, dia)

      for person in self._db_data['cast']:
         label = _('%s as %s') % (person['name'], person['character'])
         icon = EmcRemoteImage(person['profile_path']) # TODO use 'dest' to cache the img
         icon.size_hint_min_set(100, 100) # TODO FIXME
         dia.list_item_append(label, icon, None, person['id'])

   def _cast_info_cb(self, button, list_dia):
      item = list_dia.list_item_selected_get()
      pid = item.data_get()[0][0]
      CastPanel(pid)

   ### refresh infos
   def _refresh_info_button_cb(self, button):
      tmdb = TMDBv3(lang=ini.get('tvshows', 'info_lang'))
      tmdb.tv_search(self._serie_name, self._search_done_cb)

   def _search_done_cb(self, tmdb, results):
      if len(results) == 1:
         self._result_choosed_cb(None, results[0]['tmdb_id'])
      elif len(results) > 1:
         title = _('Found %d results, which one?') % len(results)
         dia = EmcDialog(style='list', title=title,
                         done_cb=self._result_choosed_cb)
         for item in results:
            if item['poster_url']:
               img = EmcRemoteImage(item['poster_url'])
               img.size_hint_min_set(100, 100) # TODO fixme
            else:
               img = None
            if item['year']:
               name = '%s (%s)' % (item['name'], item['year'])
            else:
               name = item['name']
            dia.list_item_append(name, img, serie_id=item['tmdb_id'])
      else:
         text = _('The search for "%s" did not make any results.<br>' \
                  'If your show is listed on themoviedb.org please rename ' \
                  'your folder to match the title on the site.<br>' \
                  'If otherwise it is not in the online database please ' \
                  'contribute and add it yourself.') % self._serie_name
         EmcDialog(style='minimal', title=_('Nothing found'), text=text)

   def _result_choosed_cb(self, dia, serie_id):
      if dia: dia.delete()

      tmdb = TMDBv3(lang=ini.get('tvshows', 'info_lang'))
      tmdb.get_tv_info(serie_id, self._refresh_done_cb, self._refresh_prog_cb)

      self._prog_dia = EmcDialog(style='progress',
                                 title=_('Fetching updated info'),
                                 content=gui.load_image('tmdb_logo.png'))

   def _refresh_prog_cb(self, tvdb, progress):
      self._prog_dia.progress_set(progress)
      
   def _refresh_done_cb(self, tvdb, data):
      self._prog_dia.delete()
      if data:
         mod_instance._tvshows_db.set_data(self._serie_name, data)
         self._db_data = data
         self.update()
         mod_instance._browser.refresh()


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

def get_serie_from_relative_dir_url(url):
   """
   TESTCASES:
   /Prison Break/Season 1
   """
   # split the url in a list
   parts = utils.splitpath(url)

   # the serie name is always the first folder name
   serie = parts[0]

   # now search the first number in the second folder name
   try:
      return (serie, int(re.findall('\d+', parts[1])[0]))
   except:
      return None


###### Config Panel stuff
def config_panel_cb():
   bro = config_gui.browser_get()
   bro.page_add('config://tvshows/', _('TV Shows'), None, populate_config)

def populate_config(browser, url):
   config_gui.standard_item_string_add('tvshows', 'info_lang',
                                       _('Preferred language for contents'))


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
         EmcNotify(_('TvShows scanner started'))
         sources = ini.get_string_list('tvshows', 'folders', ';')
         folders = [f.replace('file://', '') for f in sources]
         self._generator = utils.grab_files(folders, recursive=False)

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
         EmcNotify(_('TvShows scanner done'))
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

      # perform a search by title
      self._current_serie_name = serie_name
      if self._tvdb is None:
         self._tvdb = TMDBv3(lang=ini.get('tvshows', 'info_lang'))
      self._tvdb.tv_search(serie_name, self._search_done_cb)
      return ecore.ECORE_CALLBACK_RENEW

   def _search_done_cb(self, tvdb, results):
      if len(results) > 0:
         tvdb.get_tv_info(results[0]['tmdb_id'], self._fetch_data_done_cb)
      else:
         self._fetch_data_done_cb(tvdb, None)

   def _fetch_data_done_cb(self, tvdb, result):
      # store result info into the idler-db
      self._idler_db.set_data(self._current_serie_name, {
         'last_search_time': time.time(),
         'last_search_success': True if result else False
      })

      if result:
         # store the data into tvshow-db
         self._tvshows_db.set_data(self._current_serie_name, result)

         # show a nice notification
         text = _('<title>Found serie:</><br>%s<br>%s seasons') % \
                  (result['name'], len(result['seasons']))
         EmcNotify(text, icon=get_tv_icon_filename(result['id']))

         # refresh the browser view
         self._browser.refresh()

      # clear the "semaphore", now another serie can be processed
      self._current_serie_name = None
      self._current_serie_data = None


""" idler_db Reference
{
   MacGyver: {
      last_search_time: local-timestamp
      last_search_success: bool
   }
   ...
}
"""

""" tvshows_db Reference

{
   MacGyver: {
      id: 2875
      name: 'MacGyver'
      created_by: ['Lee David Zlotoff']
      country: ['US', 'CA']
      episode_run_time: '45, 60, 48'
      first_air_date: '1985-09-29'
      last_air_date: '1992-05-21'
      genres: ['Action & Adventure']
      networks: ['American Broadcasting Company']
      number_of_episodes: 139
      number_of_seasons: 7
      overview: 'blah, blah, blah, ...'
      seasons: {
         1: {
            id: 9278
            season_num: 1
            first_air_date: '1994-05-14'
            overview: 'blah, blah, blah, ...'
            episodes: {
               1: {
                  id: 220169
                  episode_num: 1
                  season_num: 1
                  series_id: 2875
                  director: ['name', ... ]
                  writer: ['name', ... ]
                  first_aired: '1994-05-14'
                  title: 'Lost Treasure of Atlantis'
                  overview: 'blah, blah, blah, ...'
                  thumb_url: 'http://.../1AtgwHTkFWh0VvMM7WyAelbC8NN.jpg'
               }
               2: { ... }
               ...
            }
         }
         2: { ... }
         ...
      }
   }
   ...
}

"""

