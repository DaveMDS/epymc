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

import sys

from epymc.extapi.onlinevideo import api_version, state_get, \
   fetch_url, play_url, report_error, item_add, call_ydl, local_resource, \
   relative_date, seconds_to_duration, url_encode, URLError, HTTPError, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


api_base = 'https://api.vimeo.com'
app_token = '55e9f802ceb814b649ef3c9504d4d38f' # Official token for EpyMC
headers = { 'Authorization': 'Bearer '+app_token, 'User-Agent': 'EpyMC',
            'Accept': 'application/vnd.vimeo.*+json;version=3.2' }

icon_channels = local_resource(__file__, 'icon_channels.png')
icon_groups = local_resource(__file__, 'icon_groups.png')
icon_categories = local_resource(__file__, 'icon_categories.png')
icon_users = local_resource(__file__, 'icon_users.png')
icon_videos = 'icon/play'

ITEMS_PER_PAGE = 50

ST_HOME = 0
ST_VIDEO_LIST = 1
ST_CHANN_LIST = 2
ST_GROUP_LIST = 3
ST_USERS_LIST = 4
ST_CATEGORIES = 5
ST_PLAY = 10

STATE, URL = state_get()


def vimeo_api_url(url):
   try: 
      return fetch_url(url, headers=headers, parser='json')
   except HTTPError as e:
      report_error('%d: %s' % (e.code, e.reason))
   except URLError as e:
      report_error('%s' % (e.reason))
   sys.exit(1)

def vimeo_api_call(endpoint, **kargs):
   url = api_base + endpoint + '?' + url_encode(kargs)
   return vimeo_api_url(url)

def video_item_add(video):
   try:
      poster = [ p['link'] for p in video['pictures']['sizes'] if p['width'] == 640 ][0]
      if '?' in poster: poster = poster.split('?')[0]
   except:
      poster = None
   views = video['stats']['plays'] or 0
   likes = video['metadata']['connections']['likes']['total'] or 0
   comments = video['metadata']['connections']['comments']['total'] or 0
   info = '<title>%s</> <small>%s</small><br>' \
          '<small><name>%s</> %s <name>/ %s %s</><br>' \
          '<success>%s %s</> <name>/</> ' \
          '<warning>%s %s</> <name>/</> ' \
          '<info>%s %s</></small><br>%s' % (
            video['name'], seconds_to_duration(video['duration']),
            _('user'), video['user']['name'],
            _('uploaded'), relative_date(video['created_time']),
            views, ngettext('view', 'views', views),
            likes, ngettext('like', 'likes', likes),
            comments, ngettext('comment', 'comments', comments),
            video['description'] or '')
   item_add(ST_PLAY, video['name'], video['link'], icon=icon_videos,
                     poster=poster, info=info)

def channel_item_add(channel):
   url = api_base + channel['metadata']['connections']['videos']['uri']
   try:
      poster = [ p['link'] for p in channel['pictures']['sizes'] if p['width'] == 640 ][0]
      if '?' in poster: poster = poster.split('?')[0]
   except:
      poster = None

   videos = channel['metadata']['connections']['videos']['total']
   followers = channel['metadata']['connections']['users']['total']
   info = '<title>%s</title><br>' \
          '<small><name>%s</> %s <name>/ %s %s</><br>' \
          '<name>%s</> %s<br>' \
          '<success>%d %s</success> <name>/</> ' \
          '<info>%d %s</info></small><br>%s' % (
            channel['name'],
            _('user'), channel['user']['name'],
            _('created'), relative_date(channel['created_time']),
            _('updated'), relative_date(channel['modified_time']),
            videos, ngettext('video', 'videos', videos),
            followers, ngettext('follower', 'followers', followers),
            channel['description'] or '')
   item_add(ST_VIDEO_LIST, channel['name'], url, icon=icon_channels,
                           poster=poster, info=info)

def group_item_add(group):
   url = api_base + group['metadata']['connections']['videos']['uri']
   try:
      poster = [ p['link'] for p in group['pictures']['sizes'] if p['width'] == 640 ][0]
      if '?' in poster: poster = poster.split('?')[0]
   except:
      poster = None
   videos = group['metadata']['connections']['videos']['total'] or 0
   followers = group['metadata']['connections']['users']['users'] or 0
   info = '<title>%s</><br>' \
          '<small><name>%s</> %s <name>/ %s %s</><br>' \
          '<name>%s</> %s<br>' \
          '<success>%d %s</> <name>/</> <info>%d %s</></small><br>%s' % (
            group['name'],
            _('user'), group['user']['name'],
            _('created'), relative_date(group['created_time']),
            _('updated'), relative_date(group['modified_time']),
            videos, ngettext('video', 'videos', videos),
            followers, ngettext('follower', 'followers', followers),
            group['description'] or '')
   item_add(ST_VIDEO_LIST, group['name'], url, icon=icon_groups,
                           poster=poster, info=info)

def user_item_add(user):
   url = api_base + user['metadata']['connections']['videos']['uri']
   try:
      poster = [ p['link'] for p in user['pictures']['sizes'] if p['width'] == 300 ][0]
      if '?' in poster: poster = poster.split('?')[0]
   except:
      poster = None
   info = '<title>%s</><br>' \
          '<small><name>%s</> %s<br>' \
          '<name>%s</> %s</small><br>%s' % (
            user['name'],
            _('joined'), relative_date(user['created_time']),
            _('location'), user['location'] or _('Unknown'),
            user['bio'] or '')
   item_add(ST_VIDEO_LIST, user['name'], url, icon=icon_users,
                           poster=poster, info=info)


