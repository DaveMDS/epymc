#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2018 Davide Andreoli <dave@gurumeditation.it>
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

from __future__ import absolute_import, print_function

import os, re, time
from operator import itemgetter

from efl import ecore, evas, elementary, emotion
from efl.elementary.image import Image
from efl.elementary.entry import utf8_to_markup

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass, FolderItemClass
from epymc.sdb import EmcDatabase
from epymc.gui import EmcDialog, EmcImage, EmcSourcesManager, \
    EmcVKeyboard, EmcNotify, EmcTagsManager, EmcMenu
from epymc.themoviedb import TMDBv3, CastPanel, get_poster_filename, \
    get_backdrop_filename, get_icon_filename

import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.ini as ini
import epymc.utils as utils
import epymc.gui as gui
import epymc.events as events
import epymc.config_gui as config_gui


# debuggin stuff
def DBG(msg):
    # print('MOVIES: %s' % msg)
    pass


MOVIE_DB_VERSION = 1
MOVIE_TAGS_DB_VERSION = 1
MOVIE_FAV_PEOPLE_DB_VERSION = 1
DEFAULT_INFO_LANG = 'en'
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

    @staticmethod
    def _manager_cb(sources):
        _mod._folders = sources
        _mod._browser.refresh(hard=True)

    def label_get(self, url, mod):
        return _('Manage sources')

    def icon_get(self, url, mod):
        return 'icon/plus'


class RescanItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        if not mod._scanner:
            mod._scanner = BackgroundScanner(mod._browser, mod._movie_db, mod._idler_db)

    def label_get(self, url, mod):
        return _('Rescan library')

    def icon_get(self, url, mod):
        return 'icon/refresh'


class SpecialItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        if url == 'movies://actors':
            mod._browser.page_add(url, _('Actors'), mod._styles_for_folders,
                                  mod.populate_actors_list)
        elif url == 'movies://directors':
            mod._browser.page_add(url, _('Directors'), mod._styles_for_folders,
                                  mod.populate_directors_list)
        elif url.startswith('movies://actors/'):
            name = url.replace('movies://actors/', '')
            CastPanel(name=name, lang=ini.get('movies', 'info_lang'))
        elif url.startswith('movies://directors/'):
            name = url.replace('movies://directors/', '')
            CastPanel(name=name, lang=ini.get('movies', 'info_lang'))
        elif url == 'movies://tags_manager':
            EmcTagsManager(mod._tags_db,
                           done_cb=lambda: _mod._browser.refresh(hard=True))

    def label_get(self, url, mod):
        if url == 'movies://actors':
            return _('Actors')
        elif url == 'movies://directors':
            return _('Directors')
        elif url.startswith('movies://actors/'):
            return _('Actor info')
        elif url.startswith('movies://directors/'):
            return _('Director info')
        elif url == 'movies://tags_manager':
            return _('Tags manager')

    def label_end_get(self, url, mod):
        if url == 'movies://actors':
            count = len(_mod._fav_actors_db)
        elif url == 'movies://directors':
            count = len(_mod._fav_directors_db)
        else:
            return None
        return ngettext('{} favorite', '{} favorites', count).format(count)

    def icon_get(self, url, mod):
        if url == 'movies://actors':
            return 'icon/head'
        elif url == 'movies://directors':
            return 'icon/head'
        elif url.startswith(('movies://directors/', 'movies://actors/')):
            return 'icon/info'
        elif url == 'movies://tags_manager':
            return 'icon/tag'


class ActorItemClass(EmcItemClass):
    def item_selected(self, url, name):
        _mod._browser.page_add(url, name, _mod._styles_for_folders,
                               _mod.populate_actor_movies)

    def label_get(self, url, name):
        return name

    def label_end_get(self, url, name):
        return str(len(_mod._actors_cache[name]))

    def icon_get(self, url, name):
        if name in _mod._fav_actors_db:
            return 'icon/star'
        else:
            return 'icon/head'


