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

import sys, urllib2, re
from bs4 import BeautifulSoup

AGENT='Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'

### API V.3  ###################################################################
STATE = int(sys.argv[1])
URL = sys.argv[2]

ACT_NONE = 0; ACT_FOLDER = 1; ACT_MORE = 2; ACT_PLAY = 3; ACT_SEARCH = 4

def addItem(next_state, label, url, info = None, icon = None, poster = None, action = ACT_NONE):
   print((next_state, label, url, info, icon, poster, action))

def playUrl(url):
   print('PLAY!' + url)

### API END  ###################################################################

def open_url(url):
   req = urllib2.Request(url)
   content = urllib2.urlopen(req)
   data = content.read()
   content.close()
   return data


# this is the first page, show fixed categories
if STATE == 0:
   # addItem(69,'A Random Video', 'http://fantasti.cc/random.php?v=1')
   addItem(4, 'Search videos', 'search', action=ACT_SEARCH)

   addItem(1, 'Upcoming video', 'http://fantasti.cc/videos/upcoming', action=ACT_FOLDER)

   addItem(6, 'Categories', 'http://fantasti.cc/category', action=ACT_FOLDER)
   
   addItem(1, 'Popular today', 'http://fantasti.cc/videos/popular/today', action=ACT_FOLDER)
   addItem(1, 'Popular this week', 'http://fantasti.cc/videos/popular/7days', action=ACT_FOLDER)
   addItem(1, 'Popular this month', 'http://fantasti.cc/videos/popular/31days', action=ACT_FOLDER)
   addItem(1, 'Popular all time', 'http://fantasti.cc/videos/popular/all_time', action=ACT_FOLDER)
   addItem(1, 'Popular made popular', 'http://fantasti.cc/videos/popular/made_popular', action=ACT_FOLDER)

   addItem(2, 'Collections - Popular', 'http://fantasti.cc/videos/collections/popular/31days', action=ACT_FOLDER)
   addItem(2, 'Collections - Top Rated', 'http://fantasti.cc/videos/collections/top_rated/31days', action=ACT_FOLDER)
   addItem(2, 'Collections - Most Viewed', 'http://fantasti.cc/videos/collections/most_viewed/31days', action=ACT_FOLDER)
   addItem(2, 'Collections - Most Discussed', 'http://fantasti.cc/videos/collections/most_discussed/31days', action=ACT_FOLDER)
   addItem(2, 'Collections - Top Favorites', 'http://fantasti.cc/videos/collections/top_favorites/31days', action=ACT_FOLDER)
   


# handle a page with a list of videos (popular videos)
elif STATE == 1:
   data = open_url(URL)
   soup = BeautifulSoup(data)

   loop = soup.findAll('div', class_='loop')
   for div in loop:
      title = div.find('a', class_='title').string
      thumb = div.find('img', class_='img_100')['src']
      url = 'http://fantasti.cc/' + div.find('a')['href']
      try:
         # what a mess for the info ...
         infos = div.find('span', style='font-size:11px;').get_text('|', strip=True).split('|')
         info1 = infos[0].split('\n')[0].strip()
         duration = info1.split('.')[0]
         uploaded = info1.split(':')[-1]
         from_ = infos[1]
         tags = ', '.join(infos[2:])
         info = '<title>Duration: </title>{}<br>' \
                '<title>Uploaded: </title>{}<br>' \
                '<title>From: </title>{}<br>' \
                '<title>Tags: </title>{}'.format(duration, uploaded, from_, tags)
         info = info
      except:
         info = None

      addItem(69, title, url, poster=thumb, info=info)
   
   # more items...
   try:
      url = 'http://fantasti.cc/' + soup.find('a', text='next >>')['href']
      addItem(1, 'More items...', url, icon='icon/next', action=ACT_MORE)
   except:
      pass


# handle a page with collections list
elif STATE == 2:
   data = open_url(URL)
   soup = BeautifulSoup(data)

   loop_div = soup.find('div', attrs = {'id' : 'loop'})
   for box in loop_div.findAll('div', recursive=False):
      NUM_VIDS = box.table.tr.findAll('td')[1].contents[0]
      NUM_VIDS = re.compile('([0-9]+)').search(NUM_VIDS).group(1) 
      TITLE = box.find('a').contents[0]
      TITLE = '%s (%s vids)' % (TITLE, NUM_VIDS)
      THUMB = box.find('a', recursive=False).img['src']
      URL = box.find('a')['href']
      # print(TITLE, URL, THUMB)
      addItem(3, TITLE, 'http://fantasti.cc/' + URL, poster=THUMB)

   # more items...
   try:
      url = 'http://fantasti.cc/' + soup.find('a', text='next >>')['href']
      addItem(2, 'More items...', url, icon='icon/next', action=ACT_MORE)
   except:
      pass


