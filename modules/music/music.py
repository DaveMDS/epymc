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

import os
import operator
import threading

import ecore

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.sdb import EmcDatabase
from epymc.gui import EmcDialog
import epymc.mainmenu as mainmenu
import epymc.utils as utils
import epymc.ini as ini


def DBG(msg):
   # print('MUSIC: ' + msg)
   pass


_audio_extensions = ['.mp3', '.MP3']
_mod = None


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


class SongItemClass(EmcItemClass):
   def item_selected(self, url, song):
      _mod.song_selected(url)

   def label_get(self, url, song):
      return song['title']

   def poster_get(self, url, song):
      return _mod.song_poster_get(url)

   def info_get(self, url, song):
      return _mod.song_info_get(url)


class AlbumItemClass(EmcItemClass):
   def item_selected(self, url, album):
      _mod.album_selected(url)

   def label_get(self, url, album):
      return album['name'] + '  by ' + album['artist']

   def poster_get(self, url, album):
      return _mod.album_poster_get(url)

   def info_get(self, url, album):
      return _mod.album_info_get(url)


class ArtistItemClass(EmcItemClass):
   def item_selected(self, url, artist):
       _mod.artist_selected(url)

   def label_get(self, url, artist):
      return artist['name']

   def poster_get(self, url, artist):
      return _mod.artist_poster_get(url)

   def info_get(self, url, artist):
      return _mod.artist_info_get(url)


class MusicModule(EmcModule):
   name = 'music'
   label = 'Music'
   icon = 'icon/module'
   info = """Long info for the <b>Music</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>"""

   def __init__(self):
      global _mod

      DBG('Init module')
      _mod = self

      # create config ini section if not exists
      ini.add_section('music')

      # make default of covers_dir if necessary
      if not ini.has_option('music', 'covers_dir'):
         dir = os.path.join(utils.config_dir_get(), 'music_covers')
         ini.set('music', 'covers_dir', dir)

      if not os.path.exists(ini.get('music', 'covers_dir')):
         os.mkdir(ini.get('music', 'covers_dir'))

      # open songs/albums/artists database (they are created if not exists)
      self._songs_db = EmcDatabase('music_songs')
      self._albums_db = EmcDatabase('music_albums')
      self._artists_db = EmcDatabase('music_artists')

      # add an item in the mainmenu
      mainmenu.item_add('music', 5, 'Music', None, self.cb_mainmenu)

      # create a browser instance
      self._browser = EmcBrowser('Music')

   def __shutdown__(self):
      DBG('Shutdown module')
      # delete mainmenu item
      mainmenu.item_del('music')

      # delete browser
      self._browser.delete()

      ## close databases
      del self._songs_db
      del self._albums_db
      del self._artists_db


   def cb_mainmenu(self):
      # get music folders from config
      self.__folders = ini.get_string_list('music', 'folders', ';')
      if not self.__folders:
         print 'NO FOLDERS'
         #TODO alert the user. and instruct how to add folders
         return

      # show the root page
      self._browser.page_add('music://root', 'Music', None, self.populate_root_page)
      self._browser.show()
      mainmenu.hide()

      # Update db in a parallel thread
      self.dialog = EmcDialog(title = 'Rebuilding Database, please wait...',
                              spinner = True, style = 'cancel')

      thread = UpdateDBThread(self.__folders, self._songs_db,
                              self._albums_db, self._artists_db)
      thread.start()
      ecore.Timer(0.5, self.check_thread_done, thread)

   def check_thread_done(self, thread):
      if thread.is_alive():
         return True # renew the timer

      # thread done, kill the dialog
      self.dialog.delete()
      del self.dialog

      return False # kill the timer

