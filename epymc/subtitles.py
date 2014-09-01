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

from __future__ import absolute_import, print_function

import os
import sys
import re
import glob
import codecs
import struct
import threading
import zlib
import base64
import codecs
import hashlib
from operator import itemgetter
try:
   from xmlrpclib import ServerProxy # py2
except:
   from xmlrpc.client import ServerProxy # py3

from efl import ecore

from epymc import utils, gui, ini
from epymc.gui import EmcDialog, EmcNotify
from epymc import __version__ as emc_version

def LOG(msg):
   print('SUBTITLES: %s' % msg)

def DBG(msg):
   # print('SUBTITLES: %s' % msg)
   pass


def read_file_with_encodings(fname, encodings):
   text = None
   for enc in encodings:
      try:
         DBG('Trying encoding: %s' % enc)
         with codecs.open(fname, encoding=enc) as f:
            text = f.read()
      except Exception as ex:
         DBG('Decode failed, error: %s' % ex)
      else:
         DBG('Decode successful')
         break
   return text

def srt_time_to_seconds(timestr):
   """ Convert "00:00:10,500" to seconds (float) """
   time, ms = timestr.split(',')
   h, m, s = map(int, time.split(':'))
   return (h * 1440) + (m * 60) + s + (float(ms) / 1000)

def parse_format_srt(full_text):
   """ SubRip (.srt) parser (en.wikipedia.org/wiki/SubRip)

   1
   00:00:10,500 --> 00:00:13,000  X1:63 X2:223 Y1:43 Y2:58
   Elephant's Dream

   2
   00:00:15,000 --> 00:00:18,000
   At the left we can see...

   """
   DBG('Parsing SRT format')
   idx = 0
   L = []
   for it in re.sub('\r\n', '\n', full_text).split('\n\n'):
      lines = [ x for x in it.split('\n') if x ] # spit and remove empty lines
      if len(lines) >= 3:
         start_str, end_str = lines[1].split(' --> ')
         L.append(SubtitleItem(idx, srt_time_to_seconds(start_str),
                                    srt_time_to_seconds(end_str),
                                    '<br>'.join(lines[2:])))
         idx += 1
   DBG('Loaded %d items' % len(L))
   return L

def parse_format_sub(full_text):
   """ MicroDVD (.sub) format

   Docs at: http://en.wikipedia.org/wiki/MicroDVD

   NOTE: Need framerate or frame number from emotion (not currently implemented)

   """
   raise NotImplementedError()


# Supported formats
FORMATS = ('.srt')
PARSERS = {
   '.srt': parse_format_srt,
}

class SubtitleItem(object):
   def __init__(self, idx, start, end, text):
      self.idx = idx
      self.start = start
      self.end = end
      self.text = text

   def __str__(self):
      return '[%d] %f -> %f : %s' % (self.idx, self.start, self.end, self.text)