# handle a page with the videos of a given collection
elif STATE == 3:
   data = open_url(URL)
   soup = BeautifulSoup(data)

   for div in soup.findAll('div', attrs = {'class': 'HoldPhotos'}):
      TITLE = div.p.a['title']
      URL = div.p.a['href']
      THUMB = div.p.a.img['src']
      # print(TITLE, URL, THUMB)
      addItem(69, TITLE, 'http://fantasti.cc' + URL, poster=THUMB)

   # more items... (TODO this do not work)
   # try:
      # url = 'http://fantasti.cc/' + soup.find('a', text='next >>')['href']
      # addItem(3, 'More items...', url, icon='icon/next', action=ACT_MORE)
   # except:
      # pass


# 4 handle the first search query (only page 1)
# 5 handle more search results (from page 2) (and the videos of categories)
elif STATE in (4, 5):
   if STATE == 4:
      URL = URL.replace(' ', '+')
      URL = 'http://fantasti.cc/search/' + URL + '/videos/'

   html = open_url(URL)
   soup = BeautifulSoup(html)

   for div in soup.findAll('div', class_='video_thumb'):
      title = div.find('h2', class_='video_h2').string
      url = div.find('a', class_='xxx')['href']
      thumb = div.find('img', class_='img_100')['src']

      duration = div.find('span', class_='v_lenght').string
      from_ = div.find('span', class_='video_tube').string
      info = u'<title>Duration: </title>{}<br>' \
              '<title>From: </title>{}'.format(duration, from_)

      addItem(69, title, 'http://fantasti.cc' + url, poster=thumb, info=info)

   # more items...
   try:
      url = 'http://fantasti.cc/' + soup.find('a', text='next >>')['href']
      addItem(5, 'More items...', url, icon='icon/next', action=ACT_MORE)
   except:
      pass


# handle the list of categories
elif STATE == 6:
   html = open_url(URL)
   soup = BeautifulSoup(html)

   for a in soup.findAll('a', class_='wid-cloud'):
      name = a.string
      url = 'http://fantasti.cc/category/' + name.replace(' ', '+') + '/videos'
      addItem(5, name, url) 


# read a page with a single video and play the video
elif STATE == 69:

   html = open_url(URL)

   if "xvideos" in URL: # OK
      link = re.compile('(http://www.xvideos.com/.+?)"').findall(html)[0]
      html = open_url(link)
      fetchurl = re.compile('flv_url=(.+?)&').findall(html)[0]
      playUrl(urllib2.unquote(fetchurl))

   elif "pornhub" in URL: # BROKEN
      match = re.compile('href="([^"]+viewkey[^"]+)"').findall(html)
      html = open_url(match[0])
      match = re.compile('"video_url":"([^"]+)"').findall(html)
      fetchurl = urllib2.unquote(match[0])
      playUrl(fetchurl)

   elif 'redtube' in URL: # OK
      link = re.compile('(http://www.redtube.com/.+?)"').findall(html)[0]
      html = open_url(link)
      fetchurl = re.compile('flv_h264_url=(.+?)"').findall(html)[0]
      playUrl(urllib2.unquote(fetchurl))

   elif "xhamster" in URL: # OK
      vid = re.compile('xhamster.com/movies/(.+?)/').findall(html)[0]
      html = open_url('http://xhamster.com/xembed.php?video=%s' % vid)
      srv = re.compile("&srv=(.+?)&").findall(html)[0]
      fil = re.compile("&file=(.+?)&").findall(html)[0]
      fetchurl = urllib2.unquote(srv + '/key=' + fil)
      playUrl(fetchurl)

   elif 'you_porn' in URL: # OK
      link = re.compile('(http://www.youporn.com/watch/.+?)"').findall(html)[0]
      html = open_url(link)
      soup = BeautifulSoup(html)
      fetchurl = soup.find('video', id='player-html5')['src']
      playUrl(fetchurl)

   elif 'pornotube' in URL: # OK
      fetchurl = re.compile('"clip":"(.+?)"').findall(html)[0]
      playUrl(fetchurl)

   # elif 'hardsextube' in URL: # HardSexTube TODO

   # elif 'tube8' in URL: # Tube8 TODO

   # elif 'madthumbs' in URL: # MadThumbs TODO

   # elif 'spankwire' in URL: # SpankWire TODO
   
   # elif 'empflix' in URL: # Empflix TODO
      

   
      
