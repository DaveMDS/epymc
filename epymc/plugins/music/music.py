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

import os
import operator
import mutagen

from efl import ecore

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
   print('MUSIC: ' + msg)
   pass


_mod = None


class RootOnAirItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('music://onair', _('OnAir'), None,
                            mod.populate_onair_page)

   def label_get(self, url, mod):
      return _('OnAir')

   def label_end_get(self, url, mod):
      return str(len(mediaplayer.playlist))

   def icon_get(self, url, mod):
      return 'icon/play'

class RootArtistsItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('music://artists', _('Artists'), None,
                            mod.populate_artists_page)

   def label_get(self, url, mod):
      return _('Artists')

   def label_end_get(self, url, mod):
      return str(len(mod._artists_db))

class RootAlbumsItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('music://albums', _('Albums'), None,
                            mod.populate_albums_page)

   def label_get(self, url, mod):
      return _('Albums')

   def label_end_get(self, url, mod):
      return str(len(mod._albums_db))

class RootSongsItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('music://songs', _('Songs'), None,
                            mod.populate_songs_page)

   def label_get(self, url, mod):
      return _('Songs')

   def label_end_get(self, url, mod):
      return str(len(mod._songs_db))

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

   def _manager_cb(self, sources):
      _mod._folders = sources

   def label_get(self, url, mod):
      return _('Manage sources')

   def icon_get(self, url, mod):
      return 'icon/plus'

class QueueAlbumItemClass(EmcItemClass):
   def item_selected(self, url, album):
      _mod.queue_album(album)

   def label_get(self, url, album):
      return _('Play the whole album')

   def icon_get(self, url, album):
      return 'icon/plus'

class QueueArtistItemClass(EmcItemClass):
   def item_selected(self, url, album):
      _mod.queue_artist(album)

   def label_get(self, url, album):
      return _('Play all the songs')

   def icon_get(self, url, album):
      return 'icon/plus'

class SongItemClass(EmcItemClass):
   def item_selected(self, url, song):
      _mod.queue_url(url, song)

   def label_get(self, url, song):
      try:
         return "%02d - %s" % (song['tracknumber'], song['title'])
      except:
         return song['title']

   def poster_get(self, url, song):
      return _mod.search_poster_for_song(url, song)

   def info_get(self, url, song):
      text = '<title>' + song['title'] + '</><br>'
      if 'artist' in song:
         text += _('<em>by</em> %s<br>') % song['artist']
      if 'album' in song:
         text += _('<em>from</em> %s<br>') % song['album']
      if 'length' in song:
         length = int(song['length']) / 1000
         min = length / 60
         sec = length % 60
         text += _('duration: %s<br>') % ('%.02d:%.02d' % (min,sec))
      return text

   def icon_get(self, url, song):
      if url == mediaplayer._onair_url:
         return 'icon/play'

class AlbumItemClass(EmcItemClass):
   def item_selected(self, url, album):
      _mod._browser.page_add('music://album/'+album['name'], album['name'],
                             None, _mod.populate_album_page, album)

   def label_get(self, url, album):
      return _('%(name)s by %(artist)s') % (album)

   def poster_get(self, url, album):
      return _mod.search_poster_for_album(album)

   def info_get(self, url, album):
      text = '<title>' + album['name'] + '</><br>'
      text += _('<em>by</em> %s<br>') % album['artist']
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
      _mod._browser.page_add('music://artist/'+artist['name'], artist['name'],
                             None, _mod.populate_artist_page, artist)

   def label_get(self, url, artist):
      return artist['name']

   def poster_get(self, url, artist):
      return _mod.search_poster_for_artist(artist)

   def info_get(self, url, artist):
      n = len(artist['albums'])
      albums = ngettext('%d album', '%d albums', n) % n
      n = len(artist['songs'])
      songs = ngettext('%d song', '%d songs', n) % n
      return '<title>%s</><br>%s, %s' % (artist['name'], albums, songs)


