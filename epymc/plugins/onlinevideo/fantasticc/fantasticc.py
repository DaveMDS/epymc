#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2015 Davide Andreoli <dave@gurumeditation.it>
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

import sys, re
from bs4 import BeautifulSoup

from epymc.extapi.onlinevideo import api_version, state_get, \
   fetch_url, play_url, item_add, call_ydl, report_error, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


ST_HOME = 0
ST_VIDEO_LIST = 1
ST_COLLECTION_LIST = 2
ST_COLLECTION_VIDEO_LIST = 3
ST_SEARCH = 4
ST_SEARCH_RES = 5
ST_CATEGORIES_LIST = 6
ST_PLAY = 69

STATE, URL = state_get()



# this is the first page, show fixed categories
if STATE == ST_HOME:
   # item_add(ST_PLAY,'A Random Video', 'http://fantasti.cc/random.php?v=1')
   item_add(ST_SEARCH, 'Search videos', 'search', action=ACT_SEARCH)

   item_add(ST_VIDEO_LIST, 'Upcoming video', 'http://fantasti.cc/videos/upcoming', action=ACT_FOLDER)

   item_add(ST_CATEGORIES_LIST, 'Categories', 'http://fantasti.cc/category', action=ACT_FOLDER)
   
   item_add(ST_VIDEO_LIST, 'Popular today', 'http://fantasti.cc/videos/popular/today', action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Popular this week', 'http://fantasti.cc/videos/popular/7days', action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Popular this month', 'http://fantasti.cc/videos/popular/31days', action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Popular all time', 'http://fantasti.cc/videos/popular/all_time', action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Popular made popular', 'http://fantasti.cc/videos/popular/made_popular', action=ACT_FOLDER)

   item_add(ST_COLLECTION_LIST, 'Collections - Popular', 'http://fantasti.cc/videos/collections/popular/31days', action=ACT_FOLDER)
   item_add(ST_COLLECTION_LIST, 'Collections - Top Rated', 'http://fantasti.cc/videos/collections/top_rated/31days', action=ACT_FOLDER)
   item_add(ST_COLLECTION_LIST, 'Collections - Most Viewed', 'http://fantasti.cc/videos/collections/most_viewed/31days', action=ACT_FOLDER)
   item_add(ST_COLLECTION_LIST, 'Collections - Most Discussed', 'http://fantasti.cc/videos/collections/most_discussed/31days', action=ACT_FOLDER)
   item_add(ST_COLLECTION_LIST, 'Collections - Top Favorites', 'http://fantasti.cc/videos/collections/top_favorites/31days', action=ACT_FOLDER)
   


# handle a page with a list of videos (popular videos)
elif STATE == ST_VIDEO_LIST:
   soup = fetch_url(URL, parser='bs4')

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
         info = '<title>%s</title><br>' \
                '<name>Duration:</name> %s<br>' \
                '<name>source</name> %s <name>/ uploaded %s</name><br>' \
                '<name>Tags:</name> %s' % \
                (title, duration, from_, uploaded, tags)
      except:
         info = None

      item_add(ST_PLAY, title, url, poster=thumb, info=info)
   
   # more items...
   try:
      url = 'http://fantasti.cc/' + soup.find('a', text='next >>')['href']
      item_add(ST_VIDEO_LIST, 'More items...', url, icon='icon/next', action=ACT_MORE)
   except:
      pass


# handle a page with collections list
elif STATE == ST_COLLECTION_LIST:
   soup = fetch_url(URL, parser='bs4')

   loop_div = soup.find('div', attrs = {'id' : 'loop'})
   for box in loop_div.findAll('div', recursive=False):
      NUM_VIDS = box.table.tr.findAll('td')[1].contents[0]
      NUM_VIDS = re.compile('([0-9]+)').search(NUM_VIDS).group(1) 
      TITLE = box.find('a').contents[0]
      TITLE = '%s (%s vids)' % (TITLE, NUM_VIDS)
      THUMB = box.find('a', recursive=False).img['src']
      URL = box.find('a')['href']
      # print(TITLE, URL, THUMB)
      item_add(ST_COLLECTION_VIDEO_LIST, TITLE, 'http://fantasti.cc/' + URL, poster=THUMB)

   # more items...
   try:
      url = 'http://fantasti.cc/' + soup.find('a', text='next >>')['href']
      item_add(ST_COLLECTION_LIST, 'More items...', url, icon='icon/next', action=ACT_MORE)
   except:
      pass


# handle a page with the videos of a given collection
elif STATE == ST_COLLECTION_VIDEO_LIST:
   soup = fetch_url(URL, parser='bs4')

   for div in soup.findAll('div', attrs = {'class': 'HoldPhotos'}):
      TITLE = div.p.a['title']
      URL = div.p.a['href']
      THUMB = div.p.a.img['src']
      # print(TITLE, URL, THUMB)
      item_add(ST_PLAY, TITLE, 'http://fantasti.cc' + URL, poster=THUMB)

   # more items... (TODO this do not work)
   # try:
      # url = 'http://fantasti.cc/' + soup.find('a', text='next >>')['href']
      # item_add(ST_COLLECTION_VIDEO_LIST, 'More items...', url, icon='icon/next', action=ACT_MORE)
   # except:
      # pass


# 4 handle the first search query (only page 1)
# 5 handle more search results (from page 2) (and the videos of categories)
elif STATE in (ST_SEARCH, ST_SEARCH_RES):
   if STATE == ST_SEARCH:
      URL = URL.replace(' ', '+')
      URL = 'http://fantasti.cc/search/' + URL + '/videos/'

   soup = fetch_url(URL, parser='bs4')

   for div in soup.findAll('div', class_='video_thumb'):
      title = div.find('h2', class_='video_h2').string
      url = div.find('a', class_='xxx')['href']
      thumb = div.find('img', class_='img_100')['src']

      duration = div.find('span', class_='v_lenght').string
      from_ = div.find('span', class_='video_tube').string
      info = '<title>%s</title><br>' \
             '<name>Duration: </name>%s<br>' \
             '<name>Source: </name>%s' % \
              (title, duration, from_)

      item_add(ST_PLAY, title, 'http://fantasti.cc' + url, poster=thumb, info=info)

   # more items...
   try:
      url = 'http://fantasti.cc/' + soup.find('a', text='next >>')['href']
      item_add(ST_SEARCH_RES, 'More items...', url, icon='icon/next', action=ACT_MORE)
   except:
      pass


# handle the list of categories
elif STATE == ST_CATEGORIES_LIST:
   soup = fetch_url(URL, parser='bs4')

   for a in soup.findAll('a', class_='wid-cloud'):
      name = a.string
      url = 'http://fantasti.cc/category/' + name.replace(' ', '+') + '/videos'
      item_add(ST_SEARCH_RES, name, url) 


# read a page with a single video and play the video
elif STATE == ST_PLAY:
   soup = fetch_url(URL, parser='bs4')
   link = soup.find('div', class_='video-wrap')['data-origin-source']
   url = call_ydl(link)
   if url:
      play_url(url)
   else:
      report_error('Video not found')
