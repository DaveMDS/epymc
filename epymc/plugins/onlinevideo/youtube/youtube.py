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

from __future__ import absolute_import, print_function, unicode_literals, division

import os, sys, re
from bs4 import BeautifulSoup

from epymc.extapi.onlinevideo import api_version, state_get, fetch_url, \
   play_url, item_add, call_ydl, local_resource, seconds_to_duration, \
   relative_date, url_encode, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


ytb_base = 'http://www.youtube.com'
ytb_icon = local_resource(__file__, 'youtube.png')

ST_HOME = 0
ST_PLAY = 1
ST_SEARCH = 3
ST_CHN_CATEGORIES = 10
ST_CHN_CHANNELS = 11
ST_CHN_VIDEOS = 12

STATE, URL = state_get()


# this is the first page, show fixed categories
if STATE == ST_HOME:
   item_add(ST_SEARCH, _('Search videos'), 'search', None, action=ACT_SEARCH)
   item_add(ST_CHN_CATEGORIES, _('Browse channels'),
            ytb_base+'/channels', None, action=ACT_FOLDER)


###############################################################################
### youtube site scraper ######################################################
###############################################################################

# 0. search results
if STATE == ST_SEARCH:
   if not URL.startswith(ytb_base):
      # first page, URL is the search query entered by the user
      URL = ytb_base + '/results?' + url_encode(
            {'search_query': URL, 'filters': 'video'})

   soup = fetch_url(URL, parser='bs4')
   for div in soup.findAll('div', class_='yt-lockup-video'):
      id = div['data-context-item-id']
      title = div.find('h3', class_='yt-lockup-title').find('a')['title']
      url = ytb_base + '/watch?v=' + id
      poster = 'http://i.ytimg.com/vi/' + id + '/hqdefault.jpg'

      duration = div.find('span', class_='video-time').string
      user = div.find('div', class_='yt-lockup-byline').find('a').string
      descr = div.find('div', class_='yt-lockup-description')
      meta = div.find('ul', class_='yt-lockup-meta-info')
      uploaded = meta.contents[0].string
      views = meta.contents[1].string

      info = '<title>%s</> <small>%s</><br>' \
             '<small><name>%s</> %s <name>/ %s %s</><br>' \
             '<success>%s</></small>' \
             '<br>%s' % (
               title, duration,
               _('user'), user,
               _('uploaded'), uploaded,
               views, descr or '')

      item_add(ST_PLAY, title, url, info=info, poster=poster)

   # more items...
   try:
      url = ytb_base + soup.find('a', attrs={'data-link-type': 'next'})['href']
      item_add(ST_SEARCH, _('More items...'), url, icon='icon/next', action=ACT_MORE)
   except:
      pass


# 1. show the list of channels categories
elif STATE == ST_CHN_CATEGORIES:
   soup = fetch_url(URL, parser='bs4')
   for cat in soup.findAll('div', class_='yt-gb-shelf'):
      try:
         title = cat.find('span', class_='category-title').string
         href = cat.find('a', class_='category-title-link')['href']
         thumb = cat.find('img', role='contentinfo')['src']
         thumb = os.path.dirname(os.path.dirname(thumb)) + '/'

         channels_count = cat.find('span', class_='channel-count').string
         info = '<title>%s</title><br>%s %s' % (
                  title, channels_count,
                  ngettext('channel', 'channels', channels_count))

         item_add(ST_CHN_CHANNELS, title, ytb_base+href, poster=thumb, info=info)
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
         thumb = os.path.dirname(os.path.dirname(thumb)) + '/'
         subscribers = cha.find('span', class_='yt-subscription-button-subscriber-count-branded-horizontal')['title']

         description = cha.find('p', class_='description').string.strip()
         info = '<title>%s</title><br><success>%s</success><br>%s' % (
                title, subscribers, description)

         item_add(ST_CHN_VIDEOS, title, ytb_base+href+'/videos?flow=list&sort=dd',
                  poster=thumb, info=info)
      except:
         pass


# 3. show a list of videos in a given channel
elif STATE == ST_CHN_VIDEOS:
   soup = fetch_url(URL, parser='bs4')
   for div in soup.findAll('div', class_='yt-lockup-video'):
      id = div['data-context-item-id']
      title = div.find('h3', class_='yt-lockup-title').find('a')['title']
      url = ytb_base + '/watch?v=' + id
      poster = 'http://i.ytimg.com/vi/' + id + '/hqdefault.jpg'
      duration = div.find('span', class_='video-time').string
      descr = div.find('div', class_='yt-lockup-description')
      meta = div.find('ul', class_='yt-lockup-meta-info')
      li = meta.find('li')
      uploaded = li.string
      views = li.next_sibling.string
      info = '<title>%s</title> <small>%s</small><br>' \
             '<small><name>%s %s</name><br>' \
             '<success>%s</success></small>' \
             '<br>%s' % (
               title, duration,
               _('uploaded'), uploaded,
               views, descr)# or '')

      item_add(ST_PLAY, title, url, info=info, poster=poster)


# 99. play a video using youtube-dl to get the real url   \o/
elif STATE == ST_PLAY:
   # play the video using ytdl
   play_url(call_ydl(URL))
   
   # and scrape the list of related videos
   soup = fetch_url(URL, parser='bs4')
   for item in soup.find_all('li', class_='related-list-item'):
      id = item.find('a', class_='thumb-link').span['data-vid']
      thumb = 'http://i.ytimg.com/vi/' + id + '/mqdefault.jpg'
      url = ytb_base + '/watch?v=' + id
      title = item.find('a', class_='content-link')['title']
      item_add(ST_PLAY, title, url, poster=thumb)
