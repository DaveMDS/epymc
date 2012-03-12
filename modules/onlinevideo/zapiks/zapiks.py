#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2012 Davide Andreoli <dave@gurumeditation.it>
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

# REFERENCE:
# From app: "cmd STATE URL"
# To app: (label,url,state,icon,is_folder)  one item per line
#  or
# To app: PLAY!http://bla.bla.bla/coolvideo.ext

import os, sys, urllib2
from BeautifulSoup import BeautifulSoup

AGENT='Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'

### API V.2  ###################################################################
STATUS = int(sys.argv[1])
URL = sys.argv[2]

def addItem(label, url, state, icon, action = 0):
   # actions: 0=none, 1=folder, 2=moreitems
   print((label, url, state, icon, action))

def playUrl(url):
   print 'PLAY!' + url
### API END  ###################################################################

# this is the first page, show fixed categories
if STATUS == 0:
   b = 'http://www.zapiks.com/'
   u = '/popular_1.php'
   d = os.path.dirname(__file__)
   addItem('Surf', b+'surf_'+u, 1, os.path.join(d,'surf.png'), True)
   addItem('Snowboard', b+'snowboard_'+u, 1, os.path.join(d,'snowboard.png'), True)
   addItem('Mountain Bike', b+'mountainbike_'+u, 1, os.path.join(d,'vtt.png'), True)
   addItem('Bmx', b+'bmx_'+u, 1, os.path.join(d,'bmx.png'), True)
   addItem('Skate', b+'skate_'+u, 1, os.path.join(d,'skate.png'), True)
   addItem('Ski', b+'ski_'+u, 1, os.path.join(d,'ski.png'), True)
   addItem('Kite', b+'kite_'+u, 1, os.path.join(d,'zapiks.png'), True)
   addItem('Wakeboard', b+'wake_'+u, 1, os.path.join(d,'zapiks.png'), True)
   addItem('Other', b+'other_'+u, 1, os.path.join(d,'zapiks.png'), True)


# the page for each category
elif STATUS == 1:
   req = urllib2.Request(URL)
   req.add_header('User-Agent', AGENT)
   response = urllib2.urlopen(req)
   link = response.read()
   soup = BeautifulSoup(link, convertEntities=BeautifulSoup.HTML_ENTITIES)
   response.close()
   videos = soup.findAll('div', attrs={'class' : "media_thumbnail medium"})
   for video in videos:
      try:
         url = video('a')[0]['href']
         name = video('a')[0]['title']
         thumb = video('img')[0]['src']
         addItem(name, 'http://www.zapiks.com' + url, 2, thumb)
      except:
         pass
   try:
      nextPage = soup.find('span', attrs={'class' : "next"})('a')[1]['href']
      addItem('Next page', 'http://www.zapiks.com' + nextPage, 1, 'icon/next', True)
   except:
      pass


# finally extract the video link from the page
elif STATUS == 2:
   req = urllib2.Request(URL)
   req.add_header('User-Agent', AGENT)
   response = urllib2.urlopen(req)
   link = response.read()
   response.close()
   soup = BeautifulSoup(link)
   vid = soup.find('link', attrs={'rel' : "video_src"})['href']
   vidId = vid[-5:]
   req = urllib2.Request('http://www.zapiks.com/view/index.php?file='+vidId+'&lang=fr')
   req.addheaders = [('Referer', 'http://www.zapiks.com'), (AGENT)]
   response = urllib2.urlopen(req)
   link = response.read()
   response.close()
   soup = BeautifulSoup(link)
   url = soup.find('file').string
   playUrl(url)
