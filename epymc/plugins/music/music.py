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

import os
import operator
import mutagen

from efl import ecore
from efl.elementary.entry import utf8_to_markup

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.sdb import EmcDatabase
from epymc.gui import EmcDialog, EmcNotify, EmcSourcesManager
import epymc.mainmenu as mainmenu
import epymc.utils as utils
import epymc.events as events
import epymc.ini as ini
import epymc.gui as gui
import epymc.mediaplayer as mediaplayer


def DBG(msg):
    # print('MUSIC: %s' % msg)
    pass


_mod = None


class RootOnAirItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        mediaplayer.audio_player_show()

    def label_get(self, url, mod):
        return _('OnAir')

    def label_end_get(self, url, mod):
        return str(len(mediaplayer.playlist))

    def icon_get(self, url, mod):
        return 'icon/play'


class RootArtistsItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        mod._browser.page_add('music://artists', _('Artists'), mod._styles,
                              mod.populate_artists_page)

    def label_get(self, url, mod):
        return _('Artists')

    def label_end_get(self, url, mod):
        return str(len(mod._artists_db))

    def icon_get(self, url, mod):
        return 'icon/artist'


class RootAlbumsItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        mod._browser.page_add('music://albums', _('Albums'), mod._styles2,
                              mod.populate_albums_page)

    def label_get(self, url, mod):
        return _('Albums')

    def label_end_get(self, url, mod):
        return str(len(mod._albums_db))

    def icon_get(self, url, mod):
        return 'icon/album'


class RootSongsItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        mod._browser.page_add('music://songs', _('Songs'), mod._styles,
                              mod.populate_songs_page)

    def label_get(self, url, mod):
        return _('Songs')

    def label_end_get(self, url, mod):
        return str(len(mod._songs_db))

    def icon_get(self, url, mod):
        return 'icon/song'


class RootRebuildItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        mod.rebuild_db()

    def label_get(self, url, mod):
        return _('Rescan library')

    def icon_get(self, url, mod):
        return 'icon/refresh'


class RootAddSourceItemClass(EmcItemClass):
    def item_selected(self, url, mod):
        EmcSourcesManager('music', done_cb=self._manager_cb)

    @staticmethod
    def _manager_cb(sources):
        _mod._folders = sources

    def label_get(self, url, mod):
        return _('Manage sources')

    def icon_get(self, url, mod):
        return 'icon/plus'


class PlaySongsItemClass(EmcItemClass):
    def item_selected(self, url, songs_list):
        _mod.queue_song_list(songs_list, queue=False)

    def label_get(self, url, songs_list):
        return _('Play all the songs')

    def icon_get(self, url, songs_list):
        return 'icon/play'


class QueueSongsItemClass(EmcItemClass):
    def item_selected(self, url, songs_list):
        _mod.queue_song_list(songs_list, queue=True)

    def label_get(self, url, songs_list):
        return _('Queue all the songs')

    def icon_get(self, url, songs_list):
        return 'icon/plus'


class SongItemClass(EmcItemClass):
    def item_selected(self, url, song):
        _mod.queue_url(url, song)

    def label_get(self, url, song):
        title = utf8_to_markup(song['title'])
        try:
            return "%02d. %s" % (song['tracknumber'], title)
        except:
            return title

    def cover_get(self, url, song):
        return _mod.search_poster_for_song(url, song)

    def info_get(self, url, song):
        text = '<title>{}</>'.format(utf8_to_markup(song['title']))
        if 'length' in song:
            length = utils.seconds_to_duration(int(song['length']) / 1000)
            text += ' <small>({})</small><br>'.format(length)
        else:
            text += '<br>'
        if 'artist' in song:
            text += '<artist>{0} {1}</artist><br>'.format(_('by'),
                                                          utf8_to_markup(song['artist']))
        if 'album' in song:
            text += '<album>{0} {1}</album><br>'.format(_('from'),
                                                        utf8_to_markup(song['album']))

        return text