class MusicModule(EmcModule):
   name = 'music'
   label = _('Music')
   icon = 'icon/music'
   info = _("""Long info for the <b>Music</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>""")

   _browser = None        # browser instance
   _rebuild_notify = None # rebuild notification object

   _songs_db = None     # key=url           data=dict
   _albums_db = None    # key=album_name    data=dict
   _artists_db = None   # key=artist_name   data=dict


   def __init__(self):
      global _mod

      DBG('Init module')
      _mod = self

      # create config ini section if not exists
      ini.add_section('music')

      # make default of covers_dir if necessary
      if not ini.has_option('music', 'covers_dir'):
         dir = os.path.join(utils.user_conf_dir, 'music_covers')
         ini.set('music', 'covers_dir', dir)

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
      self._browser = EmcBrowser(_('Music'))

      # listen to emc events
      events.listener_add('music', self.events_cb)

   def __shutdown__(self):
      global _mod
      
      DBG('Shutdown module')

      # stop listen to emc events
      events.listener_del('music')

      # delete mainmenu item
      mainmenu.item_del('music')

      # delete browser
      self._browser.delete()

      ## close databases
      if self._songs_db: del self._songs_db
      if self._albums_db: del self._albums_db
      if self._artists_db: del self._artists_db

      _mod = None

   def cb_mainmenu(self, url=None):
      # get music folders from config
      self._folders = ini.get_string_list('music', 'folders', ';')
      # if not self._folders:
         # print('NO FOLDERS')
         #TODO alert the user. and instruct how to add folders
         # return

      # open songs/albums/artists database (they are created if not exists)
      if self._songs_db is None:
         self._songs_db = EmcDatabase('music_songs')
      if self._albums_db is None:
         self._albums_db = EmcDatabase('music_albums')
      if self._artists_db is None:
         self._artists_db = EmcDatabase('music_artists')

      # start the browser in the requested page
      if url is None:
         self._browser.page_add('music://root', _('Music'), None, self.populate_root_page)
      elif url == 'music://artists':
         self._browser.page_add(url, _('Artists'), None, self.populate_artists_page)
      elif url == 'music://albums':
         self._browser.page_add(url, _('Albums'), None, self.populate_albums_page)
      elif url == 'music://songs':
         self._browser.page_add(url, _('Songs'), None, self.populate_songs_page)

      self._browser.show()
      mainmenu.hide()

      # trigger a new scan (DISABLED FOR NOW)
      # self.rebuild_db()

   ### rebuild db stuff
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
         full_path = self._rebuild_files.next()
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
         return ecore.ECORE_CALLBACK_CANCEL

      return ecore.ECORE_CALLBACK_RENEW

   def read_file_metadata(self, full_path):
      DBG('GET METADATA FOR: ' + full_path)

      try:
         meta = mutagen.File(full_path, easy=True)
         assert meta is not None
      except:
         return

      item_data = dict()
      item_data['url'] = 'file://' + full_path

      if 'title' in meta:
         item_data['title'] = meta['title'][0].encode('utf-8') # TODO is the encode correct? doesn't evas support unicode now??
      else:
         item_data['title'] = os.path.basename(full_path)

      if 'artist' in meta:
         item_data['artist'] = meta['artist'][0].encode('utf-8')

         # create artist item if necessary
         if not self._artists_db.id_exists(item_data['artist']):
            DBG('NEW ARTIST: ' + item_data['artist'])
            artist_data = dict()
            artist_data['name'] = item_data['artist']
            artist_data['albums'] = list()
            artist_data['songs'] = list()
         else:
            DBG('ARTIST EXIST')
            artist_data = self._artists_db.get_data(item_data['artist'])

         # add song to song list (in artist), only if not exists yet
         if not full_path in artist_data['songs']:
            artist_data['songs'].append('file://' + full_path)

         # add album to albums list (in artist), only if not exist yet
         if 'album' in meta and not meta['album'] in artist_data['albums']:
            artist_data['albums'].append(meta['album'])

         # write artist to db
         self._artists_db.set_data(item_data['artist'], artist_data)
      else:
         item_data['artist'] = 'Unknow'

      try:
         if '/' in meta['tracknumber'][0]:
            tn = int(meta['tracknumber'][0].split('/')[0])
         else:
            tn = int(meta['tracknumber'][0])
         item_data['tracknumber'] = tn
      except:
         pass

      if 'length' in meta:
         item_data['length'] = meta['length'][0].encode('utf-8')

      if 'album' in meta:
         item_data['album'] = meta['album'][0].encode('utf-8')

         # create album item if necesary
         if not self._albums_db.id_exists(item_data['album']):
            DBG('NEW ALBUM: ' + item_data['album'])
            album_data = dict()
            album_data['name'] = item_data['album']
            album_data['artist'] = item_data['artist']
            album_data['songs'] = list()
         else:
            DBG('ALBUM EXIST')
            album_data = self._albums_db.get_data(item_data['album'])

         # add song to song list (in album), only if not exists yet
         if not full_path in album_data['songs']:
            album_data['songs'].append('file://' + full_path)

         # write album to db
         self._albums_db.set_data(item_data['album'], album_data)

      # write song to db
      self._songs_db.set_data('file://' + full_path, item_data)

   ### playlist & metadata stuff
   def search_poster_for_album(self, album):
      # search as the first song of the album
      if 'songs' in album and len(album['songs']) > 0:
         return self.search_poster_for_song(album['songs'][0])
      return None

   def search_poster_for_artist(self, artist):
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

   def queue_album(self, album):
      for url in album['songs']:
         mediaplayer.playlist.append(url, metadata_cb=self.playlist_metadata_cb)

      if mediaplayer._onair_url is None:
         mediaplayer.playlist.play_next()
      
      EmcNotify('<title>%s</><br>%s' % (album['name'], _('queued')),
                icon='icon/music')

   def queue_artist(self, artist):
      for url in artist['songs']:
         mediaplayer.playlist.append(url, metadata_cb=self.playlist_metadata_cb)

      if mediaplayer._onair_url is None:
         mediaplayer.playlist.play_next()
      
      EmcNotify('<title>%s</><br>%s' % (artist['name'], _('queued')),
                icon='icon/music')

   ### emc events callback
   def events_cb(self, event):

      if event == 'PLAYBACK_STARTED':
         DBG('PLAYBACK_STARTED')
         # update the audio controls
         if len(mediaplayer.playlist) > 0:
            if self._songs_db.id_exists(mediaplayer._onair_url):
               song = self._songs_db.get_data(mediaplayer._onair_url)
               text = '<title>' + song['title'] + '</><br>'
               if 'artist' in song:
                  text += _('<em>by</em> %s<br>') % song['artist']
               if 'album' in song:
                  text += _('<em>from</em> %s<br>') % song['album']
               gui.audio_controls_show(text = text)

         # update the browser view
         self._browser.refresh()

      elif event == 'PLAYBACK_FINISHED':
         DBG('PLAYBACK_FINISHED')
         gui.audio_controls_hide()
         self._browser.refresh()

