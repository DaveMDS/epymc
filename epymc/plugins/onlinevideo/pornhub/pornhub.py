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

API_BASE = 'http://www.pornhub.com/webmasters'

# Reference:
#
#  /search?
#     &search = <search query>
#     &catergory = cat  (verified-amateurs, big-ass, ...)
#     &categories[] = cat1,cat2,etc...
#     &stars[] = pornstar1,pornstar2,etc...
#     &tags[] = tag1,tag2,etc...
#     &page = XX
#     &ordering = [featured|newest|mostviewed|rating]
#     &period = [weekly|monthly|alltime]  (only works with the `ordering` parameter)
#     &thumbsize = [small|medium|large|small_hd|medium_hd|large_hd]
#   >>> {
#   >>>   "videos": [
#   >>>     {
#   >>>       "duration": "7:12",
#   >>>       "views": "3533804",
#   >>>       "video_id": "ph5b63795b6ca33",
#   >>>       "rating": "72.56",
#   >>>       "ratings": 21141,
#   >>>       "title": "Step Wants Son To Eat Her",
#   >>>       "url": "https://it.pornhub.com/view_video.php?viewkey=ph5b63795b6ca33",
#   >>>       "default_thumb": "https://ci.phncdn.com/videos/201808/02/177046021/original/(m=eaf8Ggaaaa)(mh=6wSkEAIBryS9JOsI)12.jpg",
#   >>>       "thumb": "https://ci.phncdn.com/videos/201808/02/177046021/original/(m=eaf8Ggaaaa)(mh=6wSkEAIBryS9JOsI)13.jpg",
#   >>>       "publish_date": "2018-08-04 14:41:08",
#   >>>       "thumbs": [
#   >>>         {
#   >>>           "size": "320x240", "width": "320", "height": "240",
#   >>>           "src": "https://ci.phncdn.com/videos/201808/02/177046021/original/(m=eaf8Ggaaaa)(mh=6wSkEAIBryS9JOsI)1.jpg"
#   >>>         },
#   >>>         {
#   >>>           "size": "320x240", "width": "320", "height": "240",
#   >>>           "src": "https://ci.phncdn.com/videos/201808/02/177046021/original/(m=eaf8Ggaaaa)(mh=6wSkEAIBryS9JOsI)16.jpg"
#   >>>         }
#   >>>       ],
#   >>>       "tags": [
#   >>>         { "tag_name": "mom" },
#   >>>         { "tag_name": "mother" },
#   >>>         { "tag_name": "natural tits" }
#   >>>       ],
#   >>>       "pornstars": [
#   >>>         { "pornstar_name": "Nina Kayy" }
#   >>>       ],
#   >>>       "categories": [
#   >>>         { "category": "big-ass" },
#   >>>         { "category": "big-tits" }
#   >>>       ],
#   >>>       "segment": "straight"
#   >>>     }
#   >>>   ]
#   >>> }
#
#  /video_by_id?&id={videoID}&thumbsize={thumbsize}
#  /video_embed_code?id={videoID}
#  /deleted_videos?page={page}
#  /is_video_active?id={videoID}
#  /tags?list={list} (A to Z for tag starting letter, 0 for other)
#
#  /stars
#   >>> {
#   >>>   "stars": [
#   >>>     { "star": { "star_name": "Aaliyah Brown" } },
#   >>>     { "star": { "star_name": "Aaliyah Grey" } },
#   >>>     { "star": { "star_name": "Aaliyah Hadid" } }
#   >>>   ]
#   >>> }
#
#  /stars_detailed
#   >>> {
#   >>>   "stars": [
#   >>>     {
#   >>>       "star": {
#   >>>         "star_name": "Aaliyah Grey",
#   >>>         "star_thumb": "https://ci.phncdn.com/pics/pornstars/000/253/151/(m=lciuhScOb_c)(mh=Sc798oRDdpvJPEAN)thumb_294161.jpg",
#   >>>         "star_url": "https://it.pornhub.com/pornstar/aaliyah-grey",
#   >>>         "gender": "female",
#   >>>         "videos_count_all": "8"
#   >>>       }
#   >>>     },
#   >>>     ... etc
#   >>>   ]
#   >>> }
#
#  /categories
#    >>> {
#    >>>   "categories": [
#    >>>     { "id": "97", "category": "italian" },
#    >>>     { "id": "105", "category": "60fps-1" },
#    >>>     { "id": "252", "category": "amateur-gay" }
#    >>>    ]
#    >>> }
#
#
#


