#!/usr/bin/env python

import os
import operator

import ecore

from modules import EmcModule
from browser import EmcBrowser
from sdb import EmcDatabase
from gui import EmcDialog
import mainmenu
import utils
import ini
import threading


_audio_extensions = ['.mp3', '.MP3']

def DBG(msg):
   #~ print('MUSIC: ' + msg)
   pass


class MusicModule(EmcModule):
   name = 'music'
   label = 'Music'

   __browser = None
   #~ __film_db = None

   def __init__(self):
      DBG('Init module')

      # create config ini section if not exists
      ini.add_section('music')

      # make default of covers_dir if necessary
      if not ini.has_option('music', 'covers_dir'):
         dir = os.path.join(utils.config_dir_get(), 'music_covers')
         ini.set('music', 'covers_dir', dir)

      if not os.path.exists(ini.get('music', 'covers_dir')):
         os.mkdir(ini.get('music', 'covers_dir'))

      # open film/person database (they are created if not exists)
      self.__songs_db = EmcDatabase('music_songs')
      self.__albums_db = EmcDatabase('music_albums')
      self.__artists_db = EmcDatabase('music_artists')

      # add an item in the mainmenu
      mainmenu.item_add('music', 5, 'Music', None, self.cb_mainmenu)

      # create a browser instance
      self.__browser = EmcBrowser('Music', 'List',
                           item_selected_cb = self.cb_item_selected,
                           poster_get_cb = self.cb_poster_get,
                           info_get_cb = self.cb_info_get)

   def __shutdown__(self):
      DBG('Shutdown module')
      # delete mainmenu item
      mainmenu.item_del('music')

      # delete browser
      del self.__browser

      ## close databases
      del self.__songs_db
      del self.__albums_db
      del self.__artists_db


   def cb_mainmenu(self):
      # get music folders from config
      self.__folders = ini.get_string_list('music', 'sources', ';')
      if not self.__folders:
         print "NO FOLDERS"
         #TODO alert the user. and instruct how to add folders
         return

      self.make_root_page()
      mainmenu.hide()
      self.__browser.show()

      # Update db in a parallel thread
      self.dialog = EmcDialog(title = 'Rebuilding Database, please wait...',
                              spinner = True)
      self.dialog.activate()
      thread = UpdateDBThread(self.__folders, self.__songs_db,
                              self.__albums_db, self.__artists_db)
      thread.start()
      ecore.Timer(0.5, self.check_thread_done, thread)

   def check_thread_done(self, thread):
      if thread.is_alive():
         return True # renew the timer

      # thread done, kill the dialog
      self.dialog.delete()
      del self.dialog

      return False # kill the timer
### pages
   def make_root_page(self):
      self.__browser.page_add("music://root", "Music")

      self.__browser.item_add('music://artists', 'Artists')
      self.__browser.item_add('music://albums', 'Albums')
      self.__browser.item_add('music://songs', 'Songs')
      self.__browser.item_add('music://generes', 'Generes (TODO)')
      self.__browser.item_add('music://playlists', 'Playlists (TODO)')
      self.__browser.item_add('emc://back', 'Back')

   def make_songs_list(self):
      self.__browser.page_add('music://songs', 'Songs')
                       #~ item_selected_cb = self.cb_song_selected,
                       #~ info_get_cb = self.cb_song_info_get)
      L = list()
      for key in self.__songs_db.keys():
         item_data = self.__songs_db.get_data(key)
         L.append((key, item_data['title']))

      L.sort(key = operator.itemgetter(1))
      for k, t in L:
         self.__browser.item_add(k, t)

   def make_albums_list(self):
      self.__browser.page_add('music://albums', 'Albums')
                       #~ item_selected_cb = self.cb_album_selected,
                       #~ info_get_cb = self.cb_album_info_get)
      L = list()
      for key in self.__albums_db.keys():
         album_data = self.__albums_db.get_data(key)
         label = album_data['name'] + '  by ' + album_data['artist']
         L.append((key, label))

      L.sort(key = operator.itemgetter(1))
      for k, l in L:
         self.__browser.item_add(k, l)

   def make_artists_list(self):
      self.__browser.page_add('music://artists', 'Artists')
                       #~ item_selected_cb = self.cb_artist_selected,
                       #~ info_get_cb = self.cb_artist_info_get)
      L = list()
      for key in self.__artists_db.keys():
         artist_data = self.__artists_db.get_data(key)
         label = artist_data['name']
         L.append((key, label))

      L.sort(key = operator.itemgetter(1))
      for k, l in L:
         self.__browser.item_add(k, l)