### browser pages
   def populate_root_page(self, browser, page_url):
      count = len(self._artists_db)
      self._browser.item_add(RootArtistsItemClass(), 'music://artists', self)
      self._browser.item_add(RootAlbumsItemClass(), 'music://albums', self)
      self._browser.item_add(RootSongsItemClass(), 'music://songs', self)
      # self._browser.item_add('music://generes', 'Generes (TODO)')
      # self._browser.item_add('music://playlists', 'Playlists (TODO)')

   def populate_songs_page(self, browser, page_url):
      L = list()
      for key in self._songs_db.keys():
         L.append(self._songs_db.get_data(key))

      for song in sorted(L, key = operator.itemgetter('title')):
         self._browser.item_add(SongItemClass(), song['url'], song)

   def populate_albums_page(self, browser, page_url):
      L = list()
      for key in self._albums_db.keys():
         L.append(self._albums_db.get_data(key))

      for album in sorted(L, key = operator.itemgetter('name')):
         self._browser.item_add(AlbumItemClass(), album['name'], album)

   def populate_artists_page(self, browser, page_url):
      L = list()
      for key in self._artists_db.keys():
         L.append(self._artists_db.get_data(key))

      for artist in sorted(L, key = operator.itemgetter('name')):
         self._browser.item_add(ArtistItemClass(), artist['name'], artist)

### artists stuff
   def artist_selected(self, artist):
      artist_data = self._artists_db.get_data(artist)
      import pprint
      pprint.pprint(artist_data)

   def artist_poster_get(self, artist):
      # TODO implement
      return None
   
   def artist_info_get(self, artist):
      artist_data = self._artists_db.get_data(artist)
      text = '<hilight>%s</><br>' % (artist_data['name'])
      text += '%d albums, %d songs' % (len(artist_data['albums']), len(artist_data['songs']))
      return text

### songs stuff
   def song_selected(self, url):
      print 'SEL ' + url
      song_data = self._songs_db.get_data(url)

      import pprint
      pprint.pprint(song_data)

   def song_poster_get(self, url):
      song_data = self._songs_db.get_data(url)

      # Search cover in song directory:
      #'front.jpg', 'cover.jpg' or '<Artist> - <Album>.jpg'

      path = os.path.dirname(url)
      poster = os.path.join(path, 'front.jpg')
      if os.path.exists(poster): return poster

      poster = os.path.join(path, 'cover.jpg')
      if os.path.exists(poster): return poster

      if not song_data.has_key('artist') or not song_data.has_key('album'):
         return None

      poster = os.path.join(path, song_data['artist'] + ' - ' + song_data['album'] + '.jpg')
      if os.path.exists(poster): return poster

      # Search cover in user dir:
      # <config_dir>/music_covers/<Artist> - <Album>.jpg
      poster = os.path.join(ini.get('music', 'covers_dir'),
                     song_data['artist'] + ' - ' + song_data['album'] + '.jpg')
      if os.path.exists(poster):
         return poster

      return None

   def song_info_get(self, url):
      song_data = self._songs_db.get_data(url)
      text = '<hilight>' + song_data['title'] + '</><br>'
      if song_data.has_key('artist'):
         text += '<em>by ' + song_data['artist'] + '</><br>'
      if song_data.has_key('album'):
         text += 'from ' + song_data['album'] + '<br>'
      if song_data.has_key('length'):
         length = int(song_data['length']) / 1000
         min = length / 60
         sec = length % 60
         text += 'duration: ' + str(min) + ':' + str(sec)  + '<br>'
      return text

