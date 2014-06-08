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
import threading

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


_audio_extensions = ['.mp3', '.MP3']
_mod = None


class RootOnAirItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('music://onair', 'OnAir', None,
                            mod.populate_onair_page)

   def label_get(self, url, mod):
      return 'OnAir'

   def icon_get(self, url, mod):
      return 'icon/home'

class RootArtistsItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('music://artists', 'Artists', None,
                            mod.populate_artists_page)

   def label_get(self, url, mod):
      return 'Artists (%d)' % (len(mod._artists_db))

class RootAlbumsItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('music://albums', 'Albums', None,
                            mod.populate_albums_page)

   def label_get(self, url, mod):
      return 'Albums (%d)' % (len(mod._albums_db))

class RootSongsItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod._browser.page_add('music://songs', 'Songs', None,
                            mod.populate_songs_page)

   def label_get(self, url, mod):
      return 'Songs (%d)' % (len(mod._songs_db))

class RootRebuildItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      mod.rebuild_db()

   def label_get(self, url, mod):
      return 'Rescan library'

   def icon_get(self, url, mod):
      return 'icon/refresh'

class RootAddSourceItemClass(EmcItemClass):
   def item_selected(self, url, mod):
      EmcSourcesManager('music', done_cb=self._manager_cb)

   def _manager_cb(self, sources):
      _mod._folders = sources

   def label_get(self, url, mod):
      return 'Manage sources'

   def icon_get(self, url, mod):
      return 'icon/plus'

class QueueAlbumItemClass(EmcItemClass):
   def item_selected(self, url, album):
      _mod.queue_album(album)

   def label_get(self, url, album):
      return 'Play the whole album'

   def icon_get(self, url, album):
      return 'icon/plus'

class QueueArtistItemClass(EmcItemClass):
   def item_selected(self, url, album):
      _mod.queue_artist(album)

   def label_get(self, url, album):
      return 'Play all the songs'

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
      # search "front.jpg"
      path = os.path.dirname(utils.url2path(url))
      poster = os.path.join(path, 'front.jpg')
      if os.path.exists(poster): return poster

      # search "cover.jpg"
      poster = os.path.join(path, 'cover.jpg')
      if os.path.exists(poster): return poster

      if not 'artist' in song or not 'album' in song:
         return None

      # search "<Artist> - <Album>.jpg"
      poster = os.path.join(path, song['artist'] + ' - ' + song['album'] + '.jpg')
      if os.path.exists(poster): return poster

      # search in user cover dir:
      # <config_dir>/music_covers/<Artist> - <Album>.jpg
      poster = os.path.join(ini.get('music', 'covers_dir'),
                            song['artist'] + ' - ' + song['album'] + '.jpg')
      if os.path.exists(poster):
         return poster

   def info_get(self, url, song):
      text = '<hilight>' + song['title'] + '</><br>'
      if 'artist' in song:
         text += '<em>by ' + song['artist'] + '</><br>'
      if 'album' in song:
         text += 'from ' + song['album'] + '<br>'
      if 'length' in song:
         length = int(song['length']) / 1000
         min = length / 60
         sec = length % 60
         text += 'duration: ' + str(min) + ':' + str(sec)  + '<br>'
      return text

   def icon_get(self, url, song):
      if url == mediaplayer._onair_url:
         return 'icon/play'

class AlbumItemClass(EmcItemClass):
   def item_selected(self, url, album):
      _mod._browser.page_add('music://album/'+album['name'], album['name'],
                             None, _mod.populate_album_page, album)

   def label_get(self, url, album):
      return album['name'] + '  by ' + album['artist']

   def poster_get(self, url, album):
      # Search cover in first-song-of-album directory:
      #'front.jpg', 'cover.jpg' or '<Artist> - <Album>.jpg'
      if album['songs']:
         path = os.path.dirname(album['songs'][0])
         poster = os.path.join(path, 'front.jpg')
         if os.path.exists(poster): return poster

         poster = os.path.join(path, 'cover.jpg')
         if os.path.exists(poster): return poster

         poster = os.path.join(path, album['artist'] + ' - ' + album['name'] + '.jpg')
         if os.path.exists(poster): return poster

      # Search cover in user dir:
      # <config_dir>/music_covers/<Artist> - <Album>.jpg
      poster = os.path.join(ini.get('music', 'covers_dir'),
                           album['artist'] + ' - ' + album['name'] + '.jpg')
      if os.path.exists(poster):
         return poster

   def info_get(self, url, album):
      text = '<hilight>' + album['name'] + '</><br>'
      text += '<em>by ' + album['artist'] + '</><br>'
      text += str(len(album['songs'])) + ' songs'
      lenght = 0
      for song in album['songs']:
         song_data = _mod._songs_db.get_data(song)
         if 'length' in song_data:
            lenght += int(song_data['length'])
      text += ', ' + str(lenght / 60000) + ' min.'
      return text

