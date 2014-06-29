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


from epymc.extapi.onlinevideo import api_version, state_get, \
   fetch_url, play_url, item_add, call_ydl, local_resource, \
   relative_date, seconds_to_duration, url_encode, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


api_base = 'https://api.vimeo.com'
app_token = '55e9f802ceb814b649ef3c9504d4d38f' # Official token for EpyMC
headers = { 'Authorization': 'Bearer '+app_token, 'User-Agent': 'EpyMC',
            'Accept': 'application/vnd.vimeo.*+json;version=3.0' }

ITEMS_PER_PAGE = 50

ST_HOME = 0
ST_VIDEO_LIST = 1
ST_CHANN_LIST = 2
ST_CATEGORIES = 3
ST_PLAY = 10

STATE, URL = state_get()


def vimeo_api_url(url):
   return fetch_url(url, headers=headers, parser='json')

def vimeo_api_call(endpoint, **kargs):
   url = api_base + endpoint + '?' + url_encode(kargs)
   return vimeo_api_url(url)

def video_item_add(video):
   poster = [ p['link'] for p in video['pictures'] if p['width'] == 640 ][0]
   info = u'<title>{}</title><br>' \
           '<hilight>Duration: </hilight> {}<br>' \
           'from <i>{}</i>, added <i>{}</i>.<br>' \
           '{} plays / {} likes / {} comments<br>' \
           '<br>{}'.format(
               video['name'],
               seconds_to_duration(video['duration']),
               video['user']['name'],
               relative_date(video['created_time']),
               video['stats']['plays'],
               video['stats']['likes'],
               video['stats']['comments'],
               video['description'] or '')
   item_add(ST_PLAY, video['name'], video['link'], poster=poster, info=info)

def channel_item_add(channel):
   url = api_base + channel['metadata']['connections']['videos']
   poster = [ p['link'] for p in channel['pictures'] if p['width'] == 640 ][0]
   info = u'<title>{}</title><br>' \
           'from <i>{}</i><br>' \
           '{} videos / {} followers<br>' \
           '<br>{}'.format(
               channel['name'],
               channel['user']['name'],
               channel['stats']['videos'],
               channel['stats']['users'],
               channel['description'])
   item_add(ST_VIDEO_LIST, channel['name'], url, poster=poster, info=info)


################################################################################
# home page
################################################################################
if STATE == ST_HOME:
   item_add(ST_VIDEO_LIST, 'Search videos', 'search', action=ACT_SEARCH)
   item_add(ST_CHANN_LIST, 'Search channels', 'search', action=ACT_SEARCH)
   item_add(ST_CATEGORIES, 'Browse categories', 'cats', action=ACT_FOLDER)


################################################################################
# videos list
################################################################################
elif STATE == ST_VIDEO_LIST:
   if URL.startswith(api_base):
      results = vimeo_api_url(URL)
   else:
      results = vimeo_api_call('/videos', query=URL, per_page=ITEMS_PER_PAGE)

   for video in results['data']:
      video_item_add(video)

   if results['paging']['next']:
      url = api_base + results['paging']['next']
      text = 'More of the %s results' % results['total']
      item_add(ST_VIDEO_LIST, text, url, icon='icon/next', action=ACT_MORE)


################################################################################
# channels list
################################################################################
elif STATE == ST_CHANN_LIST:
   if URL.startswith(api_base):
      results = vimeo_api_url(URL)
   else:
      results = vimeo_api_call('/channels', query=URL, per_page=ITEMS_PER_PAGE)

   for channel in results['data']:
      channel_item_add(channel)

   if results['paging']['next']:
      url = api_base + results['paging']['next']
      text = 'More of the %s results' % results['total']
      item_add(ST_SEARCH_CHANNELS, text, url, icon='icon/next', action=ACT_MORE)


################################################################################
# browse categories and subcategories
################################################################################
elif STATE == ST_CATEGORIES:
   results = vimeo_api_call('/categories', query=URL, per_page=1000)
   
   for cat in results['data']:
      name = cat['name']
      url = api_base + cat['uri'] + '/videos?per_page=%d' % ITEMS_PER_PAGE
      item_add(ST_VIDEO_LIST, name, url)

      for sub in cat['subcategories']:
         subname = name + ' - ' + sub['name']
         url = api_base + sub['uri'] + '/videos?per_page=%d' % ITEMS_PER_PAGE
         item_add(ST_VIDEO_LIST, subname, url)


################################################################################
# play a video using youtube-dl to get the real url   \o/
################################################################################
elif STATE == ST_PLAY:
   play_url(call_ydl(URL))
   