class Subtitles(object):
   def __init__(self, url):
      self.media_path = utils.url2path(url)
      self.media_md5 = utils.md5(self.media_path)
      self.current_file = None
      self.current_item = None
      self.items = []
      self.delay = 0 # milliseconds

      self.encodings = []
      if ini.get_bool('subtitles', 'always_try_utf8'):
         self.encodings.append('utf-8')
      self.encodings.append(ini.get('subtitles', 'encoding'))

      availables = self.search_subs()
      if len(availables) > 0:
         self.file_set(availables[0])

   def search_subs(self):
      DBG('Searching subs for file %s' % self.media_path)
      name = os.path.splitext(self.media_path)[0]
      L = []

      # search as /path/to/media/name*.{supported extension}
      p = name + '*.*'
      L = [ f for f in glob.glob(p) if f.lower().endswith(FORMATS) ]
      L.sort(key=len)

      # search in /userconfig/subtitles/md5_*.{supported extension}
      p = os.path.join(utils.user_conf_dir, 'subtitles', self.media_md5 + '_*.*')
      L += [ f for f in glob.glob(p) if f.lower().endswith(FORMATS) ]

      for f in L: DBG('Found %s' % f)
      return L

   def file_set(self, fname):
      self.clear()
      self.items = []
      self.current_item = None
      self.current_file = None

      if fname is not None:
         self.parse_sub(fname)
         if self.items:
            self.current_file = fname

            name = os.path.basename(fname)
            txt = '<title>%s</title><br>%s' % (_('Subtitles'),
                  name[33:] if fname.startswith(utils.user_conf_dir) else name)
            EmcNotify(txt, icon='icon/subs') 

   def delete(self):
      DBG('Cleanup')
      self.file_set(None)

   def parse_sub(self, fname):
      LOG('Loading subs from file: %s' % fname)

      # read from file using the wanted encoding
      full_text = read_file_with_encodings(fname, self.encodings)
      if full_text is None:
         LOG('Failed to read the sub: %s' % fname)
         return

      # parse the text using the correct parser
      name, ext = os.path.splitext(fname)
      ext = ext.lower()
      if ext in PARSERS.keys():
         parser = PARSERS.get(ext)
         self.items = parser(full_text)

   def item_apply(self, item):
      if item != self.current_item:
         gui.text_set('videoplayer.subs', item.text)
         self.current_item = item

   def clear(self):
      gui.text_set('videoplayer.subs', '')

   def update(self, pos):
      # subtitles loaded ?
      if self.current_file is None:
         return

      pos -= self.delay / 1000.0

      # current item is still valid ?
      item = self.current_item
      if item and item.start < pos < item.end:
         DBG('[%.3f] item %d still valid' % (pos, item.idx))
         return

      # next item valid ?
      if item and (item.idx + 1) < len(self.items):
         next_item = self.items[item.idx + 1]
         if item.end < pos < next_item.start:
            DBG('[%.3f] item %d is ended' % (pos, item.idx))
            self.clear()
            return
         elif next_item.start < pos < next_item.end:
            DBG('[%.3f] item %d is starting now' % (pos, next_item.idx))
            self.item_apply(next_item)
            return

      # fallback: search all the items (TODO optimize using a binary search)
      DBG('[%.3f] FALLBACK' % (pos))
      for item in self.items:
         if item.start < pos < item.end:
            self.item_apply(item)
            return
         if item.end > pos:
            self.clear()
            return

      DBG('[%.3f] FALLBACK FAILED' % (pos))
      self.clear()