class ArtistItemClass(EmcItemClass):
   def item_selected(self, url, artist):
      _mod._browser.page_add('music://artist/'+artist['name'], artist['name'],
                             None, _mod.populate_artist_page, artist)

   def label_get(self, url, artist):
      return artist['name']

   def poster_get(self, url, artist):
      # TODO implement
      return None

   def info_get(self, url, artist):
      return '<hilight>%s</><br>%d albums, %d songs' % (artist['name'],
              len(artist['albums']), len(artist['songs']))


class MusicModule(EmcModule):
   name = 'music'
   label = 'Music'
   icon = 'icon/music'
   info = """Long info for the <b>Music</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>"""

   _browser = None        # browser instance
   _rebuild_notify = None # rebuild notification object
   _play_queue = []       # list of urls to play

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
         ('Artists', None, 'music://artists'),
         ('Albums', None, 'music://albums'),
         ('Songs', None, 'music://songs'),
      ]
      mainmenu.item_add('music', 5, 'Music', 'icon/music',
                        self.cb_mainmenu, subitems)

      # create a browser instance
      self._browser = EmcBrowser('Music')

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
         self._browser.page_add('music://root', 'Music', None, self.populate_root_page)
      elif url == 'music://artists':
         self._browser.page_add(url, 'Artists', None, self.populate_artists_page)
      elif url == 'music://albums':
         self._browser.page_add(url, 'Albums', None, self.populate_albums_page)
      elif url == 'music://songs':
         self._browser.page_add(url, 'Songs', None, self.populate_songs_page)

      self._browser.show()
      mainmenu.hide()

      # trigger a new scan (DISABLED FOR NOW)
      # self.rebuild_db()

   def rebuild_db(self):
      # Update db in a parallel thread
      if self._rebuild_notify is None:
         self._rebuild_notify = EmcNotify(
                  '<hilight>Rebuilding Database</><br>please wait...', hidein=0)

         thread = UpdateDBThread(self._folders, self._songs_db,
                                 self._albums_db, self._artists_db)
         thread.start()
         ecore.Timer(2.0, self.check_thread_done, thread)
      
   def check_thread_done(self, thread):
      if thread.is_alive():
         self._browser.refresh()
         return True # renew the timer

      # thread done, close the notification
      self._rebuild_notify.close()
      self._rebuild_notify = None

      # refresh the current page :/
      self._browser.refresh(hard=True)

      return False # kill the timer

   def queue_url(self, url, song = None):

      if song is None:
         song = self._songs_db.get_data(url)

      self._play_queue.append(url)

      if len(self._play_queue) == 1:
         mediaplayer.play_url(url, only_audio = True)
      else:
         EmcNotify('<hilight>%s</><br>queued' % (song['title']))

   def queue_album(self, album):

      for url in album['songs']:
         self._play_queue.append(url)

      if mediaplayer._onair_url is None:
         if len(self._play_queue) > 0:
            mediaplayer.play_url(self._play_queue[0], only_audio = True)
      
      EmcNotify('<hilight>%s</><br>queued' % (album['name']))

   def queue_artist(self, artist):

      DBG(str(artist))
      
      for url in artist['songs']:
         self._play_queue.append(url)

      if mediaplayer._onair_url is None:
         if len(self._play_queue) > 0:
            mediaplayer.play_url(self._play_queue[0], only_audio = True)
      
      EmcNotify('<hilight>%s</><br>queued' % (artist['name']))


   def events_cb(self, event):

      if event == 'PLAYBACK_STARTED':
         DBG('PLAYBACK_STARTED')
         # update the audio controls
         if len(self._play_queue) > 0:
            song = self._songs_db.get_data(self._play_queue[0])
            text = '<hilight>' + song['title'] + '</><br>'
            if 'artist' in song:
               text += '<em>by ' + song['artist'] + '</><br>'
            if 'album' in song:
               text += 'from ' + song['album'] + '<br>'
            gui.audio_controls_show(text = text)
         # update the browser view
         self._browser.refresh()

      elif event == 'PLAYBACK_FINISHED':
         DBG('PLAYBACK_FINISHED')
         # remove the finished song from queue
         if len(self._play_queue) > 0:
            self._play_queue.pop(0)
         # play the next songs in queue
         if len(self._play_queue) > 0:
            mediaplayer.play_url(self._play_queue[0], only_audio = True)
         # or hide the audio controls
         else:
            gui.audio_controls_hide()
         # update the browser view
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
      for url in self._play_queue:
         song = self._songs_db.get_data(url)
         self._browser.item_add(SongItemClass(), url, song)

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


