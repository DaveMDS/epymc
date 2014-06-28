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

import os, sys, re
from bs4 import BeautifulSoup

from epymc.extapi.onlinevideo import api_version, state_get, \
   fetch_url, play_url, item_add, call_ydl, local_resource, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:27.0) Gecko/20100101 Firefox/27.0'}
vimeo_base = 'http://vimeo.com'


ST_HOME = 0
ST_SEARCH = 1
ST_SEARCH_MORE = 2
ST_PLAY = 10


STATE, URL = state_get()


################################################################################
# home page
################################################################################
if STATE == ST_HOME:
   item_add(ST_SEARCH, 'Search videos', 'search', None, action=ACT_SEARCH)


################################################################################
# search results
################################################################################
elif STATE in (ST_SEARCH, ST_SEARCH_MORE):
   
   if STATE == ST_SEARCH:
      # search query in place of the url
      URL = '{}/search/sort:relevant/format:detail?q={}'.format(vimeo_base, URL)

   soup = fetch_url(URL, headers=headers, parser='bs4')
   for vid in soup.find('ol', class_='browse_videos').findAll('li', recursive=False):
      url = vimeo_base + vid.a['href']
      title = vid.find('p', class_='title').get_text(strip=True)
      thumb = vid.find('img', class_='thumbnail')['src'].replace('150x84', '590x332')
      info = ''

      try:
         duration = vid.find('div', class_='duration').get_text()
         info += u'<title>Duration: </title>{}<br>'.format(duration)
      except: pass

      try:
         user = vid.find('p', class_='meta').a.get_text()
         time = vid.find('p', class_='meta').time.get_text()
         info += u'<title>User: </title>{}<br>' \
                  '<title>Uploaded: </title>{}<br>'.format(user, time)
      except: pass

      try:
         plays = vid.find('span', class_='plays').get_text()
         likes = vid.find('span', class_='likes').get_text()
         comments = vid.find('span', class_='comments').get_text()
         info += u'<title>Counts: </title>{} - {} - {}<br>' \
                  .format(plays, likes, comments)
      except: pass

      try:
         descr = vid.find('p', class_='description').get_text(strip=True)
         info += u'<br>{}'.format(descr)
      except: pass

      item_add(ST_PLAY, title, url, poster=thumb, info=info)

   # more items...
   try:
      url = vimeo_base + soup.find('a', rel='next')['href']
      item_add(ST_SEARCH_MORE, 'More results...', url, icon='icon/next', action=ACT_MORE)
   except:
      pass


################################################################################
# play a video using youtube-dl to get the real url   \o/
################################################################################
elif STATE == ST_PLAY:
   play_url(call_ydl(URL))
   