### albums stuff
   def album_selected(self, album):
      album_data = self._albums_db.get_data(album)
      import pprint
      pprint.pprint(album_data)

   def album_poster_get(self, album):
      album_data = self._albums_db.get_data(album)

      # Search cover in first-song-of-album directory:
      #'front.jpg', 'cover.jpg' or '<Artist> - <Album>.jpg'
      if album_data['songs']:
         path = os.path.dirname(album_data['songs'][0])
         poster = os.path.join(path, 'front.jpg')
         if os.path.exists(poster): return poster

         poster = os.path.join(path, 'cover.jpg')
         if os.path.exists(poster): return poster

         poster = os.path.join(path, album_data['artist'] + ' - ' + album + '.jpg')
         if os.path.exists(poster): return poster

      # Search cover in user dir:
      # <config_dir>/music_covers/<Artist> - <Album>.jpg
      poster = os.path.join(ini.get('music', 'covers_dir'),
                           album_data['artist'] + ' - ' + album + '.jpg')
      if os.path.exists(poster):
         return poster

      return None

   def album_info_get(self, album):
      album_data = self._albums_db.get_data(album)
      text = '<hilight>' + album_data['name'] + '</><br>'
      text += '<em>by ' + album_data['artist'] + '</><br>'
      text += str(len(album_data['songs'])) + ' songs'
      lenght = 0
      for song in album_data['songs']:
         song_data = self._songs_db.get_data(song)
         if song_data.has_key('length'):
            lenght += int(song_data['length'])
         print song_data
      text += ', ' + str(lenght / 60000) + ' min.'
      return text

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

      print 'This is the thread speaking, HALO'

      for folder in self.folders:
         # strip url
         if folder.find('://', 0, 16) > 0:
            folder = folder[folder.find('://')+3:]

         print 'Scanning dir ' + folder + ' ...'
         # count = 50 # TODO REMOVE ME

         for root, dirs, files in os.walk(folder):
            for file in files:
               (filename, ext) = os.path.splitext(file)
               if ext in _audio_extensions:
                  path = os.path.join(root, file)

                  if not self.songs_db.id_exists(path):
                     self.read_metadata(path)
                  else:
                     print 'FOUND IN DB'
                  # TODO Check also file modification time

                  #~ count -= 1 # TODO REMOVE ME
                  #~ if count < 1:# TODO REMOVE ME
                        #~ return # TODO REMOVE ME
               else:
                  print 'Error: invalid file extension for file: ' + file

   def read_metadata(self, full_path):
      print 'GET METADATA FOR: ' + full_path

      meta = EasyID3(full_path)

      import pprint
      pprint.pprint(meta)

      item_data = dict()

      item_data['url'] = full_path #TODO need to use a real url?

      if meta.has_key('title'):
         item_data['title'] = meta['title'][0].encode('utf-8') # TODO is the encode correct? doesn't evas support unicode now??
      else:
         item_data['title'] = full_path # TODO just file name


      if meta.has_key('artist'):
         item_data['artist'] = meta['artist'][0].encode('utf-8')

         # create artist item if necesary
         if not self.artists_db.id_exists(item_data['artist']):
            print 'NEW ARTIST: ' + item_data['artist']
            artist_data = dict()
            artist_data['name'] = item_data['artist']
            artist_data['albums'] = list()
            artist_data['songs'] = list()
         else:
            print 'ARTIST EXIST'
            artist_data = self.artists_db.get_data(item_data['artist'])

         # add song to song list (in artist), only if not exists yet
         if not full_path in artist_data['songs']:
            artist_data['songs'].append(full_path)

         # add album to albums list (in artist), only if not exist yet
         if meta.has_key('album') and not meta['album'] in artist_data['albums']:
            artist_data['albums'].append(meta['album'])

         # write artist to db
         self.artists_db.set_data(item_data['artist'], artist_data, thread_safe = False) # TODO thread_safe = True

      else:
         item_data['artist'] = 'Unknow'


      if meta.has_key('tracknumber'):
         item_data['tracknumber'] = meta['tracknumber'][0].encode('utf-8')

      if meta.has_key('length'):
         item_data['length'] = meta['length'][0].encode('utf-8')

      if meta.has_key('album'):
         item_data['album'] = meta['album'][0].encode('utf-8')

         # create album item if necesary
         if not self.albums_db.id_exists(item_data['album']):
            print 'NEW ALBUM: ' + item_data['album']
            album_data = dict()
            album_data['name'] = item_data['album']
            album_data['artist'] = item_data['artist']
            album_data['songs'] = list()
         else:
            print 'ALBUM EXIST'
            album_data = self.albums_db.get_data(item_data['album'])

         # add song to song list (in album), only if not exists yet
         if not full_path in album_data['songs']:
            album_data['songs'].append(full_path)

         # write album to db
         self.albums_db.set_data(item_data['album'], album_data, thread_safe = False) # TODO thread_safe = True

      # write song to db
      self.songs_db.set_data(full_path, item_data, thread_safe = False) # TODO thread_safe = True