class DirectorItemClass(EmcItemClass):
    def item_selected(self, url, name):
        _mod._browser.page_add(url, name, _mod._styles_for_folders,
                               _mod.populate_director_movies)

    def label_get(self, url, name):
        return name

    def label_end_get(self, url, name):
        return str(len(_mod._directors_cache[name]))

    def icon_get(self, url, name):
        if name in _mod._fav_directors_db:
            return 'icon/star'
        else:
            return 'icon/head'


class MovieItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        mod.show_movie_info(url)

    def label_get(self, url, mod):
        try:
            assert ini.get('movies', 'db_names_in_list') == 'True'
            return utf8_to_markup(mod._movie_db.get_data(url)['title'])
        except:
            return utf8_to_markup(os.path.basename(url))

    def icon_end_get(self, url, mod):
        counts = mediaplayer.play_counts_get(url)
        if counts['finished'] > 0:
            return 'icon/check_on'
        if counts['stop_at'] > 0:
            return 'icon/check_off'

    def icon_get(self, url, mod):
        if mod._movie_db.id_exists(url):
            e = mod._movie_db.get_data(url)
            icon = get_icon_filename(e['id'])
            if os.path.exists(icon):
                return icon

    def poster_get(self, url, mod):
        if mod._movie_db.id_exists(url):
            e = mod._movie_db.get_data(url)
            poster = get_poster_filename(e['id'])
            if os.path.exists(poster):
                return poster
            else:
                return 'special/bd/' + utf8_to_markup(e['title'])
        else:
            return 'special/bd/' + utf8_to_markup(os.path.basename(url))

    def cover_get(self, url, mod):
        return 'special/vthumb/' + url

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
                   '<name>%s:</> %s/10<br>' \
                   '<name>%s:</> %s<br>' \
                   '<name>%s:</> %s<br>' % (
                       utf8_to_markup(e['title']), e['country'], e['release_date'][:4],
                       _('Rating'), e['rating'],
                       _('Director'), e['director'],
                       _('Cast'), mod._get_cast(e, 4))
        else:
            name, year = get_movie_name_from_url(url)
            text = '<title>%s</><br><name>%s:</> %s<br>' \
                   '<name>%s:</> %s<br><name>%s:</> %s<br>' % (
                       utf8_to_markup(os.path.basename(url)),
                       _('File size'),
                       utils.hum_size(os.path.getsize(utils.url2path(url))),
                       _('Title'), utf8_to_markup(name),
                       _('Year'), year or _('Unknown'))
        return text


class MyFolderItemClass(FolderItemClass):
    def item_selected(self, url, mod):
        mod._browser.page_add(url, os.path.basename(url),
                              mod._styles_for_folders, mod.populate_url)


class TagItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        tag_name = url.split('/')[-1]
        _mod._browser.page_add(url, tag_name, _mod._styles_for_folders,
                               _mod.populate_tag)

    def label_get(self, url, mod):
        return url.split('/')[-1]

    def label_end_get(self, url, mod):
        tag_name = url.split('/')[-1]
        count = len(mod._tags_db.get_data(tag_name))
        return ngettext('{} movie', '{} movies', count).format(count)

    def icon_get(self, url, mod):
        return 'icon/tag'


class SetFavoriteDirectorItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        if url in mod._fav_directors_db:
            mod._fav_directors_db.del_data(url)
        else:
            mod._fav_directors_db.set_data(url, None)
        mod._browser.refresh()

    def label_get(self, url, mod):
        if url in mod._fav_directors_db:
            return _('Remove from favorites')
        else:
            return _('Add to favorites')

    def icon_get(self, url, mod):
        if url in mod._fav_directors_db:
            return 'icon/star'
        else:
            return 'icon/star_off'


class SetFavoriteActorItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        if url in mod._fav_actors_db:
            mod._fav_actors_db.del_data(url)
        else:
            mod._fav_actors_db.set_data(url, None)
        mod._browser.refresh()

    def label_get(self, url, mod):
        if url in mod._fav_actors_db:
            return _('Remove from favorites')
        else:
            return _('Add to favorites')

    def icon_get(self, url, mod):
        if url in mod._fav_actors_db:
            return 'icon/star'
        else:
            return 'icon/star_off'


class MoviesModule(EmcModule):
    name = 'movies'
    label = _('Movies')
    icon = 'icon/movie'
    info = _('The movies module is used to browse your films collection, '
             'it is fully integrated with themoviedb.org online database.')

    _browser = None  # the browser widget instance
    _movie_db = None  # key: movie_url  data: dictionary as of the tmdb api
    _idler_db = None  # key: file_url  data: timestamp of the last unsuccessfull tmdb query
    _tags_db = None  # key: tag_name  data: list of tmdb movie IDs
    _fav_actors_db = None  # key: actor_name  data: None
    _fav_directors_db = None  # key: director_name  data: None
    _scanner = None  # BackgroundScanner instance
    _actors_cache = None  # key: actor name     val: [list of films urls]
    _directors_cache = None  # key: director name  val: [list of films urls]
    _styles_for_folders = ('List', 'PosterGrid')

    def __init__(self):
        global _mod

        DBG('Init module')
        _mod = self

        # create config ini section if not exists, with defaults
        ini.add_section('movies')
        if not ini.has_option('movies', 'enable_scanner'):
            ini.set('movies', 'enable_scanner', 'False')
        if not ini.has_option('movies', 'scanner_clean_dead_files'):
            ini.set('movies', 'scanner_clean_dead_files', '0')
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

        # get movies folders from config
        self._folders = ini.get_string_list('movies', 'folders', ';')

        # add an item in the mainmenu
        subitems = []
        for f in self._folders:
            subitems.append((os.path.basename(f), None, f))
        mainmenu.item_add('movies', 10, _('Movies'), 'icon/movie',
                          self.cb_mainmenu, subitems)

        # add an entry in the config gui
        config_gui.root_item_add('movies', 10, _('Movie Collection'),
                                 icon='icon/movie', callback=config_panel_cb)

        # create a browser instance
        self._browser = EmcBrowser(_('Movies'), 'List', 'icon/movie')

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
        if self._movie_db is not None:
            del self._movie_db
        if self._idler_db is not None:
            del self._idler_db

    def play_movie(self, url):
        mediaplayer.play_url(url)
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

    # ##### BROWSER STUFF
    def cb_mainmenu(self, url=None):

        # if not self._folders:
        # TODO alert the user. and instruct how to add folders

        # open movie/idler/tags databases (they are created if not exists)
        if self._movie_db is None:
            self._movie_db = EmcDatabase('movies', MOVIE_DB_VERSION)
            self._idler_db = EmcDatabase('movieidlercache', MOVIE_DB_VERSION)
            self._tags_db = EmcDatabase('movietags', MOVIE_TAGS_DB_VERSION)
            self._fav_actors_db = EmcDatabase('moviefavactors', MOVIE_FAV_PEOPLE_DB_VERSION)
            self._fav_directors_db = EmcDatabase('moviefavdirectors', MOVIE_FAV_PEOPLE_DB_VERSION)

        # restore a previous browser state (if available)
        if self._browser.freezed and not url:
            self._browser.unfreeze()
            return

        # destory the browser state (if an url is requested)
        if self._browser.freezed and url:
            self._browser.clear()

        # start the browser in the wanted page
        if url is None:
            self._browser.clear()
            self._browser.page_add('movies://root', _('Movies'),
                                   self._styles_for_folders,
                                   self.populate_root_page)
        else:
            self._browser.page_add(url, os.path.basename(url),
                                   self._styles_for_folders,
                                   self.populate_url)

        self._browser.show()
        mainmenu.hide()

        # on idle scan all files (one shot every time the activity start)
        if not self._scanner and ini.get_bool('movies', 'enable_scanner'):
            self._scanner = BackgroundScanner(self._browser, self._movie_db, self._idler_db)

    def populate_root_page(self, browser, page_url):
        for f in self._folders:
            self._browser.item_add(MyFolderItemClass(), f, self)

        self._browser.item_add(SpecialItemClass(), 'movies://directors', self)
        self._browser.item_add(SpecialItemClass(), 'movies://actors', self)

        for tag in sorted(self._tags_db.keys()):
            self._browser.item_add(TagItemClass(), 'movies://tag/%s' % tag, self)
        self._browser.item_add(SpecialItemClass(), 'movies://tags_manager', self)

        self._browser.item_add(RescanItemClass(), 'movies://rescan_library', self)
        self._browser.item_add(AddSourceItemClass(), 'movies://add_source', self)

    def populate_url(self, browser, url):
        dirs, files = [], []
        for fname in os.listdir(url[7:]):
            if fname[0] != '.':
                if os.path.isdir(os.path.join(url[7:], fname)):
                    dirs.append(fname)
                else:
                    name, ext = os.path.splitext(fname)
                    if ext.lower() in mediaplayer.video_extensions:
                        files.append(fname)

        for fname in utils.natural_sort(dirs):
            self._browser.item_add(MyFolderItemClass(), os.path.join(url, fname), self)
        for fname in utils.natural_sort(files):
            self._browser.item_add(MovieItemClass(), os.path.join(url, fname), self)

    def populate_actors_list(self, browser, url):
        # first show the favorites
        for name in sorted(self._fav_actors_db.keys()):
            self._browser.item_add(ActorItemClass(), 'movies://actors/' + name, name)

        # then all the actors NOT in favorites
        actors = {}  # key:actor_name  val:[list of movie urls]
        for url, movie in self._movie_db:
            for actor in movie['cast']:
                name = actor['name']
                if name in actors:
                    actors[name].append(url)
                else:
                    actors[name] = [url]
        self._actors_cache = actors

        for name in sorted(self._actors_cache.keys()):
            if name not in self._fav_actors_db:
                self._browser.item_add(ActorItemClass(), 'movies://actors/' + name, name)

    def populate_actor_movies(self, browser, url):
        name = url.replace('movies://actors/', '')
        # actor info item
        self._browser.item_add(SpecialItemClass(), url, self)
        # favorite/unfavorite item
        self._browser.item_add(SetFavoriteActorItemClass(), name, self)
        # all movies for this actor
        for url in self._actors_cache[name]:
            self._browser.item_add(MovieItemClass(), url, self)

    def populate_directors_list(self, browser, url):
        # first show the favorites
        for name in sorted(self._fav_directors_db.keys()):
            self._browser.item_add(DirectorItemClass(),
                                   'movies://directors/' + name, name)
        # then all the directors NOT in favorites
        directors = {}  # key:director_name  val:[list of movie urls]
        for url, movie in self._movie_db:
            name = movie['director']
            if name in directors:
                directors[name].append(url)
            else:
                directors[name] = [url]
        self._directors_cache = directors

        for name in sorted(self._directors_cache.keys()):
            if name not in self._fav_directors_db:
                self._browser.item_add(DirectorItemClass(),
                                       'movies://directors/' + name, name)

    def populate_director_movies(self, browser, url):
        name = url.replace('movies://directors/', '')
        # director info item
        self._browser.item_add(SpecialItemClass(), url, self)
        # favorite/unfavorite item
        self._browser.item_add(SetFavoriteDirectorItemClass(), name, self)
        # all movies for this director
        for movie_url in self._directors_cache[name]:
            self._browser.item_add(MovieItemClass(), movie_url, self)

    def populate_tag(self, browser, url):
        tag_name = url.split('/')[-1]
        tag_ids = self._tags_db.get_data(tag_name)
        for movie_url, movie in self._movie_db:
            if movie['id'] in tag_ids:
                self._browser.item_add(MovieItemClass(), movie_url, self)

    @staticmethod
    def _get_cast(e, max_num=999):
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

    # ##### INFO PANEL STUFF
    def show_movie_info(self, url):
        image = Image(gui.win)
        dialog = EmcDialog(style='panel', text=' ', content=image)

        self._dialog = dialog
        self._current_url = url
        self.update_movie_info(url)

    def hide_movie_info(self):
        self._dialog.delete()
        del self._dialog

    def update_movie_info(self, url):
        # update buttons
        self._dialog.buttons_clear()
        self._dialog.button_add(_('Play'), self._cb_panel_1)
        if self._movie_db.id_exists(url):
            self._dialog.button_add(_('Cast'), self._cb_panel_2)
            self._dialog.button_add(_('Posters'), self._cb_panel_3)
            self._dialog.button_add(_('Backdrops'), self._cb_panel_4)
            self._dialog.button_add(_('Tags'), self._cb_panel_6)
        self._dialog.button_add(_('Search Info'), self._cb_panel_5)

        o_image = self._dialog.content_get()

        if self._movie_db.id_exists(url):
            e = self._movie_db.get_data(url)

            # update text info
            self._dialog.title_set(e['title'].replace('&', '&amp;'))
            info = '<name>%s:</> %s<br>' \
                   '<name>%s:</> %s<br>' \
                   '<name>%s: </name> %s<br>' \
                   '<name>%s:</> %s<br>' \
                   '<name>%s:</> %s/10<br>' \
                   '<br><name>%s:</><br>%s' % (
                       _('Director'), e['director'],
                       _('Cast'), self._get_cast(e),
                       _('Released'), e['release_date'],
                       _('Country'), e['countries'],
                       _('Rating'), e['rating'],
                       _('Overview'), e['overview'])
            self._dialog.text_set(info.replace('&', '&amp;'))

            # update poster
            poster = get_poster_filename(e['id'])
            if os.path.exists(poster):
                o_image.file_set(poster)
            else:
                # TODO show a dummy image
                o_image.file_set('')

            # remember the movie ID
            self._movie_id = e['id']

        else:
            name, year = get_movie_name_from_url(url)
            self._dialog.title_set(name)
            # TODO print also file size, video len, codecs, streams found, file metadata, etc..
            msg = _('Media:<br>%s<br><br>' \
                    'No info stored for this media<br>' \
                    'Try the Search info button...') % url
            self._dialog.text_set(msg)
            # TODO make thumbnail
            # o_image.file_set('')

    # ####### Play
    def _cb_panel_1(self, button):
        self.play_movie(self._current_url)
        self.hide_movie_info()

    # ####### Cast
    def _cb_panel_2(self, button):
        if self._movie_db.id_exists(self._current_url):
            movie_info = self._movie_db.get_data(self._current_url)
            dia = EmcDialog(title=_('Cast'), style='list',
                            done_cb=self._cast_info_done_cb)

            for person in sorted(movie_info['cast'], key=itemgetter('order')):
                label = '<big>{}</big> <i>{} <big>{}</big></i>'.format(
                    person['name'], _('as'), person['character'])
                icon = EmcImage(person['profile_path'])
                icon.size_hint_min_set(100, 100)  # TODO FIXME
                dia.list_item_append(label, icon, None, person['id'])
            dia.list_go()

    @staticmethod
    def _cast_info_done_cb(list_dia, pid):
        CastPanel(pid, lang=ini.get('movies', 'info_lang'))

    # ####### Choose poster
    def _cb_panel_3(self, button):
        if self._movie_db.id_exists(self._current_url):
            movie_info = self._movie_db.get_data(self._current_url)
            tmdb = TMDBv3(lang=ini.get('movies', 'info_lang'))
            tmdb.get_posters(movie_info['tmdb_id'], self._cb_posters_list_complete)

    def _cb_posters_list_complete(self, tmdb, posters):
        title = _('%d posters available') % (len(posters))
        dialog = EmcDialog(style='image_list_horiz', title=title,
                           done_cb=self._cb_posters_list_ok)
        for poster in posters:
            icon = EmcImage(poster['thumb_url'])
            dialog.list_item_append(None, icon, poster=poster)
        dialog.list_go()

    def _cb_posters_list_ok(self, dialog, poster):
        dest = get_poster_filename(poster['movie_id'])
        utils.download_url_async(poster['url'], dest,
                                 complete_cb=self._cb_image_done,
                                 progress_cb=self._cb_image_progress)

        # kill the list dialog
        dialog.delete()
        del dialog

        # show a progress dialog
        self._poster_dialog = EmcDialog(title=_('Downloading image'),
                                        style='progress',
                                        content=gui.load_image('tmdb_logo.png'))

    def _cb_image_progress(self, dest, tot, done):
        if tot > 0: self._poster_dialog.progress_set(float(done) / float(tot))

    def _cb_image_done(self, dest, status):
        # kill the dialog
        self._poster_dialog.delete()
        del self._poster_dialog
        # update browser and info panel
        self.update_movie_info(self._current_url)
        self._browser.refresh()

    # ####### Choose fanart
    def _cb_panel_4(self, button):
        if self._movie_db.id_exists(self._current_url):
            movie_info = self._movie_db.get_data(self._current_url)
            tmdb = TMDBv3()
            tmdb.get_backdrops(movie_info['tmdb_id'], self._cb_backdrops_list_complete)

    def _cb_backdrops_list_complete(self, tmdb, backdrops):

        title = _('%d backdrops available') % (len(backdrops))
        dialog = EmcDialog(style='image_list_vert', title=title,
                           done_cb=self._cb_backdrops_list_ok)
        for backdrop in backdrops:
            img = EmcImage(backdrop['thumb_url'])
            dialog.list_item_append(None, img, backdrop=backdrop)
        dialog.list_go()

    def _cb_backdrops_list_ok(self, dialog, backdrop):
        # download the selected backdrop
        dest = get_backdrop_filename(backdrop['movie_id'])
        utils.download_url_async(backdrop['url'], dest,
                                 complete_cb=self._cb_image_done,
                                 progress_cb=self._cb_image_progress)

        # kill the list dialog
        dialog.delete()
        del dialog

        # show a progress dialog
        self._poster_dialog = EmcDialog(title=_('Downloading image'),
                                        style='progress',
                                        content=gui.load_image('tmdb_logo.png'))

    # ####### Get movie info from themoviedb.org
    def _cb_panel_5(self, button):
        name, year = get_movie_name_from_url(self._current_url)
        self._do_movie_search(name, year)

    def _do_movie_search(self, name, year):
        tmdb = TMDBv3(lang=ini.get('movies', 'info_lang'))
        tmdb.movie_search(name, year, self._cb_search_done)
        search = _('Searching for')
        if year:
            text = '<b>%s:</b><br>%s (%s)<br>' % (search, name, year)
        else:
            text = '<b>%s:</b><br>%s<br>' % (search, name)

        self.tmdb_dialog = EmcDialog(title='themoviedb.org',
                                     style='progress', text=text,
                                     user_data=tmdb)
        self.tmdb_dialog.button_add(_('Change name'),
                                    lambda b: EmcVKeyboard(text=name, accept_cb=self._vkbd_cb))

    def _vkbd_cb(self, vkbd, txt):
        if self.tmdb_dialog: self.tmdb_dialog.delete()
        self._do_movie_search(txt, None)

    def _cb_search_done(self, tmdb, results):
        if len(results) == 0:
            self.tmdb_dialog.text_append(
                '<br>' + _('nothing found, please try with a better name'))  # TODO explain better the format
        elif len(results) == 1:
            tmdb.get_movie_info(results[0]['tmdb_id'],
                                self._cb_info_done, self._cb_info_progress)
            self.tmdb_dialog.text_append('<b>%s</b>' % _('Downloading movie info...'))
        else:
            self.tmdb_dialog.text_append(_('<b>Found %d results</b><br>') % (len(results)))
            title = _('Found %d results, which one?') % (len(results))
            dialog2 = EmcDialog(title=title, style='list',
                                done_cb=self._cb_list_ok,
                                canc_cb=self._cb_list_cancel)
            for res in results:
                icon = EmcImage(res['poster_url'])
                icon.size_hint_min_set(100, 100)  # TODO fixme
                label = '%s (%s)' % (res['title'], res['year'])
                dialog2.list_item_append(label, icon, None, res['tmdb_id'])
            dialog2.list_go()

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
        self.tmdb_dialog.text_append('<b>%s</b>' % _('Downloading movie info...'))

    def _cb_info_progress(self, tmdb, progress):
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

    # ####### Tags
    def _cb_panel_6(self, button):
        m = EmcMenu(relto=button, dismiss_on_select=False)
        if self._tags_db:
            for tag in sorted(self._tags_db.keys()):
                if self._movie_id in self._tags_db.get_data(tag):
                    end = 'icon/check_on'
                else:
                    end = 'icon/check_off'
                m.item_add(tag, 'icon/tag', end, callback=self._tag_menu_cb)
        else:
            m.item_add(_('No tags present')).disabled = True
        m.item_add(_('Tags manager'), end='icon/tag',
                   callback=self._tag_menu_manager_cb)
        m.show()

    def _tag_menu_cb(self, menu, item):
        tag_name = item.text
        tag_ids = self._tags_db.get_data(tag_name)
        if self._movie_id in tag_ids:
            tag_ids.remove(self._movie_id)
            menu.item_icon_end_set(item, 'icon/check_off')
        else:
            tag_ids.append(self._movie_id)
            menu.item_icon_end_set(item, 'icon/check_on')
        self._tags_db.set_data(tag_name, tag_ids)

    def _tag_menu_manager_cb(self, menu, item):
        menu.close()
        EmcTagsManager(self._tags_db)


