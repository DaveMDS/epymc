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

import os, sys, re, subprocess

from epymc.extapi.onlinevideo import \
   api_version, user_agent, state_get, \
   fetch_url, play_url, item_add, call_ydl, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


ITEMS_PER_PAGE = 50

STATE, URL = state_get()




# youtube api reference:
# https://developers.google.com/youtube/2.0/developers_guide_protocol




def seconds_to_time_string(seconds):
   seconds = int(seconds)
   h = int(seconds / 3600)
   m = int(seconds / 60) % 60
   s = int(seconds % 60)
   if h > 0:
      return "%d:%02d:%02d" % (h,m,s)
   else:
      return "%d:%02d" % (m,s)


CATS = ['Film', 'Autos', 'Music', 'Animals', 'Sports', 'Shortmov', 'Travel',
'Games', 'Videoblog', 'People', 'Comedy', 'Entertainment', 'News', 'Howto',
'Education', 'Tech', 'Nonprofit', 'Movies', 'Shows', 'Trailers']


# this is the first page, show fixed categories
if STATE == 0:
   # b = 'http://gdata.youtube.com/feeds/api/standardfeeds/IT/'
   std = 'http://gdata.youtube.com/feeds/api/standardfeeds/'
   e = 'v=2&alt=jsonc&max-results=' + str(ITEMS_PER_PAGE)
   item_add(4, 'Search videos', 'search', None, action=ACT_SEARCH)
   item_add(4, 'Search channels (TODO)', 'search', None, action=ACT_SEARCH)
   item_add(2, 'Categories :/', 'cats', None, action=ACT_FOLDER)
   item_add(1, 'Top rated', std+'top_rated?'+e, None, action=ACT_FOLDER)
   item_add(1, 'Top favorites', std+'top_favorites?'+e, None, action=ACT_FOLDER)
   item_add(1, 'Most shared', std+'most_shared?'+e, None, action=ACT_FOLDER)
   item_add(1, 'Most popular', std+'most_popular?'+e, None, action=ACT_FOLDER)
   # item_add(1, 'Most recent', std+'most_recent?'+e, None, action=ACT_FOLDER)
   item_add(1, 'Most discussed', std+'most_discussed?'+e, None, action=ACT_FOLDER)
   item_add(1, 'Most viewed', std+'most_viewed?'+e, None, action=ACT_FOLDER)
   


# show the list of categories
elif STATE == 2:
   std = 'http://gdata.youtube.com/feeds/api/standardfeeds/'
   e = 'v=2&alt=jsonc&max-results=' + str(ITEMS_PER_PAGE)
   for cat in CATS:
      url = '%stop_rated_%s?%s' % (std, cat, e)
      item_add(1, cat, url, None, action=ACT_FOLDER)


# parse a list of video (jsonc)
elif STATE == 1 or STATE == 4:

   # STATE 4 = search query in place of the url
   if STATE == 4:
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

         item_add(3, title, url, info=info, icon=None, poster=poster)

      except:
         item_add(0, 'error parsing data', None)

   total_items = data['data']['totalItems']
   start_index = data['data']['startIndex']

   # more items
   if start_index + ITEMS_PER_PAGE < total_items:
      if 'start-index' in URL:
         URL = re.sub('&start-index=[0-9]+', '', URL)
      URL += '&start-index=%d' % (start_index + ITEMS_PER_PAGE)
      item_add(1, 'more of the %d results...' % (total_items), URL, action=ACT_MORE)

 # try:
      # nextPage = soup.find('span', attrs={'class' : "next"})('a')[1]['href']
      # item_add(1, 'More items...', 'http://www.zapiks.com' + nextPage, icon='icon/next', action=ACT_MORE)
   # except:
      # pass


# parse a list of video (json)
elif STATE == 111: # __UNUSED__
   data = fetch_url(URL, parser='json')

   # see https://developers.google.com/youtube/2.0/developers_guide_jsonc
   for e in data['feed']['entry']:
      try:
         author = e['author'][0]['name']['$t']
         title = e['title']['$t']
         desc = e['media$group']['media$description']['$t']
         rat_max = e['gd$rating']['max']
         rat_avg = e['gd$rating']['average']
         duration = e['media$group']['yt$duration']['seconds']
         videoid = e['media$group']['yt$videoid']['$t']
         viewed = e['yt$statistics']['viewCount']
         favorited = e['yt$statistics']['favoriteCount']
         likes = e['yt$rating']['numLikes']
         dislikes = e['yt$rating']['numDislikes']
         published = e['published']['$t']

         for media in e['media$group']['media$content']:
            if media['medium'] == 'video' and media['expression'] == 'full':
               if media['yt$format'] == 1:
                  url = media['url']

         for t in e['media$group']['media$thumbnail']:
            if t['yt$name'] == 'default':
               icon = t['url']
            elif t['yt$name'] == 'hqdefault':
               poster = t['url']

         info = '<hilight>Author:</> %s<br>' \
                '<hilight>Published:</> %s<br>' \
                '<hilight>Duration:</> %s<br>' \
                '<hilight>Rating:</> %.1f/%d<br>' \
                '<hilight>Viewed:</> %s  <hilight>Likes: </>+%s -%s<br>' \
                '%s' % \
                (author, published, 
                 seconds_to_time_string(duration),
                 rat_avg, rat_max, viewed, likes, dislikes,
                 desc.replace('\r\n', '<br>'))
         item_add(2, title, url, info=info, icon=None, poster=poster, action=ACT_PLAY)
      except:
         item_add(0, 'error parsing data', None)


elif STATE == 3:
   play_url(call_ydl(URL)) # run youtube-dl to get the real video url   \o/

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
