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

import os, sys, urllib2, json, subprocess
from bs4 import BeautifulSoup
from urlparse import parse_qs
from urllib import urlencode


api_version = 4

ACT_NONE = 0
ACT_FOLDER = 1
ACT_MORE = 2
ACT_PLAY = 3
ACT_SEARCH = 4

def state_get():
    return int(sys.argv[1]), sys.argv[2]

def item_add(next_state, label, url, info=None, icon=None, poster=None, action=ACT_NONE):
   """ TODO doc """
   print((next_state, label, url, info, icon, poster, action))

def play_url(url):
   """ TODO doc """
   print('PLAY!' + url)

def local_resource(_file_, res):
   return os.path.join(os.path.dirname(_file_), res)

def fetch_url(url, headers=None, parser=None):
   """ TODO doc """

   if headers is not None:
      req = urllib2.Request(url, headers=headers)
   else:
      req = urllib2.Request(url)
   f = urllib2.urlopen(req)
   data = f.read()
   f.close()

   if parser == 'json':
      data = json.loads(data)
   elif parser == 'bs4':
      data = BeautifulSoup(data)
   elif parser == 'querystr':
      data = parse_qs(data)

   return data

def call_ydl(url):
   """ TODO doc """
   ydl = os.path.join(os.path.dirname(__file__), 'youtube-dl')
   p = subprocess.Popen([ydl, '--get-url', url], stdout=subprocess.PIPE)
   out, err = p.communicate()
   return out

def url_encode(params):
   """ TODO doc """
   return urlencode(params)

def seconds_to_duration(seconds):
   """ TODO doc """
   seconds = int(seconds)
   h = int(seconds / 3600)
   m = int(seconds / 60) % 60
   s = int(seconds % 60)
   if h > 0:
      return "%d:%02d:%02d" % (h,m,s)
   else:
      return "%d:%02d" % (m,s)

def translate_iso_date(iso_date):
   """ TODO doc """
   from dateutil.parser import parse as date_parse
   from dateutil.relativedelta import relativedelta
   import datetime
   import pytz

   dt = date_parse(iso_date)
   today = datetime.datetime.now(pytz.utc)
   delta = relativedelta(today, dt)

   if delta.years > 1:
      return '{} years ago'.format(delta.years)
   elif delta.years > 0:
      return '1 year ago'
   elif delta.months > 1:
      return '{} months ago'.format(delta.months)
   elif delta.months > 0:
      return '1 month ago'
   elif delta.days > 1:
      return '{} days ago'.format(delta.days)
   elif delta.days > 0:
      return '1 day ago'
   else:
      return '{} hours ago'.format(delta.hours)

