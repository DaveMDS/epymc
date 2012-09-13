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

import sys, urllib2, re
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
   content = urllib2.urlopen(req)
   data = content.read()
   content.close()
   return data


# this is the first page, show fixed categories
if STATE == 0:
   addItem(69,'A Random Video', 'http://fantasti.cc/random.php?v=1')
   addItem(1, 'Popular today', 'http://fantasti.cc/videos/popular/today', action=ACT_FOLDER)
   addItem(1, 'Popular this week', 'http://fantasti.cc/videos/popular/7days', action=ACT_FOLDER)
   addItem(1, 'Popular this month', 'http://fantasti.cc/videos/popular/31days', action=ACT_FOLDER)
   addItem(1, 'Popular all time', 'http://fantasti.cc/videos/popular/all_time', action=ACT_FOLDER)
   addItem(1, 'Popular made popular', 'http://fantasti.cc/videos/popular/made_popular', action=ACT_FOLDER)

   addItem(2, 'Collections - Most Viewed', 'http://fantasti.cc/videos/collections/most_viewed/7days', action=ACT_FOLDER)
   addItem(2, 'Collections - Top Rated', 'http://fantasti.cc/videos/collections/top_rated/7days', action=ACT_FOLDER)
   addItem(2, 'Collections - Most Discussed', 'http://fantasti.cc/videos/collections/most_discussed/7days', action=ACT_FOLDER)
   addItem(2, 'Collections - Top Favorites', 'http://fantasti.cc/videos/collections/top_favorites/7days', action=ACT_FOLDER)
   addItem(2, 'Collections - Popular', 'http://fantasti.cc/videos/collections/popular/7days', action=ACT_FOLDER)


# handle a page with a list of videos (popular videos)
elif STATE == 1:
   data = open_url(URL)
   soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)

   try:
      entry_image = soup.findAll('div', attrs = {'class' : 'entry_image'})
      for div in entry_image:
         for a in div.findAll('a'):
            if a['href'].startswith('/videos'):
               url = a['href']
               thumb = a('img')[0]['src']
               for title in div.parent.findAll('a', attrs = {'class' : 'title'}):
                  title = title.contents[0]
                  # print title, url, thumb
                  addItem(69, title, 'http://fantasti.cc' + url, poster=thumb)

      page = re.search('(\d+)$', URL)
      if page:
         page = page.group(0)
         url = URL[0:-len(page)] + str(int(page) + 1)
      else:
         url = URL + '/page_2'
      addItem(1, 'More items...', url, action=ACT_MORE)
   except:
      pass

# handle a page with collections list
elif STATE == 2:
   try:
      data = open_url(URL)
      soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)

      loop_div = soup.find('div', attrs = {'id' : 'loop'})
      for box in loop_div.findAll('div', recursive=False):
         NUM_VIDS = box.table.tr.findAll('td')[1].contents[0]
         NUM_VIDS = re.compile('([0-9]+)').search(NUM_VIDS).group(1) 
         TITLE = box.find('a').contents[0]
         TITLE = '%s (%s vids)' % (TITLE, NUM_VIDS)
         THUMB = box.find('a', recursive=False).img['src']
         URL = box.find('a')['href']
         # print TITLE, URL, THUMB
         addItem(3, TITLE, 'http://fantasti.cc/' + URL, poster=THUMB)
   except:
      exit()

# handle a page with the videos of a given collection
elif STATE == 3:
   try:
      data = open_url(URL)
      soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)

      for div in soup.findAll('div', attrs = {'class': 'HoldPhotos'}):
         TITLE = div.p.a['title']
         URL = div.p.a['href']
         THUMB = div.p.a.img['src']
         # print TITLE, URL, THUMB
         addItem(69, TITLE, 'http://fantasti.cc' + URL, poster=THUMB)
   except:
      exit()



# read a page with a single video and play the video
elif STATE == 69:
   try:
      html = open_url(URL)

      if "xvideos" in URL: # BROKEN !!
         match = re.compile('(http://www.xvideos.com/.+?)"').findall(html)
         html = open_url(match[0])
         match = re.compile('flv_url=(.+?)&amp').findall(html)
         fetchurl = urllib.unquote(match[0])
         playUrl(fetchurl)

      elif "pornhub" in URL: # untested
         match = re.compile('href="([^"]+viewkey[^"]+)"').findall(html)
         html = open_url(match[0])
         match = re.compile('"video_url":"([^"]+)"').findall(html)
         fetchurl = urllib2.unquote(match[0])
         playUrl(fetchurl)

      elif 'redtube' in URL: # untested
         match = re.compile('(http://www.redtube.com/.+?)"').findall(html)
         html = open_url(match[0])
         match = re.compile('flv_h264_url=(.+?)"').findall(html)
         fetchurl = urllib.unquote(match[0])
         playUrl(fetchurl)

      elif "xhamster" in URL: # OK
         match = re.compile('xhamster.com/movies/(.+?)/').findall(html)
         html = open_url('http://xhamster.com/xembed.php?video=%s' % match[0])
         match = re.compile("srv=(.+?)&image").findall(html)
         fetchurl = match[0].replace('&file', '/key')
         playUrl(fetchurl)

   except:
      exit()