class SongWithArtistItemClass(SongItemClass):
    def label_get(self, url, song):
        title = utf8_to_markup(song['title'])
        artist = utf8_to_markup(song['artist'])
        return '<song>{0}</song> <artist>{1} {2}</artist>'.format(
            title, _('by'), artist)


class AlbumItemClass(EmcItemClass):
    def item_selected(self, url, album):
        _mod._browser.page_add('music://album/' + album['name'], album['name'],
                               _mod._styles, _mod.populate_album_page, album)

    def label_get(self, url, album):
        # return utf8_to_markup(_('%(name)s by %(artist)s') % (album))
        return utf8_to_markup(album['name'])

    def icon_get(self, url, album):
        return _mod.search_poster_for_album(album)

    def cover_get(self, url, album):
        return _mod.search_poster_for_album(album) or 'special/cd/' + album['name']

    def info_get(self, url, album):
        text = '<title>%s</title><br>' % utf8_to_markup(album['name'])
        text += _('<em>by</em> %s<br>') % utf8_to_markup(album['artist'])
        n = len(album['songs'])
        text += ngettext('%d song', '%d songs', n) % n

        lenght = 0
        for song in album['songs']:
            song_data = _mod._songs_db.get_data(song)
            if 'length' in song_data:
                lenght += int(song_data['length'])
        if lenght > 0:
            n = lenght / 60000
            runtime = ngettext('%d minute', '%d minutes', n) % n
            text += ', ' + runtime
        return text


class ArtistItemClass(EmcItemClass):
    def item_selected(self, url, artist):
        _mod._browser.page_add('music://artist/' + artist['name'], artist['name'],
                               _mod._styles, _mod.populate_artist_page, artist)

    def label_get(self, url, artist):
        return utf8_to_markup(artist['name'])

    def cover_get(self, url, artist):
        return _mod.search_poster_for_artist(artist)

    def info_get(self, url, artist):
        n = len(artist['albums'])
        albums = ngettext('%d album', '%d albums', n) % n
        n = len(artist['songs'])
        songs = ngettext('%d song', '%d songs', n) % n
        name = utf8_to_markup(artist['name'])
        return '<title>%s</><br>%s, %s' % (name, albums, songs)

    def icon_get(self, url, mod):
        return 'icon/artist'