# ITEMS_PER_PAGE = 30

ST_HOME = 0
ST_SEARCH = 1
ST_CATEGORIES = 2
# ST_PORNSTARS = 3
ST_VIDEO_LIST = 4
ST_PLAY = 69

STATE, URL = state_get()


def build_video_list(url, videos):
    for video in videos:
        title = video['title'] or 'Untitled video'
        likes = int(float(video['ratings']) / 100 * float(video['rating']))
        actors = [p['pornstar_name'] for p in video['pornstars']]
        cats = [c['category'] for c in video['categories']]
        tags = [t['tag_name'] for t in video['tags']]
        info = '<title>{}</title> <small>{}</small><br>' \
               '<small><name>{}</name> {}<br>' \
               '<success>{} {}</success> <name>/</name> ' \
               '<warning>{} {:.0f}%</warning> <name>/</name> ' \
               '<info>{} {}</info><br>' \
               '<name>{}:</name> {}<br>' \
               '<name>{}:</name> {}<br>' \
               '<name>{}:</name> {}<br>' \
            .format(
            title, video['duration'],
            _('uploaded'), relative_date(video['publish_date']),
            video['views'], ngettext('view', 'views', int(video['views'])),
            _('rated'), float(video['rating']),
            likes, ngettext('like', 'likes', likes),
            _('Actors'), ', '.join(actors),
            _('Categories'), ', '.join(cats),
            _('Tags'), ', '.join(tags),
        )
        item_add(ST_PLAY, title, video['url'], poster=video['thumb'], info=info)

    if len(videos) == 30:
        build_next_page_item(url, ST_VIDEO_LIST)


def build_next_page_item(url, next_state):
    # NOTE: this assume 'page=X' is ALWAYS the last param!! don't forget it!
    # num_pages = int(total / ITEMS_PER_PAGE) + 1
    url, cur_page = url.split('page=')
    next_page = int(cur_page) + 1
    # if next_page <= num_pages:
    url += 'page=' + str(next_page)
    item_add(next_state, _('More items...'), url, action=ACT_MORE)


# the first page, show fixed categories
if STATE == ST_HOME:

    url = 'http://it.pornhub.com/random'
    item_add(ST_PLAY, _('Play a random video'), url, icon='icon/play')

    item_add(ST_SEARCH, _('Search videos'), 'search', action=ACT_SEARCH)

    url = API_BASE + '/categories'
    item_add(ST_CATEGORIES, _('Categories'), url, action=ACT_FOLDER)

    url = API_BASE + '/search?ordering=newest&page=1'
    item_add(ST_VIDEO_LIST, _('Recently added'), url, action=ACT_FOLDER)

    url = API_BASE + '/search?ordering=mostviewed&period=alltime&page=1'
    item_add(ST_VIDEO_LIST, _('Most viewed'), url, action=ACT_FOLDER)

    url = API_BASE + '/search?ordering=rating&period=alltime&page=1'
    item_add(ST_VIDEO_LIST, _('Top rated'), url, action=ACT_FOLDER)

    # url =  API_BASE + '/stars_detailed'
    # item_add(ST_PORNSTARS, _('All pornstars'), url, action=ACT_FOLDER)


# search query from virtual keyboard
elif STATE == ST_SEARCH:
    url = API_BASE + '/search?' + \
          url_encode({'search': URL, 'thumbsize': 'large'})
    data = fetch_url(url, parser='json')
    build_video_list(url + '&page=1', data['videos'])


# videos list
elif STATE == ST_VIDEO_LIST:
    data = fetch_url(URL, parser='json')
    try:
        build_video_list(URL, data['videos'])
    except KeyError:  # last page probably reached
        pass


# categories list
elif STATE == ST_CATEGORIES:
    data = fetch_url(URL, parser='json')
    for cat in data['categories']:
        url = API_BASE + '/search?' + url_encode({'category': cat['category']})
        item_add(ST_VIDEO_LIST, cat['category'], url + '&page=1')


# pornstars list
# elif STATE == ST_PORNSTARS:
# data = fetch_url(URL, parser='json')
# for star in data['stars']:
# star = star['star']
# url = star['star_url'] + '&page=1'  ## THIS IS WRONG (or must be scraped)
# title = '{} ({} vids)'.format(star['star_name'], star['videos_count_all'])
# item_add(ST_VIDEO_LIST, title, url, poster=star['star_thumb'])

# play (using youtube-dl)
elif STATE == ST_PLAY:
    url = call_ydl(URL)
    play_url(url) if url else report_error('Video not found')
