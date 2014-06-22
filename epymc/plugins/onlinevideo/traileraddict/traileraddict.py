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


import os, sys, urllib2, re, hashlib
from bs4 import BeautifulSoup

AGENT='Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'

### API V.3  ###################################################################
STATE = int(sys.argv[1])
URL = sys.argv[2]

ACT_NONE = 0; ACT_FOLDER = 1; ACT_MORE = 2

def addItem(next_state, label, url, info = None, icon = None, poster = None, action = ACT_NONE):
   print((next_state, label, url, info, icon, poster, action))

def playUrl(url):
   print('PLAY!' + url)

### API END  ###################################################################

def open_url(url):
   req = urllib2.Request(url)
   req.addheaders = [(AGENT)]
   content = urllib2.urlopen(req)
   data = content.read()
   content.close()
   return data


# this is the first page
if STATE == 0:
   addItem(2, 'Top Films','http://www.traileraddict.com/top150', action=ACT_FOLDER)
   addItem(2, 'Coming Soon','http://www.traileraddict.com/comingsoon', action=ACT_FOLDER)
   addItem(2, 'Out Now','http://www.traileraddict.com/outnow', action=ACT_FOLDER)


# ComingSoon/Top150/OutNow pages
elif STATE == 2:
   data = open_url(URL)
   soup = BeautifulSoup(data)
   movies = soup.find(id='featured_c').findAll('a', attrs={'class':'m_title'})
   print movies
   for m in movies:
      title = m.contents[0]
      url = 'http://www.traileraddict.com' + m['href']
      addItem(4, title, url.encode('ascii'))


# list available trailers for a movie
elif STATE == 4:
   data = open_url(URL)
   soup = BeautifulSoup(data)

   try:
      poster = soup.find('a', attrs={'class': 'posterimgwrapper'}).find('img')['src']
      poster = 'http:' + poster
   except:
      poster = None

   videos = soup.find(id='featured_c').findAll('a', attrs={'class': 'm_title'})
   for v in videos:
      title = v.contents[0]
      url = 'http://www.traileraddict.com' + v['href']
      addItem(5, title, url.encode('ascii'), icon='icon/play', poster=poster)


# play video
elif STATE == 5:
   data = open_url(URL)

   # TrailerId
   tid = re.compile('<meta itemprop="embedUrl" content="http://www.traileraddict.com/emd/\d+\?id=(.+?)">').findall(data)[0]

   # Token
   m = hashlib.md5()
   m.update(tid)
   token = m.hexdigest()[2:7]

   url = 'http://www.traileraddict.com/js/flash/fv-secure.php?tid=%s&token=%s' % (tid, token)
   data = open_url(url)
   url = re.compile('fileurl=(.+?)\n&vidwidth', re.DOTALL).findall(data)[0]
   url = url.replace('%3A', ':').replace('%2F', '/').replace('%3F', '?').replace('%3D', '=').replace('%26', '&').replace('%2F', '//')
   playUrl(str(url))
