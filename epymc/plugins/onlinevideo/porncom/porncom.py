#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2018 Davide Andreoli <dave@gurumeditation.it>
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

from epymc.extapi.onlinevideo import api_version, state_get, \
   fetch_url, play_url, item_add, call_ydl, report_error, \
   seconds_to_duration, relative_date, url_encode, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


API_BASE = 'http://api.porn.com'
ITEMS_PER_PAGE = 50

ST_HOME = 0
ST_SEARCH = 1
ST_CATEGORIES = 2
ST_CHANNELS = 3
ST_VIDEO_LIST = 4
ST_PLAY = 69

STATE, URL = state_get()


def build_video_list(url, data):
   for video in data['result']:
      title = video['title'] or 'Untitled video'
      info = '<title>{}</title> <small>{}</small><br>' \
             '<small><name>{}</name> {}<br>' \
             '<success>{} {}</success> <name>/</name> ' \
             '<warning>{} {:.1f}/5</warning> <name>/</name> ' \
             '<info>{} {}</info><br>' \
             '<name>Actors:</name> {}<br>' \
             '<name>Tags:</name> {}</small>'.format(
                  title, seconds_to_duration(video['duration']),
                  _('uploaded'), relative_date(video['active_date']),
                  video['views'], ngettext('view', 'views', video['views']),
                  _('rated'), video['rating'],
                  video['ratings'], ngettext('like', 'likes', video['ratings']),
                  ', '.join(video['actors']),
                  ', '.join(video['tags']))

      item_add(ST_PLAY, title, video['url'], poster=video['thumb'], info=info)
   build_next_page_item(url, data['count'], ST_VIDEO_LIST)


def build_next_page_item(url, total, next_state):
   # NOTE: this assume 'page=X' is ALWAYS the last param!! don't forget it!
   num_pages = int(total / ITEMS_PER_PAGE) + 1
   url, cur_page = url.split('page=')
   next_page = int(cur_page) + 1
   if next_page <= num_pages:
      url += 'page=%d' % (next_page)
      title = 'Next page ({} of {})'.format(next_page, num_pages)
      item_add(next_state, title, url, action=ACT_MORE)
   

# the first page, show fixed categories
if STATE == ST_HOME:

   item_add(ST_SEARCH, 'Search videos', 'search', action=ACT_SEARCH)

   url = 'http://www.porn.com/random'
   item_add(ST_PLAY, 'Play a Random video', url, icon='icon/play')

   url = API_BASE + '/videos/find.json?order=date&limit={}&page=1'.format(ITEMS_PER_PAGE)
   item_add(ST_VIDEO_LIST, 'Recently Added', url, action=ACT_FOLDER)

   url =  API_BASE + '/videos/find.json?order=views&limit={}&page=1'.format(ITEMS_PER_PAGE)
   item_add(ST_VIDEO_LIST, 'Most Viewed', url, action=ACT_FOLDER)

   url =  API_BASE + '/videos/find.json?order=rating&limit={}&page=1'.format(ITEMS_PER_PAGE)
   item_add(ST_VIDEO_LIST, 'Top Rated', url, action=ACT_FOLDER)

   # url =  API_BASE + '/videos/find.json?order=favorites&limit={}&page=1'.format(ITEMS_PER_PAGE)
   # item_add(ST_VIDEO_LIST, 'Top Favorites', url, action=ACT_FOLDER)

   url =  API_BASE + '/categories/find.json'
   item_add(ST_CATEGORIES, 'Categories', url, action=ACT_FOLDER)

   url =  API_BASE + '/channels/find.json?order=rating&limit={}&page=1'.format(ITEMS_PER_PAGE)
   item_add(ST_CHANNELS, 'Channels - Top Rated', url, action=ACT_FOLDER)

   url =  API_BASE + '/channels/find.json?order=views&limit={}&page=1'.format(ITEMS_PER_PAGE)
   item_add(ST_CHANNELS, 'Channels - Most Viewed', url, action=ACT_FOLDER)

   url =  API_BASE + '/channels/find.json?order=favorites&limit={}&page=1'.format(ITEMS_PER_PAGE)
   item_add(ST_CHANNELS, 'Channels - Top Favorites', url, action=ACT_FOLDER)


# search query from virtual keyboard
elif STATE == ST_SEARCH:
   url = API_BASE + '/videos/find.json?' + \
         url_encode({'search': URL, 'limit': ITEMS_PER_PAGE, 'order': 'rating'})
   data = fetch_url(url, parser='json')
   build_video_list(url + '&page=1', data)


# videos list
elif STATE == ST_VIDEO_LIST:
   data = fetch_url(URL, parser='json')
   build_video_list(URL, data)


# categories list
elif STATE == ST_CATEGORIES:
   data = fetch_url(URL, parser='json')
   for cat in data['result']:
      url = API_BASE + '/videos/find.json?' + \
            url_encode({'tags': cat, 'limit': ITEMS_PER_PAGE, 'order': 'date'})
      item_add(ST_VIDEO_LIST, cat, url + '&page=1')
   

# channels list
elif STATE == ST_CHANNELS:
   data = fetch_url(URL, parser='json')
   for ch in data['result']:
      url = API_BASE + '/videos/find.json?' + \
            url_encode({'channel': ch['name'], 'limit': ITEMS_PER_PAGE, 'order': 'date'})
      title = '{} ({} vids)'.format(ch['name'], ch['num_videos'])
      item_add(ST_VIDEO_LIST, title, url + '&page=1')
   build_next_page_item(URL, data['count'], ST_CHANNELS)


# play (using youtube-dl)
elif STATE == ST_PLAY:
   url = call_ydl(URL)
   play_url(url) if url else report_error('Video not found')

