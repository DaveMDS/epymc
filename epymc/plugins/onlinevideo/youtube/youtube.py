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


ytb_base = 'http://www.youtube.com'
api_base = 'http://gdata.youtube.com/feeds/api/standardfeeds/'
ytb_icon = local_resource(__file__, 'youtube.png')
ITEMS_PER_PAGE = 50

ST_HOME = 0
ST_PLAY = 1
ST_VIDEO_LIST_JSONC = 2
ST_SEARCH_JSONC = 3
ST_CHN_CATEGORIES = 10
ST_CHN_CHANNELS = 11
ST_CHN_VIDEOS = 12


STATE, URL = state_get()


def seconds_to_time_string(seconds):
   seconds = int(seconds)
   h = int(seconds / 3600)
   m = int(seconds / 60) % 60
   s = int(seconds % 60)
   if h > 0:
      return "%d:%02d:%02d" % (h,m,s)
   else:
      return "%d:%02d" % (m,s)


# this is the first page, show fixed categories
if STATE == ST_HOME:
   item_add(ST_SEARCH_JSONC, 'Search videos', 'search', None, action=ACT_SEARCH)
   item_add(ST_CHN_CATEGORIES, 'Channels by categories',
            ytb_base+'/channels', None, action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST_JSONC, 'Top rated',
            api_base+'top_rated?v=2&alt=jsonc&max-results='+str(ITEMS_PER_PAGE),
            None, action=ACT_FOLDER)


###############################################################################
### youtube site scraper ######################################################
###############################################################################

# 1. show the list of channels categories
elif STATE == ST_CHN_CATEGORIES:
   soup = fetch_url(URL, parser='bs4')
   for cat in soup.findAll('div', class_='yt-gb-shelf'):
      try:
         title = cat.find('span', class_='category-title').string
         href = cat.find('a', class_='category-title-link')['href']
         # thumb = cat.find('span', class_='yt-thumb-clip').img['src']

         video_count = cat.find('span', class_='channel-count').string
         info = u'<title>Channels: </title>{}<br>'.format(video_count)

         item_add(ST_CHN_CHANNELS, title, ytb_base+href, poster=ytb_icon, info=info)
      except:
         pass


# 2. show a list of channels in a given categories
elif STATE == ST_CHN_CHANNELS:
   soup = fetch_url(URL, parser='bs4')
   for cha in soup.findAll('div', class_='yt-gb-shelf-hero'):
      try:
         title_span = cha.find('span', class_='qualified-channel-title-text')
         href = title_span.a['href']
         title = title_span.a.string
         thumb = cha.find('span', class_='yt-thumb-clip').img['src']

         description = cha.find('p', class_='description').string.strip()
         info = u'{}<br>'.format(description)
         
         item_add(ST_CHN_VIDEOS, title, ytb_base+href+'/videos?flow=list&sort=dd',
                  poster=thumb, info=info)
      except:
         pass


# 3. show a list of videos in a given channel
elif STATE == ST_CHN_VIDEOS:
   soup = fetch_url(URL, parser='bs4')
   for item in soup.findAll('li', class_='channels-browse-content-list-item'):
      try:
         title_h3 = item.find('h3', class_='yt-lockup-title')
         href = title_h3.a['href']
         title = title_h3.a['title']
         thumb = 'http:' + item.find('span', class_='yt-thumb-clip').img['data-thumb']

         description = item.find('div', class_='yt-lockup-description')
         description = ''.join([s for s in description.stripped_strings])
         metas = item.find('div', class_='yt-lockup-meta').findAll('li')
         meta = ''
         for m in metas:
            meta += m.string + '<br>'
         info = u'{}<br>{}<br>'.format(meta, description)

         item_add(ST_PLAY, title, ytb_base+href, poster=thumb, info=info)
      except:
         pass


###############################################################################
### youtube api v2 (old and deprecated) #######################################
# https://developers.google.com/youtube/2.0/developers_guide_protocol
###############################################################################

# parse a list of video (jsonc)
elif STATE in (ST_VIDEO_LIST_JSONC, ST_SEARCH_JSONC):

   # STATE 4 = search query in place of the url
   if STATE == ST_SEARCH_JSONC:
      print "search for:" , URL
      URL = 'http://gdata.youtube.com/feeds/api/videos?q=%s&v=2&alt=jsonc&max-results=%d' % (URL, ITEMS_PER_PAGE)

   data = fetch_url(URL, parser='json')

   for item in data['data']['items']:
      try:
         # see https://developers.google.com/youtube/2.0/developers_guide_jsonc
         author = item['uploader']
         title = item['title']
         desc = item['description']
         rat_max = 5
         rat_avg = item['rating']
         duration = item['duration']
         videoid = item['id']
         viewed = item['viewCount']
         favorited = item['favoriteCount']
         likes = item['likeCount']
         published = item['uploaded']
         url = item['player']['default']
         # if '1' in item['content']:
         #    url = item['content']['5']
         # else:
         #    url = 'restricted'
         #    title += '(RES)'
         poster = item['thumbnail']['hqDefault']
         icon = item['thumbnail']['sqDefault']

         info = '<hilight>Author:</> %s<br>' \
                '<hilight>Published:</> %s<br>' \
                '<hilight>Duration:</> %s<br>' \
                '<hilight>Rating:</> %.1f/%d<br>' \
                '<hilight>Viewed:</> %s  <hilight>Likes: </>+%s<br>' \
                '%s' % \
                (author, published, 
                 seconds_to_time_string(duration),
                 rat_avg, rat_max, viewed, likes,
                 desc.replace('\r\n', '<br>'))

         item_add(ST_PLAY, title, url, info=info, icon=None, poster=poster)

      except:
         item_add(ST_HOME, 'error parsing data', None)

   total_items = data['data']['totalItems']
   start_index = data['data']['startIndex']

   # more items
   if start_index + ITEMS_PER_PAGE < total_items:
      if 'start-index' in URL:
         URL = re.sub('&start-index=[0-9]+', '', URL)
      URL += '&start-index=%d' % (start_index + ITEMS_PER_PAGE)
      item_add(ST_VIDEO_LIST_JSONC, 'more of the %d results...' % (total_items), URL, action=ACT_MORE)


# play a video using youtube-dl to get the real url   \o/
elif STATE == ST_PLAY:
   play_url(call_ydl(URL))


"""
   # now make the list of related videos
   print "ADSASDASDAS"
   url = 'http://gdata.youtube.com/feeds/api/videos/%s/related?v=2&alt=jsonc' % (video_id)
   # print url
   data = fetch_url(url, parser='json')
   for item in data['data']['items']:
      # print item
      # item_add(2, 'sug1', 'url')
      author = item['uploader']
      title = item['title']
      desc = item['description']
      duration = item['duration']
      videoid = item['id']
      url = item['player']['default']
      poster = item['thumbnail']['hqDefault']
      icon = item['thumbnail']['sqDefault']

      item_add(3, title, url, poster=poster)
"""
