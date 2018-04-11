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

import json

# Use python-libdiscid or python-discid
try:
  from libdiscid.compat import discid
except ImportError:
  import discid

import epymc.utils as utils
from epymc.gui import EmcDialog, EmcImage
from epymc import __version__ as vers


def DBG(*args):
   print('MBRAINZ:', *args)
   pass


API_BASE = 'http://musicbrainz.org/ws/2'
API_HEADS = {'User-Agent': 'EpyMC/{} ( github.com/DaveMDS/epymc )'.format(vers)}
ART_BASE = 'http://coverartarchive.org'


class MusicBrainz(object):
   """ TODO doc """

   def __init__(self, show_gui=True):
      self._show_gui = show_gui
      self._wait_dialog = None

   def get_cdrom_discid(self, device_path):
      """ Retrive the discid from the disc in the drive

      Args:
         device_path:  cdrom device that must contain a valid AudioCD

      Return:
         The extracted discid (str), ex: "tULuQ98H70kkMmAtHFR7jKlxGRU-"

      """
      try:
         # TODO: this is a bit slow... should be async'ed in some way?
         disc = discid.read(device_path, features=[])
      except discid.DiscError:
         return None
      else:
         return disc.id

   def get_cdrom_info(self, device_path, info_cb, ignore_cache=False, **kargs):
      """ Fetch cdrom album info from the MusicBrainz service

      Args:
         device_path: cdrom device that must contain a valid AudioCD
         info_cb: user function to call when operation completed
                  sig: func(album_data, **kargs) album_data is None on errors
         ignore_cache: do not lookup in cache
         **kargs: any other keyword arguments will be passed back in the info_cb

      Return:
         True if the operation started successfully, info_cb will be called later
         False in case of errors
         dict (album_data) if the info was already fatched and cached

      """
      # exctract discid
      disc_id = self.get_cdrom_discid(device_path)
      if disc_id is None:
         return False
      DBG('discid', disc_id)

      # TODO use an emc db to cache results

      # MusicBrainz discid query
      self._show_wait_dialog()
      url = '{}/discid/{}?fmt=json&inc=artists+recordings'.format(API_BASE, disc_id)
      utils.EmcUrl(url, headers=API_HEADS, done_cb=self._cdrom_info_done_cb,
                   disc_id=disc_id, user_cb=info_cb, user_kargs=kargs)
      return True

   def _cdrom_info_done_cb(self, url, status, data, disc_id, user_cb, user_kargs):
      self._destroy_wait_dialog()
      if status != 200:
         user_cb(None, **user_kargs)
         return

      # parse the json response
      json_data = json.loads(data)
      if not json_data or 'error' in json_data:
         user_cb(None, **user_kargs)
         return

      # consider only in the first release (album) found
      try:
         rel = json_data['releases'][0]
      except KeyError:
         user_cb(None, **user_kargs)
         return

      # basic album info
      mbzid = rel.get('id')
      title = rel.get('title')
      date = rel.get('date')
      country = rel.get('country')

      # artists names
      artists = []
      if 'artist-credit' in rel:
         for artist in rel['artist-credit']:
            if 'name' in artist:
               artists.append(artist['name'])

      # track titles + durations
      tracks = []
      if 'media' in rel and len(rel['media']) > 0 and 'tracks' in rel['media'][0]:
         for trk in rel['media'][0]['tracks']:
            track_data = {
               'title': trk.get('title'),
               'length': (trk['length'] / 1000) if 'length' in trk else 0,
               'num': int(trk.get('number', -1))
            }
            tracks.append(track_data)

      # cover-art url (search in ALL releases)
      cover_url = None
      for r in json_data['releases']:
         if mbzid and 'cover-art-archive' in r:
            archive = r['cover-art-archive']
            if archive.get('artwork') == True and archive.get('front') == True:
               cover_url = '{}/release/{}/front-500'.format(ART_BASE, r['id'])

      # build our simple data storage
      album = {
         'mbzid': mbzid,
         'discid': disc_id,
         'title': title,
         'date': date,
         'artists': artists,
         'cover_url': cover_url,
         'tracks': tracks,
      }
      DBG(album)

      # and finally call the user callback
      user_cb(album, **user_kargs)

   def _show_wait_dialog(self):
      if self._show_gui:
         self._wait_dialog = EmcDialog(style='minimal',
                                 title=_('Fetching info'),
                                 content=EmcImage('image/musicbrainz_logo.png'),
                                 spinner=True)

   def _destroy_wait_dialog(self):
      if self._wait_dialog is not None:
         self._wait_dialog.delete()
         self._wait_dialog = None