### browser callback 'dispatcher'
   def cb_item_selected(self, page_url, item_url):
      if item_url == 'music://root':
         self.make_root_page()
      elif item_url == 'music://songs':
         self.make_songs_list()
      elif item_url == 'music://albums':
         self.make_albums_list()
      elif item_url == 'music://artists':
         self.make_artists_list()
      else:
         if page_url == 'music://songs':
            self.song_selected(item_url)
         elif page_url == 'music://albums':
            self.album_selected(item_url)
         elif page_url == 'music://artists':
            self.artist_selected(item_url)

   def cb_poster_get(self, page_url, item_url):
      if page_url == 'music://albums':
         return self.album_poster_get(item_url)
      elif page_url == 'music://songs':
         return self.song_poster_get(item_url)
      elif page_url == 'music://artists':
         return self.artist_poster_get(item_url)
      return None

   def cb_info_get(self, page_url, item_url):
      if page_url == 'music://albums':
         return self.album_info_get(item_url)
      elif page_url == 'music://songs':
         return self.song_info_get(item_url)
      elif page_url == 'music://artists':
         return self.artist_info_get(item_url)
      return None
### artists stuff
   def artist_selected(self, artist):
      artist_data = self.__artists_db.get_data(artist)
      import pprint
      pprint.pprint(artist_data)

   def artist_poster_get(self, artist):
      # TODO implement
      return None
   
   def artist_info_get(self, artist):
      artist_data = self.__artists_db.get_data(artist)
      text = '<hilight>%s</><br>' % (artist_data['name'])
      text += '%d albums, %d songs' % (len(artist_data['albums']), len(artist_data['songs']))
      return text
### songs stuff
   def song_selected(self, url):
      print 'SEL ' + url
      song_data = self.__songs_db.get_data(url)

      import pprint
      pprint.pprint(song_data)

   def song_poster_get(self, url):
      song_data = self.__songs_db.get_data(url)

      # Search cover in song directory:
      #'front.jpg', 'cover.jpg' or '<Artist> - <Album>.jpg'
      #~ if album_data['songs']:
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
      song_data = self.__songs_db.get_data(url)
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
      album_data = self.__albums_db.get_data(album)
      import pprint
      pprint.pprint(album_data)

   def album_poster_get(self, album):
      album_data = self.__albums_db.get_data(album)

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
      album_data = self.__albums_db.get_data(album)
      text = '<hilight>' + album_data['name'] + '</><br>'
      text += '<em>by ' + album_data['artist'] + '</><br>'
      text += str(len(album_data['songs'])) + ' songs'
      lenght = 0
      for song in album_data['songs']:
         song_data = self.__songs_db.get_data(song)
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
         count = 50 # TODO REMOVE ME

         for root, dirs, files in os.walk(folder):
            for file in files:
               (filename, ext) = os.path.splitext(file)
               if ext in _audio_extensions:
                  path = os.path.join(root, file)

                  if not self.songs_db.id_exists(path):
                     self.read_metadata(path)
                  else:
                     print "FOUND IN DB"
                  # TODO Check also file modification time

                  #~ count -= 1 # TODO REMOVE ME
                  #~ if count < 1:# TODO REMOVE ME
                        #~ return # TODO REMOVE ME
               else:
                  print "Error: invalid file extension for file: " + file

   def read_metadata(self, full_path):
      print "GET METADATA FOR: " + full_path

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