class BackgroundScanner(ecore.Idler):
    def __init__(self, browser, movie_db, idler_db):
        self._browser = browser
        self._movie_db = movie_db
        self._idler_db = idler_db
        self._current_url = None  # also used as a semaphore in step1
        self._generator = None
        self._tmdb = None  # TMDBv3 instance
        self._retry_after = ini.get_int('movies', 'tmdb_retry_days')
        self._retry_after *= 24 * 60 * 60
        self._added_count = 0
        self._current_step = self._step1
        self._dead_files = []

        ecore.Idler.__init__(self, self._idle_cb)

    def abort(self):
        self.delete()
        if self._tmdb:
            self._tmdb.abort()
            del self._tmdb
            self._tmdb = None
        del self

    def _idle_cb(self):
        # DBG('Mainloop idle')
        return self._current_step()

    def _step1(self):
        """ STEP 1: normal filesystem scan """
        if self._current_url is not None:
            # DBG('im busy')
            return ecore.ECORE_CALLBACK_RENEW

        # the first time build the generator object
        if self._generator is None:
            folders = ini.get_string_list('movies', 'folders', ';')
            self._generator = utils.grab_files(folders)
            txt = '<br><title>{}</>'.format(_('Movies scanner started'))
            EmcNotify(txt, 'icon/movie')

        # get the next file from the files generator
        try:
            filename = next(self._generator)
        except StopIteration:
            DBG("Starting step 2")
            self._generator = None
            self._current_step = self._step2
            return ecore.ECORE_CALLBACK_RENEW

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
            self._tmdb = TMDBv3(lang=ini.get('movies', 'info_lang'))
            name, year = get_movie_name_from_url(url)
            self._tmdb.movie_search(name, year, self._step1_search_cb)
            self._current_url = url

        return ecore.ECORE_CALLBACK_RENEW

    def _step1_search_cb(self, tmdb_obj, results):
        if len(results) > 0:
            self._tmdb.get_movie_info(results[0]['tmdb_id'], self._step1_tmdb_cb)
        else:
            # store the current time in the cache db
            self._idler_db.set_data(self._current_url, time.time())
            # clear the 'semaphore', now another file can be processed
            del self._tmdb
            self._tmdb = None
            self._current_url = None

    def _step1_tmdb_cb(self, tmdb, movie_info):
        if movie_info is None:
            # store the current time in the cache db
            self._idler_db.set_data(self._idler_url, time.time())
        else:
            # store the result in movie db
            self._added_count += 1
            self._movie_db.set_data(self._current_url, movie_info)
            found = _('Found movie')
            try:
                text = '<title>%s</><br>%s (%s)' % \
                       (found, movie_info['title'], movie_info['release_date'][:4])
                EmcNotify(text, icon=get_poster_filename(movie_info['id']))
            except:
                pass

        # clear the 'semaphore', now another file can be processed
        self._current_url = None

        # update the browser view
        self._browser.refresh()

        # delete TMDBv3 object
        del self._tmdb
        self._tmdb = None

    def _step2(self):
        """ STEP 2: scan all the db items to find dead files """
        # the first time build the generator object
        if self._generator is None:
            self._generator = self._movie_db.items()

        # get the next db item from the generator
        try:
            url, movie_data = next(self._generator)
        except StopIteration:
            DBG("Movies scanner done (step 2)")
            self._generator = None

            count = len(self._dead_files)
            txt = '<title>{}</><br>{}: {}<br>{}: {}'.format(
                _('Movies scanner done'),
                _('New movies'), self._added_count,
                _('Dead files'), count)
            EmcNotify(txt, 'icon/movie')

            if count == 0:
                return ecore.ECORE_CALLBACK_CANCEL

            clean = ini.get_int('movies', 'scanner_clean_dead_files')
            if clean == 2:  # never
                return ecore.ECORE_CALLBACK_CANCEL

            elif clean == 1:  # always
                self._step2_clean_cb()

            elif clean == 0:  # ask
                txt = _('Found {} movies in the database that point to not ' \
                        'existent files.<br>' \
                        'Should I remove those movies?'.format(count))
                EmcDialog(style='yesno', title=_('Clean dead files'), text=txt,
                          done_cb=self._step2_clean_cb)

            return ecore.ECORE_CALLBACK_CANCEL

        # check if the file still exists
        if not os.path.exists(utils.url2path(url)):
            self._dead_files.append(url)

        return ecore.ECORE_CALLBACK_RENEW

    def _step2_clean_cb(self, dia=None):
        for url in self._dead_files:
            self._movie_db.del_data(url)
        if dia is not None:
            dia.delete()


# ##### UTILS
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
    m = p.match(movie.strip())
    if m:
        name = m.group('name')
        year = m.group('year')
    else:
        name = movie
        year = None

    return name.strip(), year


# ##### Config Panel stuff ######
def config_panel_cb():
    bro = config_gui.browser_get()
    bro.page_add('config://movies/', _('Movies Collection'), None, populate_config)


def populate_config(browser, url):
    config_gui.standard_item_lang_add('movies', 'info_lang',
                                      _('Preferred language for contents'))

    config_gui.standard_item_bool_add('movies', 'db_names_in_list',
                                      _('Prefer movie titles in lists'))

    config_gui.standard_item_bool_add('movies', 'enable_scanner',
                                      _('Enable background scanner'))

    vals = (_('Ask'), _('Always'), _('Never'))
    config_gui.standard_item_int_meaning_add('movies', 'scanner_clean_dead_files',
                                             _('Background scan also clean dead files'),
                                             values=vals)
