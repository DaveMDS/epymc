#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2015 Davide Andreoli <dave@gurumeditation.it>
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

# from __future__ import absolute_import, print_function

import os
import sys
import json
import subprocess
import re
import gettext
import locale
from datetime import datetime
from bs4 import BeautifulSoup

try:
   # py3
   from urllib.request import Request, urlopen
   from urllib.error import HTTPError, URLError
   from urllib.parse import parse_qs
   from urllib.parse import urlencode
except:
   # py2
   from urllib2 import Request, urlopen, HTTPError, URLError
   from urlparse import parse_qs
   from urllib import urlencode


api_version = 4

ACT_NONE = 0
ACT_FOLDER = 1
ACT_MORE = 2
ACT_PLAY = 3
ACT_SEARCH = 4

py3 = (sys.version_info[0] >= 3)


# install _() and ngettext() in the main namespace
localedir = os.path.join(os.path.dirname(__file__), '..', 'locale')
gettext.install('epymc', names='ngettext', localedir=localedir)

# set locale from the system config (used fe by strftime)
locale.setlocale(locale.LC_ALL, '')


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

def report_error(msg):
   print('ERR!' + msg)

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

   Raise:
      URLError(reason): in case of generic connection errors
      HTTPError(code, reason): in case of specific http errors

   """
   if headers is not None:
      req = Request(url, headers=headers)
   else:
      req = Request(url)

   f = urlopen(req)
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

def ydl_executable():
   return os.path.expanduser('~/.cache/epymc/youtube-dl')

def call_ydl(url):
   """ Call youtube-dl with the given url and return the direct video url """
   p = subprocess.Popen([ydl_executable(), '--get-url', url],
                        stdout=subprocess.PIPE)
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
         L = map(int, re.split('[^\d]', date)[0:6])
         date = datetime(*L)
      except:
         return date

   delta = datetime.now() - date
   if delta.days > 365:
      years = delta.days / 365
      return ngettext('%d year ago', '%d years ago', years) % years
   if delta.days > 30:
      months = delta.days / 30
      return ngettext('%d month ago', '%d months ago', months) % months
   if delta.days > 7:
      weeks = delta.days / 7
      return ngettext('%d week ago', '%d weeks ago', weeks) % weeks
   if delta.days > 0:
      return ngettext('%d day ago', '%d days ago', delta.days) % delta.days
   if delta.seconds > 3600:
      hours = delta.seconds / 3600
      return ngettext('%d hour ago', '%d hours ago', hours) % hours
   minutes = delta.seconds / 60
   return ngettext('%d minute ago', '%d minutes ago', minutes) % minutes

def format_date(date):
   """
   Return a localized date string (fe. 25/12/2015).
   Date can be a datetime obj or an integer timestamp.
   """
   if isinstance(date, int):
      date = datetime.fromtimestamp(date)
   return date.strftime('%x')
