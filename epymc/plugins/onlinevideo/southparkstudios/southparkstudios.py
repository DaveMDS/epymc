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

from __future__ import absolute_import, print_function


from epymc.extapi.onlinevideo import api_version, state_get, \
   fetch_url, play_url, item_add, call_ydl, local_resource, format_date, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


ST_HOME = 0
ST_EPISODES_LIST = 1
ST_ACTS_LIST = 2
ST_PLAY = 4

base = 'http://southpark.cc.com/'
json_base = 'http://southpark.cc.com/feeds/carousel/video/6154fc40-b7a3-4387-94cc-fc42fc47376e/30/1/json/!airdate/'

STATE, URL = state_get()

# this is the first page, show fixed seasons list
if STATE == ST_HOME:
   for i in range(1, 20):
      item_add(ST_EPISODES_LIST, label=_('Season {0}').format(i),
               url='{}season-{}'.format(json_base, i),
               poster=local_resource(__file__, 'season{}.jpg'.format(i)))


# show the episodes of a single season
elif STATE == ST_EPISODES_LIST:
   season_data = fetch_url(URL, parser='json')
   for num, episode_data in enumerate(season_data['results'], start=1):
      title = '{}. {}'.format(num, episode_data['title'])
      poster = episode_data['images']
      air_date = int(episode_data['originalAirDate'])
      info = '<title>{}: {}</title><br>' \
             '<name>{}:</name> {}<br>{}'.format(
             _('Episode {0}').format(num), episode_data['title'],
             _('First aired'), format_date(air_date),
             episode_data['description'])
      item_add(ST_ACTS_LIST, title, url=episode_data['_url']['default'],
               info=info,
               poster=poster)


# show the acts for a single episode
elif STATE == ST_ACTS_LIST:
   urls = call_ydl(URL).splitlines()
   for i, act_url in enumerate(urls, start=1):
      act_icon = local_resource(__file__, 'act{}.jpg'.format(i))
      item_add(ST_PLAY, 'Act #{}'.format(i), act_url, icon=act_icon)


# and finally play the act
elif STATE == ST_PLAY:
   play_url(URL)