################################################################################
# home page
################################################################################
if STATE == ST_HOME:
   # searches
   item_add(ST_VIDEO_LIST, _('Search videos'), 'search1', action=ACT_SEARCH)
   item_add(ST_CHANN_LIST, _('Search channels'), 'search2', action=ACT_SEARCH)
   item_add(ST_GROUP_LIST, _('Search groups'), 'search3', action=ACT_SEARCH)
   item_add(ST_USERS_LIST, _('Search people'), 'search4', action=ACT_SEARCH)

   # more relevant videos (THIS DO NOT WORK, need to find another api)
   # url = api_base + '/videos?sort=relevant&per_page=%d' % ITEMS_PER_PAGE
   # item_add(ST_VIDEO_LIST, _('More relevant videos'), url,
                           # icon=icon_videos, action=ACT_FOLDER)

   # more followed channels
   url = api_base + '/channels?sort=followers&per_page=%d' % ITEMS_PER_PAGE
   item_add(ST_CHANN_LIST, _('More followed channels'), url,
                           icon=icon_channels, action=ACT_FOLDER)

   # more followed groups
   url = api_base + '/groups?sort=followers&per_page=%d' % ITEMS_PER_PAGE
   item_add(ST_GROUP_LIST, _('More followed groups'), url,
                           icon=icon_groups, action=ACT_FOLDER)

   # more relevant users (DO NOT WORK)
   # url = api_base + '/users?sort=relevant&per_page=%d' % ITEMS_PER_PAGE
   # item_add(ST_USERS_LIST, 'More relevant users', url,
                           # icon=icon_users, action=ACT_FOLDER)
   # browse by cats
   item_add(ST_CATEGORIES, _('Browse videos'), '/videos', action=ACT_FOLDER)
   item_add(ST_CATEGORIES, _('Browse channels'), '/channels', action=ACT_FOLDER)
   item_add(ST_CATEGORIES, _('Browse groups'), '/groups', action=ACT_FOLDER)
   item_add(ST_CATEGORIES, _('Browse users'), '/users', action=ACT_FOLDER)


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
      text = _('Load more results (%d in total)') % results['total']
      item_add(ST_VIDEO_LIST, text, url, action=ACT_MORE)


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
      text = _('Load more results (%d in total)') % results['total']
      item_add(ST_CHANN_LIST, text, url, action=ACT_MORE)


################################################################################
# groups list
################################################################################
elif STATE == ST_GROUP_LIST:
   if URL.startswith(api_base):
      results = vimeo_api_url(URL)
   else:
      results = vimeo_api_call('/groups', query=URL, per_page=ITEMS_PER_PAGE)

   for group in results['data']:
      group_item_add(group)

   if results['paging']['next']:
      url = api_base + results['paging']['next']
      text = _('Load more results (%d in total)') % results['total']
      item_add(ST_GROUP_LIST, text, url, action=ACT_MORE)

################################################################################
# users list
################################################################################
elif STATE == ST_USERS_LIST:
   if URL.startswith(api_base):
      results = vimeo_api_url(URL)
   else:
      results = vimeo_api_call('/users', query=URL, per_page=ITEMS_PER_PAGE)

   for user in results['data']:
      user_item_add(user)

   if results['paging']['next']:
      url = api_base + results['paging']['next']
      text = _('Load more results (%d in total)') % results['total']
      item_add(ST_USERS_LIST, text, url, action=ACT_MORE)


################################################################################
# browse categories and subcategories
################################################################################
elif STATE == ST_CATEGORIES:
   results = vimeo_api_call('/categories')
   if URL == '/videos': NEXT_STATE = ST_VIDEO_LIST
   elif URL == '/channels': NEXT_STATE = ST_CHANN_LIST
   elif URL == '/groups': NEXT_STATE = ST_GROUP_LIST
   elif URL == '/users': NEXT_STATE = ST_USERS_LIST
   
   for cat in results['data']:
      name = cat['name']
      url = api_base + cat['uri'] + URL + '?per_page=%d' % ITEMS_PER_PAGE

      try:
         poster = [ c['link'] for c in cat['pictures']['sizes'] if c['width'] == 640 ][0]
         if '?' in poster: poster = poster.split('?')[0]
      except:
         poster = None

      videos = cat['metadata']['connections']['videos']['total']
      channels = cat['metadata']['connections']['channels']['total']
      groups = cat['metadata']['connections']['groups']['total']
      info = '<title>%s</><br>' \
             '<small><success>%d %s</> <name>/</> ' \
             '<info>%d %s</> <name>/</> <warning>%d %s</></small>' % (name,
               videos, ngettext('video', 'videos', videos),
               channels, ngettext('channel', 'channels', channels),
               groups, ngettext('group', 'groups', groups))
      
      item_add(NEXT_STATE, name, url, icon=icon_categories,
                           info=info, poster=poster)

      for sub in cat['subcategories']:
         subname = name + ' - ' + sub['name']
         url = api_base + sub['uri'] + URL + '?per_page=%d' % ITEMS_PER_PAGE
         item_add(NEXT_STATE, subname, url, icon=icon_categories,
                              info=info, poster=poster)


################################################################################
# play a video using youtube-dl to get the real url   \o/
################################################################################
elif STATE == ST_PLAY:
   play_url(call_ydl(URL))
   