### browser pages
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

   def populate_onair_page(self, browser, page_url):
      """ list of songs in the current queue """
      for item in mediaplayer.playlist.items:
         song = self._songs_db.get_data(item.url)
         self._browser.item_add(SongItemClass(), item.url, song)

   def populate_songs_page(self, browser, page_url):
      """ list of all the songs """
      L = [self._songs_db.get_data(k) for k in self._songs_db.keys()]
      for song in sorted(L, key = operator.itemgetter('title')):
         self._browser.item_add(SongItemClass(), song['url'], song)

   def populate_albums_page(self, browser, page_url):
      """ list of all albums """
      L = [self._albums_db.get_data(k) for k in self._albums_db.keys()]
      for album in sorted(L, key = operator.itemgetter('name')):
         self._browser.item_add(AlbumItemClass(), album['name'], album)

   def populate_artists_page(self, browser, page_url):
      """ list of all artists """
      L = [self._artists_db.get_data(k) for k in self._artists_db.keys()]
      for artist in sorted(L, key = operator.itemgetter('name')):
         self._browser.item_add(ArtistItemClass(), artist['name'], artist)

   def populate_artist_page(self, browser, url, artist):
      """ list of all songs for the given artist """
      self._browser.item_add(QueueArtistItemClass(), url, artist)
      
      for song_url in artist['songs']:
         # TODO order by album/tracknumber/title
         # ... maybe use genlist group !
         song = self._songs_db.get_data(song_url)
         self._browser.item_add(SongItemClass(), song['url'], song)

   def populate_album_page(self, browser, url, album):
      """ list of all songs in the given album """
      self._browser.item_add(QueueAlbumItemClass(), url, album)
      
      L = []
      for song_url in album['songs']:
         song = self._songs_db.get_data(song_url)
         try:
            song['label'] = "[%02d] - %s" % (song['tracknumber'], song['title'])
         except:
            song['label'] = song['title']
         L.append(song)

      # TODO sort by label
      # ...or better don't do the label and sort by tracknumber/label
      #
      # for song in sorted(L, key='tracknumber'):
      for song in L:
         self._browser.item_add(SongItemClass(), song['url'], song)