class MusicModule(EmcModule):
    name = 'music'
    label = _('Music')
    icon = 'icon/music'
    info = _('The music module build a database of all your albums, songs and artist.')

    _browser = None  # browser instance
    _rebuild_notify = None  # rebuild notification object

    _songs_db = None  # key=url           data=dict
    _albums_db = None  # key=album_name    data=dict
    _artists_db = None  # key=artist_name   data=dict
    _styles = ('List', 'CoverGrid')
    _styles2 = ('CoverGrid', 'List')

    def __init__(self):
        global _mod

        DBG('Init module')
        _mod = self

        # create config ini section if not exists
        ini.add_section('music')

        # make default of covers_dir if necessary
        if not ini.has_option('music', 'covers_dir'):
            path = os.path.join(utils.user_conf_dir, 'music_covers')
            ini.set('music', 'covers_dir', path)

        if not os.path.exists(ini.get('music', 'covers_dir')):
            os.mkdir(ini.get('music', 'covers_dir'))

        # add an item in the mainmenu
        subitems = [
            (_('Artists'), None, 'music://artists'),
            (_('Albums'), None, 'music://albums'),
            (_('Songs'), None, 'music://songs'),
        ]
        mainmenu.item_add('music', 5, _('Music'), 'icon/music',
                          self.cb_mainmenu, subitems)

        # create a browser instance
        self._browser = EmcBrowser(_('Music'), icon='icon/music')
        self._rebuild_idler = None
        self._rebuild_timer = None
        self._rebuild_files = None
        self._folders = None

    def __shutdown__(self):
        global _mod

        DBG('Shutdown module')

        # delete mainmenu item
        mainmenu.item_del('music')

        # delete browser
        self._browser.delete()

        # close databases
        if self._songs_db:
            del self._songs_db
        if self._albums_db:
            del self._albums_db
        if self._artists_db:
            del self._artists_db

        _mod = None

    def cb_mainmenu(self, url=None):
        # get music folders from config
        self._folders = ini.get_string_list('music', 'folders', ';')
        # if not self._folders:
        # print('NO FOLDERS')
        # TODO alert the user. and instruct how to add folders
        # return

        # open songs/albums/artists database (they are created if not exists)
        if self._songs_db is None:
            self._songs_db = EmcDatabase('music_songs')
        if self._albums_db is None:
            self._albums_db = EmcDatabase('music_albums')
        if self._artists_db is None:
            self._artists_db = EmcDatabase('music_artists')

        # restore a previous browser state (if available)
        if self._browser.freezed and not url:
            self._browser.unfreeze()
            return

        # clear the browser state (if an url is requested)
        if self._browser.freezed and url:
            self._browser.clear()

        # start the browser in the requested page
        if url is None:
            self._browser.clear()
            self._browser.page_add('music://root', _('Music'), self._styles, self.populate_root_page)
        elif url == 'music://artists':
            self._browser.page_add(url, _('Artists'), self._styles, self.populate_artists_page)
        elif url == 'music://albums':
            self._browser.page_add(url, _('Albums'), self._styles2, self.populate_albums_page)
        elif url == 'music://songs':
            self._browser.page_add(url, _('Songs'), self._styles, self.populate_songs_page)

        self._browser.show()
        mainmenu.hide()

        # trigger a new scan (DISABLED FOR NOW)
        # self.rebuild_db()

    # ### rebuild db stuff
    def rebuild_db(self):
        if self._rebuild_notify is None:
            txt = '<title>%s</title><br>%s' % \
                  (_('Rebuilding database'), _('please wait...'))
            self._rebuild_notify = EmcNotify(hidein=0, icon='icon/music', text=txt)

            self._rebuild_files = utils.grab_files(self._folders)
            self._rebuild_timer = ecore.Timer(1.0, self.rebuild_db_timer)
            self._rebuild_idler = ecore.Idler(self.rebuild_db_idler)

    def rebuild_db_timer(self):
        self._browser.refresh()
        return ecore.ECORE_CALLBACK_RENEW

    def rebuild_db_idler(self):
        try:
            # get the next file from the generator and read metadata (if needed)
            full_path = next(self._rebuild_files)
            (name, ext) = os.path.splitext(full_path)
            if ext.lower() in mediaplayer.audio_extensions:
                if self._songs_db.id_exists('file://' + full_path):
                    DBG('FOUND IN DB')
                else:
                    self.read_file_metadata(full_path)
            else:
                DBG('Warning: invalid file extension for file: ' + full_path)
        except StopIteration:
            # no more files to process, all done
            self._rebuild_timer.delete()
            self._rebuild_idler = None
            self._rebuild_timer = None
            self._rebuild_files = None

            self._rebuild_notify.close()
            self._rebuild_notify = None
            txt = '<title>%s</title><br>%s' % \
                  (_('Rebuilding database'), _('operation completed'))
            EmcNotify(icon='icon/music', text=txt)
            self._browser.refresh()
            return ecore.ECORE_CALLBACK_CANCEL

        return ecore.ECORE_CALLBACK_RENEW

    def read_file_metadata(self, full_path):
        DBG('GET METADATA FOR: ' + full_path)

        try:
            meta = mutagen.File(full_path, easy=True)
            assert meta is not None
        except:
            return

        title = artist = album = None

        if 'title' in meta:
            if isinstance(meta['title'][0], bytes):
                title = meta['title'][0].decode('utf-8')
            elif utils.is_py3():
                title = meta['title'][0]
            else:
                title = meta['title'][0].encode('utf-8')

        if 'artist' in meta:
            if isinstance(meta['artist'][0], bytes):
                artist = meta['artist'][0].decode('utf-8')
            elif utils.is_py3():
                artist = meta['artist'][0]
            else:
                artist = meta['artist'][0].encode('utf-8')

        if 'album' in meta:
            if isinstance(meta['album'][0], bytes):
                album = meta['album'][0].decode('utf-8')
            elif utils.is_py3():
                album = meta['album'][0]
            else:
                album = meta['album'][0].encode('utf-8')

        item_data = dict()
        item_data['url'] = 'file://' + full_path
        item_data['title'] = title or os.path.basename(full_path)

        if artist:
            item_data['artist'] = artist

            # create artist item if necessary
            if not self._artists_db.id_exists(artist):
                DBG('NEW ARTIST: {}'.format(artist))
                artist_data = {'name': artist, 'albums': [], 'songs': []}
            else:
                DBG('ARTIST EXIST')
                artist_data = self._artists_db.get_data(artist)

            # add song to song list (in artist), only if not exists yet
            if not full_path in artist_data['songs']:
                artist_data['songs'].append('file://' + full_path)

            # add album to albums list (in artist), only if not exist yet
            if 'album' in meta and not meta['album'] in artist_data['albums']:
                artist_data['albums'].append(meta['album'])

            # write artist to db
            self._artists_db.set_data(artist, artist_data)
        else:
            item_data['artist'] = 'Unknown'

        try:
            if '/' in meta['tracknumber'][0]:
                tn = int(meta['tracknumber'][0].split('/')[0])
            else:
                tn = int(meta['tracknumber'][0])
            item_data['tracknumber'] = tn
        except:
            item_data['tracknumber'] = 0

        if 'length' in meta:
            item_data['length'] = meta['length'][0].encode('utf-8')

        if album:
            item_data['album'] = album

            # create album item if necesary
            if not self._albums_db.id_exists(album):
                DBG('NEW ALBUM: {}'.format(album))
                album_data = {'name': album, 'artist': artist, 'songs': []}
            else:
                DBG('ALBUM EXIST')
                album_data = self._albums_db.get_data(album)

            # add song to song list (in album), only if not exists yet
            if not full_path in album_data['songs']:
                album_data['songs'].append('file://' + full_path)

            # write album to db
            self._albums_db.set_data(item_data['album'], album_data)
        else:
            item_data['album'] = 'Unknown'

        # write song to db
        self._songs_db.set_data('file://' + full_path, item_data)

    # playlist & metadata stuff
    def search_poster_for_album(self, album):
        # search as the first song of the album
        if 'songs' in album and len(album['songs']) > 0:
            return self.search_poster_for_song(album['songs'][0])
        return None

    @staticmethod
    def search_poster_for_artist(artist):
        # TODO implement
        return None

    def search_poster_for_song(self, url, song=None):
        # search "front.jpg" in the song folder
        path = os.path.dirname(utils.url2path(url))
        poster = os.path.join(path, 'front.jpg')
        if os.path.exists(poster):
            return poster

        # search "cover.jpg" in the song folder
        poster = os.path.join(path, 'cover.jpg')
        if os.path.exists(poster):
            return poster

        if song is None:
            song = self._songs_db.get_data(url)

        if (not song) or (not 'artist' in song) or (not 'album' in song):
            return None

        # search "<Artist> - <Album>.jpg"  in the song folder
        poster = os.path.join(path, song['artist'] + ' - ' + song['album'] + '.jpg')
        if os.path.exists(poster): return poster

        # <config_dir>/music_covers/<Artist> - <Album>.jpg
        poster = os.path.join(ini.get('music', 'covers_dir'),
                              song['artist'] + ' - ' + song['album'] + '.jpg')
        if os.path.exists(poster):
            return poster

    def playlist_metadata_cb(self, item, song=None):
        if song is None:
            song = self._songs_db.get_data(item.url)

        # build the metadata dict from a shallow copy of the song data
        metadata = song.copy()
        metadata['poster'] = self.search_poster_for_song(song['url'], song)
        if 'length' in metadata:
            metadata['length'] = int(metadata['length']) / 1000.0

        return metadata

    def queue_url(self, url, song=None):
        if song is None:
            song = self._songs_db.get_data(url)

        metadata = self.playlist_metadata_cb(None, song)
        mediaplayer.playlist.append(url, metadata=metadata)

        if mediaplayer.playlist.onair_item is None:
            mediaplayer.playlist.play_next()
        else:
            EmcNotify('<title>%s</><br>%s' % (song['title'], _('queued')),
                      icon='icon/music')

    def queue_song_list(self, songs_list, queue):
        if queue is False:
            mediaplayer.playlist.clear()
        for song in songs_list:
            mediaplayer.playlist.append(song['url'], metadata_cb=self.playlist_metadata_cb)

    # browser pages
    def populate_root_page(self, browser, page_url):
        count = len(self._artists_db)
        # self._browser.item_add('music://generes', 'Generes (TODO)')
        # self._browser.item_add('music://playlists', 'Playlists (TODO)')
        self._browser.item_add(RootOnAirItemClass(), 'music://onair', self)
        self._browser.item_add(RootArtistsItemClass(), 'music://artists', self)
        self._browser.item_add(RootAlbumsItemClass(), 'music://albums', self)
        self._browser.item_add(RootSongsItemClass(), 'music://songs', self)
        self._browser.item_add(RootRebuildItemClass(), 'music://rebuild', self)
        self._browser.item_add(RootAddSourceItemClass(), 'music://add_source', self)

    def populate_songs_page(self, browser, page_url):
        """ list of all the songs """
        li = [self._songs_db.get_data(k) for k in self._songs_db.keys()]
        self._browser.item_add(PlaySongsItemClass(), page_url, li)
        for song in sorted(li, key=operator.itemgetter('title')):
            self._browser.item_add(SongWithArtistItemClass(), song['url'], song)

    def populate_albums_page(self, browser, page_url):
        """ list of all albums (grouped by artist) """
        li = [self._albums_db.get_data(k) for k in self._albums_db.keys()]
        last_artist = None
        for album in sorted(li, key=lambda md: md.get('artist', '') or ''):
            if album['artist'] != last_artist:
                last_artist = album['artist']
                self._browser.group_add(last_artist, 'icon/artist')
            self._browser.item_add(AlbumItemClass(), album['name'], album)

    def populate_artists_page(self, browser, page_url):
        """ list of all artists """
        li = [self._artists_db.get_data(k) for k in self._artists_db.keys()]
        for artist in sorted(li, key=lambda md: md.get('name', '') or ''):
            self._browser.item_add(ArtistItemClass(), artist['name'], artist)

    def populate_artist_page(self, browser, url, artist):
        """ list of all songs for the given artist (grouped by album) """
        li = [self._songs_db.get_data(url) for url in artist['songs']]
        li.sort(key=operator.itemgetter('album', 'tracknumber', 'title'))
        self._browser.item_add(PlaySongsItemClass(), url, li)
        self._browser.item_add(QueueSongsItemClass(), url, li)
        last_album = None
        for song in li:
            if song['album'] != last_album:
                last_album = song['album']
                self._browser.group_add(last_album, 'icon/album')
            self._browser.item_add(SongItemClass(), song['url'], song)

    def populate_album_page(self, browser, url, album):
        """ list of all songs in the given album """
        li = [self._songs_db.get_data(url) for url in album['songs']]
        li.sort(key=operator.itemgetter('tracknumber', 'title'))
        self._browser.item_add(PlaySongsItemClass(), url, li)
        self._browser.item_add(QueueSongsItemClass(), url, li)
        for song in li:
            self._browser.item_add(SongItemClass(), song['url'], song)
