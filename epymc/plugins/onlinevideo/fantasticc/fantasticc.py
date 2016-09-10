#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2016 Davide Andreoli <dave@gurumeditation.it>
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

from __future__ import absolute_import, print_function, unicode_literals, division

import re

from epymc.extapi.onlinevideo import api_version, state_get, \
   fetch_url, play_url, item_add, call_ydl, report_error, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


url_base = 'http://fantasti.cc'

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

   item_add(ST_VIDEO_LIST, 'Upcoming video', url_base + '/videos/upcoming', action=ACT_FOLDER)

   item_add(ST_CATEGORIES_LIST, 'Categories', url_base + '/category', action=ACT_FOLDER)
   
   item_add(ST_VIDEO_LIST, 'Popular today', url_base + '/videos/popular/today', action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Popular this week', url_base + '/videos/popular/7days', action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Popular this month', url_base + '/videos/popular/31days', action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Popular all time', url_base + '/videos/popular/all_time', action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Popular made popular', url_base + '/videos/popular/made_popular', action=ACT_FOLDER)

   item_add(ST_COLLECTION_LIST, 'Collections - Popular', url_base + '/videos/collections/popular/31days', action=ACT_FOLDER)
   item_add(ST_COLLECTION_LIST, 'Collections - Top Rated', url_base + '/videos/collections/top_rated/31days', action=ACT_FOLDER)
   item_add(ST_COLLECTION_LIST, 'Collections - Most Viewed', url_base + '/videos/collections/most_viewed/31days', action=ACT_FOLDER)
   item_add(ST_COLLECTION_LIST, 'Collections - Most Discussed', url_base + '/videos/collections/most_discussed/31days', action=ACT_FOLDER)
   item_add(ST_COLLECTION_LIST, 'Collections - Top Favorites', url_base + '/videos/collections/top_favorites/31days', action=ACT_FOLDER)
   


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
      item_add(ST_VIDEO_LIST, 'More items...', url, action=ACT_MORE)
   except:
      pass


# handle a page with collections list
elif STATE == ST_COLLECTION_LIST:
   soup = fetch_url(URL, parser='bs4')

   for div in soup.findAll('div', class_='submitted-videos'):
      num_vids = div.find('div', class_='counter-right').string
      num_vids = re.compile('([0-9]+)').search(num_vids).group(1)
      if int(num_vids) < 1:
         continue
      title = div.find('a', class_='clnk').string
      title = '%s (%s vids)' % (title, num_vids)
      thumb = div.find('div', class_='item').find('a')['style']
      thumb = thumb.split('(', 1)[1].split(')')[0]
      url = url_base + div.find('a', class_='clnk')['href']
      item_add(ST_COLLECTION_VIDEO_LIST, title, url, poster=thumb)

   # more items...
   try:
      url = 'http://fantasti.cc/' + soup.find('a', text='next >>')['href']
      item_add(ST_COLLECTION_LIST, 'More items...', url, action=ACT_MORE)
   except:
      pass


# handle a page with the videos of a given collection
elif STATE == ST_COLLECTION_VIDEO_LIST:
   soup = fetch_url(URL, parser='bs4')

   for div in soup.find_all('div', class_='submitted-video-item'):
      title = div.find('div', class_='submitted-video__name').string
      thumb = div.img['src']
      url = url_base + div.find('a', class_='submitted-video-open')['href']
      item_add(ST_PLAY, title, url, poster=thumb)

   # more items... (TODO this do not work)
   # try:
      # url = 'http://fantasti.cc/' + soup.find('a', text='next >>')['href']
      # item_add(ST_COLLECTION_VIDEO_LIST, 'More items...', url, action=ACT_MORE)
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
      item_add(ST_SEARCH_RES, 'More items...', url, action=ACT_MORE)
   except:
      pass


# handle the list of categories
elif STATE == ST_CATEGORIES_LIST:
   soup = fetch_url(URL, parser='bs4')

   for div in soup.findAll('div', class_='content-block-category'):
      name = div.find('span', class_='category-name').string
      url = url_base + div.find('a')['href'] + 'videos/'
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
