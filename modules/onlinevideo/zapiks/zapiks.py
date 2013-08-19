#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2013 Davide Andreoli <dave@gurumeditation.it>
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

import os, sys, urllib2
from BeautifulSoup import BeautifulSoup

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
   req.addheaders = [('Referer', 'http://www.zapiks.com'), (AGENT)]
   content = urllib2.urlopen(req)
   data = content.read()
   content.close()
   return data

# this is the first page, show fixed categories
if STATE == 0:
   b = 'http://www.zapiks.com/'
   u = '/popular_1.php'
   d = os.path.dirname(__file__)
   addItem(1, 'Surf', b+'surf_'+u, poster=os.path.join(d,'surf.png'), action=ACT_FOLDER)
   addItem(1, 'Snowboard', b+'snowboard_'+u, poster=os.path.join(d,'snowboard.png'), action=ACT_FOLDER)
   addItem(1, 'Mountain Bike', b+'mountainbike_'+u, poster=os.path.join(d,'vtt.png'), action=ACT_FOLDER)
   addItem(1, 'Bmx', b+'bmx_'+u, poster=os.path.join(d,'bmx.png'), action=ACT_FOLDER)
   addItem(1, 'Skate', b+'skate_'+u, poster=os.path.join(d,'skate.png'), action=ACT_FOLDER)
   addItem(1, 'Ski', b+'ski_'+u, poster=os.path.join(d,'ski.png'), action=ACT_FOLDER)
   addItem(1, 'Kite', b+'kite_'+u, poster=os.path.join(d,'zapiks.png'), action=ACT_FOLDER)
   addItem(1, 'Wakeboard', b+'wake_'+u, poster=os.path.join(d,'zapiks.png'), action=ACT_FOLDER)
   addItem(1, 'Other', b+'other_'+u, poster=os.path.join(d,'zapiks.png'), action=ACT_FOLDER)


# the page for each category
elif STATE == 1:
   data = open_url(URL)
   soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)

   videos = soup.findAll('div', attrs={'class' : "media_thumbnail medium"})
   for video in videos:
      try:
         url = video('a')[0]['href']
         name = video('a')[0]['title']
         thumb = video('img')[0]['src']
         addItem(2, name, 'http://www.zapiks.com' + url, poster=thumb)
      except:
         pass
   try:
      nextPage = soup.find('span', attrs={'class' : "next"})('a')[1]['href']
      addItem(1, 'More items...', 'http://www.zapiks.com' + nextPage, icon='icon/next', action=ACT_MORE)
   except:
      pass


# extract the video link from the video page
elif STATE == 2:
   data = open_url(URL)
   soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
   vid = soup.find('link', attrs={'rel' : "video_src"})['href']
   vidId = vid[-5:]
   url2 = 'http://www.zapiks.com/view/index.php?file='+vidId+'&lang=fr'

   data = open_url(url2)
   soup = BeautifulSoup(data)
   video_url = soup.find('file').string
   playUrl(video_url)
