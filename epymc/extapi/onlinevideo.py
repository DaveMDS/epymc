#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2014 Davide Andreoli <dave@gurumeditation.it>
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

import os, sys, json, subprocess, re
from datetime import datetime
from bs4 import BeautifulSoup

try:
   # py3
   import urllib.request as urllib2
   from urllib.parse import parse_qs
   from urllib.parse import urlencode
except:
   # py2
   import urllib2
   from urlparse import parse_qs
   from urllib import urlencode


api_version = 4

ACT_NONE = 0
ACT_FOLDER = 1
ACT_MORE = 2
ACT_PLAY = 3
ACT_SEARCH = 4

py3 = (sys.version_info[0] >= 3)

def state_get():
   """ Get the state (and the url) of the current running scraper process """
   return int(sys.argv[1]), sys.argv[2]

def item_add(next_state, label, url, info=None, icon=None, poster=None, action=ACT_NONE):
   """ Add an item to the current page """
   print((next_state, label, url, info, icon, poster, action))

def play_url(url):
   """ Tell EpyMC to start the playback of the given url """
   if py3:
      print('PLAY!' + url.decode('utf8'))
   else:
      print('PLAY!' + url)

def local_resource(_file_, res):
   """ Get the full path of a resouce included with the scraper """
   return os.path.join(os.path.dirname(_file_), res)

def fetch_url(url, headers=None, parser=None):
   """
   Download the given url and return the page data, optionally parsed.

   Args:
      headers: dict of headers to send with the request
      parser: can be one of json, bs4, querystr

   Return:
      The downloaded data, optionally parsed if parser is given

   """
   if headers is not None:
      req = urllib2.Request(url, headers=headers)
   else:
      req = urllib2.Request(url)

   f = urllib2.urlopen(req)
   data = f.read()
   f.close()

   # in py3 urlopen return a byte obj, so we need to encode it
   if py3: data = data.decode('utf8')

   if parser == 'json':
      data = json.loads(data)
   elif parser == 'bs4':
      data = BeautifulSoup(data)
   elif parser == 'querystr':
      data = parse_qs(data)

   return data

def call_ydl(url):
   """ Call youtube-dl with the given url and return the direct video url """
   ydl = os.path.join(os.path.dirname(__file__), 'youtube-dl')
   p = subprocess.Popen([ydl, '--get-url', url], stdout=subprocess.PIPE)
   out, err = p.communicate()
   return out

def url_encode(params):
   """
   Encode a dictionary as an url query str.

   Args:
      params: dictionary of key/values to encode
              ex: {'page': 2, 'filter': 'myfilter'}
   
   Returns:
      A string suitable to use in url params.
      ex: "page=2&filter=myfilter"

   """
   return urlencode(params)

def seconds_to_duration(seconds):
   """Convert the number of seconds in a readable duration """
   seconds = int(seconds)
   h = int(seconds / 3600)
   m = int(seconds / 60) % 60
   s = int(seconds % 60)
   if h > 0:
      return "%d:%02d:%02d" % (h,m,s)
   else:
      return "%d:%02d" % (m,s)

def relative_date(date):
   """
   Return a human readable relative date. Date can be a datetime obj or
   an iso date string (like: "2013-08-14T22:13:52+00:00") with or without the
   timezone information.
   """
   if not isinstance(date, datetime):
      try:
         L = map(int, re.split('[^\d]', date))
         if len(L) > 6: L = L[0:6]
         date = datetime(*L)
      except:
         return date

   delta = datetime.now() - date
   if delta.days > 365 * 2:
      return '{} years ago'.format(delta.days / 365)
   elif delta.days > 365:
      return '1 year ago'
   elif delta.days > 30 * 2:
      return '{} months ago'.format(delta.days / 30)
   elif delta.days > 30:
      return '1 month ago'
   elif delta.days > 7 * 2:
      return '{} weeks ago'.format(delta.days / 7)
   elif delta.days > 7:
      return '1 week ago'
   elif delta.days > 1:
      return '{} days ago'.format(delta.days)
   elif delta.days > 0:
      return 'yesterday'
   elif delta.seconds > 3600 * 2:
      return '{} hours ago'.format(delta.seconds / 3600)
   elif delta.seconds > 3600:
      return '1 hour ago'
   elif delta.seconds > 60 * 2:
      return '{} minutes ago'.format(delta.seconds / 60)
   else:
      return '1 minute ago'