class Opensubtitles(object):
   """ OpenSubtitles API implementation.

   Check the official API documentation at:
   http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC

   """
   OPENSUBTITLES_SERVER = 'http://api.opensubtitles.org/xml-rpc'
   # USER_AGENT = 'OS Test User Agent'
   USER_AGENT = 'Emotion Media Center v' + emc_version

   def __init__ (self, url, done_cb=None):
      self.dialog = None
      self.token = None
      self.results = []
      self.done_cb = done_cb
      self.oso_user = ini.get('subtitles', 'opensubtitles_user')
      self.oso_pass = ini.get('subtitles', 'opensubtitles_pass')
      self.langs2 = ini.get_string_list('subtitles', 'langs')
      self.langs3 = [ utils.iso639_1_to_5(l) for l in self.langs2 ]
      self.path = utils.url2path(url)
      self.size = os.path.getsize(self.path)
      self.hash = self.calc_hash()
      self.xmlrpc = ServerProxy(self.OPENSUBTITLES_SERVER, allow_none=True)

      self.build_wait_dialog(_('Searching subtitles'))
      self.search_in_a_thread()

   def calc_hash(self):
      """'Original from: http://goo.gl/qqfM0 """
      longlongformat = 'q' # long long
      bytesize = struct.calcsize(longlongformat)

      try:
         f = open(self.path, "rb")
      except(IOError):
         return "IOError"

      hash = self.size

      if self.size < 65536 * 2:
         return "SizeError"

      for x in range(int(65536 / bytesize)):
         buffer = f.read(bytesize)
         (l_value, ) = struct.unpack(longlongformat, buffer)
         hash += l_value
         hash = hash & 0xFFFFFFFFFFFFFFFF # to remain as 64bit number

      f.seek(max(0, self.size - 65536), 0)
      for x in range(int(65536 / bytesize)):
         buffer = f.read(bytesize)
         (l_value, ) = struct.unpack(longlongformat, buffer)
         hash += l_value
         hash = hash & 0xFFFFFFFFFFFFFFFF

      f.close()
      return "%016x" % hash

   def get_from_data_or_none(self, data, key):
      if data:
         status = data.get('status').split()[0]
         return data.get(key) if status == '200' else None

   def search_in_a_thread(self):
      self._thread_finished = False
      self._thread_error = None
      ecore.Timer(0.1, self.check_search_done)
      threading.Thread(target=self.perform_search).start()

   def perform_login(self):
      try:
         data = self.xmlrpc.LogIn(self.oso_user, self.oso_pass,
                                  self.langs2[0], self.USER_AGENT)
         assert data.get('status').split()[0] == '200'
         self.token = self.get_from_data_or_none(data, 'token')
      except:
         self._thread_error = _('Login failed')

   def perform_search(self):
      if self.token is None:
         self.perform_login()

      if self.token is None or self.hash is None:
         self._thread_finished = True
         return

      try:
         data = self.xmlrpc.SearchSubtitles(self.token, [{
                                       'sublanguageid': ','.join(self.langs3),
                                       'moviehash': self.hash,
                                       'moviebytesize': self.size }])
      except:
         self._thread_error = _('Search failed')
      else:
         data = self.get_from_data_or_none(data, 'data')
         if data:
            for sub in data:
               if '.' + sub['SubFormat'] not in FORMATS: continue
               if 'SubBad' in sub and sub['SubBad'] != '0': continue
               for key in ('SubDownloadsCnt', 'SubRating'):
                  if key in sub and sub[key]:
                     sub[key] = float(sub[key])
               self.results.append(sub)

      self._thread_finished = True

   def check_search_done(self):
      if self._thread_finished == False:
         return ecore.ECORE_CALLBACK_RENEW

      self.dialog.delete()
      if self._thread_error:
         EmcDialog(style='error', title='Opensubtitles.org',
                   text=self._thread_error)
      elif not self.results:
         EmcDialog(style='info', title='Opensubtitles.org',
            text=_('No results found for languages: %s') % ' '.join(self.langs3))
      else:
         self.build_result_dialog()

      return ecore.ECORE_CALLBACK_CANCEL

   def build_wait_dialog(self, title):
      self.dialog = EmcDialog(style='minimal', spinner=True, title=title,
                              content=gui.load_image('osdo_logo.png'))

   def build_result_dialog(self):
      txt = '%s<br>Size: %s<br>Hash: %s' % (self.path, self.size, self.hash)
      self.dialog = EmcDialog(title='Opensubtitles.org', style='list',
                              done_cb=self.download_in_a_thread)
      self.dialog.button_add(_('Download'), self.download_in_a_thread,
                             icon='icon/download')

      for sub in sorted(self.results, reverse=True,
               key=itemgetter('LanguageName', 'SubRating', 'SubDownloadsCnt')):
         txt = '[%s] %s, from user: %s, rating: %.1f, downloads: %.0f' % \
               (sub['SubFormat'].upper(), sub['LanguageName'],
                sub['UserNickName'] or _('Unknown'), sub['SubRating'],
                sub['SubDownloadsCnt'])
         item = self.dialog.list_item_append(txt, 'icon/subs')
         item.data['sub'] = sub

   def download_in_a_thread(self, btn):
      item = self.dialog.list_item_selected_get()
      sub = item.data['sub']

      self.dialog.delete()
      self.build_wait_dialog(_('Downloading subtitles'))

      self._thread_finished = False
      self._thread_error = None
      ecore.Timer(0.1, self.check_download_done)
      threading.Thread(target=self.perform_download, args=(sub,)).start()

   def perform_download(self, sub):
      try:
         res = self.xmlrpc.DownloadSubtitles(self.token,
                                             [ sub['IDSubtitleFile'] ],
                                             { 'subencoding':'utf8' } )
         data = res['data'][0]['data']
      except:
         self._thread_error = _('Download failed')
         self._thread_finished = True
         return

      try:
         text = zlib.decompress(base64.b64decode(data), 47)
         md5 = utils.md5(self.path)
         fname = '%s_%s_001.%s' % (md5, sub['ISO639'], sub['SubFormat'])
         full_path = os.path.join(utils.user_conf_dir, 'subtitles', fname)
         full_path = utils.ensure_file_not_exists(full_path)

         with codecs.open(full_path, 'w', 'utf8') as f:
            f.write(text.decode('utf8'))

         self._downloaded_path = full_path
      except:
         self._thread_error = _('Decode failed')

      self._thread_finished = True

   def check_download_done(self):
      if self._thread_finished == False:
         return ecore.ECORE_CALLBACK_RENEW

      self.dialog.delete()
      if self._thread_error:
         EmcDialog(style='error', title='Opensubtitles.org',
                   text=self._thread_error)
      else:
         if callable(self.done_cb):
            self.done_cb(self._downloaded_path)

      return ecore.ECORE_CALLBACK_CANCEL