###############################################################################
from mutagen.easyid3 import EasyID3

class UpdateDBThread(threading.Thread):

   def __init__(self, folders, songs_db, albums_db, artists_db):
      threading.Thread.__init__(self)
      self.folders = folders
      self.songs_db = songs_db
      self.albums_db = albums_db
      self.artists_db = artists_db

   def run(self):
      global _audio_extensions

      print('This is the thread speaking, HALO')

      for folder in self.folders:
         # strip url
         if folder.find('://', 0, 16) > 0:
            folder = folder[folder.find('://')+3:]

         print('Scanning dir ' + folder + ' ...')
         for root, dirs, files in os.walk(folder):
            for file in files:
               (filename, ext) = os.path.splitext(file)
               if ext in _audio_extensions:
                  path = os.path.join(root, file)

                  if not self.songs_db.id_exists('file://' + path):
                     self.read_metadata(path)
                  else:
                     print('FOUND IN DB')
                  # TODO Check also file modification time
               else:
                  print('Error: invalid file extension for file: ' + file)

   def read_metadata(self, full_path):
      DBG('GET METADATA FOR: ' + full_path)

      try:
         meta = EasyID3(full_path)
      except:
         return

      # import pprint
      # pprint.pprint(meta)

      item_data = dict()

      item_data['url'] = 'file://' + full_path

      if 'title' in meta:
         item_data['title'] = meta['title'][0].encode('utf-8') # TODO is the encode correct? doesn't evas support unicode now??
      else:
         item_data['title'] = full_path # TODO just file name

      if 'artist' in meta:
         item_data['artist'] = meta['artist'][0].encode('utf-8')

         # create artist item if necessary
         if not self.artists_db.id_exists(item_data['artist']):
            DBG('NEW ARTIST: ' + item_data['artist'])
            artist_data = dict()
            artist_data['name'] = item_data['artist']
            artist_data['albums'] = list()
            artist_data['songs'] = list()
         else:
            DBG('ARTIST EXIST')
            artist_data = self.artists_db.get_data(item_data['artist'])

         # add song to song list (in artist), only if not exists yet
         if not full_path in artist_data['songs']:
            artist_data['songs'].append('file://' + full_path)

         # add album to albums list (in artist), only if not exist yet
         if 'album' in meta and not meta['album'] in artist_data['albums']:
            artist_data['albums'].append(meta['album'])

         # write artist to db
         self.artists_db.set_data(item_data['artist'], artist_data,
                              thread_safe=False) # we should be the only writer
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
         if not self.albums_db.id_exists(item_data['album']):
            DBG('NEW ALBUM: ' + item_data['album'])
            album_data = dict()
            album_data['name'] = item_data['album']
            album_data['artist'] = item_data['artist']
            album_data['songs'] = list()
         else:
            DBG('ALBUM EXIST')
            album_data = self.albums_db.get_data(item_data['album'])

         # add song to song list (in album), only if not exists yet
         if not full_path in album_data['songs']:
            album_data['songs'].append('file://' + full_path)

         # write album to db
         self.albums_db.set_data(item_data['album'], album_data,
                              thread_safe=False) # we should be the only writer

      # write song to db
      self.songs_db.set_data('file://' + full_path, item_data,
                             thread_safe=False) # we should be the only writer

