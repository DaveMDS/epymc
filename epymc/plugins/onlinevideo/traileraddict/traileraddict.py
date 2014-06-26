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

# CREDITS:
#  this is a rude copy from the xbmc addons by:
#      stacked <stacked.xbmc@gmail.com>
#  all the credits goes to him...thanks!


import re, hashlib
from bs4 import BeautifulSoup

from epymc.extapi.onlinevideo import api_version, user_agent, state_get, \
   fetch_url, play_url, item_add, call_ydl, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


ST_HOME = 0
ST_MOVIE_LIST = 2
ST_VIDEO_LIST = 4
ST_PLAY_VIDEO = 5

base = 'http://www.traileraddict.com'

STATE, URL = state_get()


# this is the first page
if STATE == ST_HOME:
   item_add(ST_MOVIE_LIST, 'Top Films','http://www.traileraddict.com/top150', action=ACT_FOLDER)
   item_add(ST_MOVIE_LIST, 'Coming Soon','http://www.traileraddict.com/comingsoon', action=ACT_FOLDER)
   item_add(ST_MOVIE_LIST, 'Out Now','http://www.traileraddict.com/outnow', action=ACT_FOLDER)


# ComingSoon/Top150/OutNow pages
elif STATE == ST_MOVIE_LIST:
   soup = fetch_url(URL, parser='bs4')
   movies = soup.find(id='featured_c').findAll('a', class_='m_title')
   for m in movies:
      title = m.contents[0]
      url = base + m['href']
      item_add(ST_VIDEO_LIST, title, url.encode('ascii'))


# list available trailers for a movie
elif STATE == ST_VIDEO_LIST:
   soup = fetch_url(URL, parser='bs4')

   try:
      poster = soup.find('a', attrs={'class': 'posterimgwrapper'}).find('img')['src']
      poster = 'http:' + poster
   except:
      poster = None

   videos = soup.find(id='featured_c').findAll('a', attrs={'class': 'm_title'})
   for v in videos:
      title = v.contents[0].strip()
      url = base + v['href']
      item_add(ST_PLAY_VIDEO, title, url.encode('ascii'), icon='icon/play', poster=poster)


# play video
elif STATE == ST_PLAY_VIDEO:

   # trailer id
   data = fetch_url(URL)
   tid = re.compile('<meta itemprop="embedUrl" content="http://www.traileraddict.com/emd/\d+\?id=(.+?)">').findall(data)[0]

   # token
   m = hashlib.md5()
   m.update(tid)
   token = m.hexdigest()[2:7]

   # info page
   url = '%s/js/flash/fv-secure.php?tid=%s&token=%s' % (base, tid, token)
   data = fetch_url(url, parser='querystr')
   url = data['fileurl'][0]
   # url = url.replace('%3A', ':').replace('%2F', '/').replace('%3F', '?').replace('%3D', '=').replace('%26', '&').replace('%2F', '//')
   play_url(url)
