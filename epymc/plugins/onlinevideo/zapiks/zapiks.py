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

import os
import traceback
from bs4 import BeautifulSoup

from epymc.extapi.onlinevideo import api_version, state_get, \
   fetch_url, play_url, item_add, call_ydl, relative_date, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


ST_HOME = 0
ST_VIDEO_LIST = 1
ST_PLAY = 2

base = 'http://www.zapiks.com/'

STATE, URL = state_get()


# this is the first page, show fixed categories
if STATE == ST_HOME:
   b = base
   u = '/popular_1.php'
   d = os.path.dirname(__file__)
   item_add(ST_VIDEO_LIST, 'Brand New Videos', b+'p_1', action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Surf', b+'surf_'+u, poster=os.path.join(d,'surf.png'), action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Snowboard', b+'snowboard_'+u, poster=os.path.join(d,'snowboard.png'), action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Mountain Bike', b+'mountainbike_'+u, poster=os.path.join(d,'vtt.png'), action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Bmx', b+'bmx_'+u, poster=os.path.join(d,'bmx.png'), action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Skate', b+'skate_'+u, poster=os.path.join(d,'skate.png'), action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Ski', b+'ski_'+u, poster=os.path.join(d,'ski.png'), action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Kite', b+'kite_'+u, poster=os.path.join(d,'zapiks.png'), action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Wakeboard', b+'wake_'+u, poster=os.path.join(d,'zapiks.png'), action=ACT_FOLDER)
   item_add(ST_VIDEO_LIST, 'Other', b+'other_'+u, poster=os.path.join(d,'zapiks.png'), action=ACT_FOLDER)


# the page for each category
elif STATE == ST_VIDEO_LIST:
   # soup = fetch_url(URL, parser='bs4') # this line work, but:
   # the zapiks page have an erroneous auto closing div tag
   # so wee need this hack to let bs4 correctly parse the html
   html = fetch_url(URL)
   soup = BeautifulSoup(html.replace('/>', '>'), 'lxml')

   videos = soup.findAll('a', class_='teaser-video-content')
   for video in videos:
      try:
         url = 'http://www.zapiks.com' + video['href']
         title = video.find('span', class_='teaser-title').string.strip()
         thumb = video.find('div', class_='teaser-thumbnail')['style']
         thumb = thumb.replace("background-image : url('", '').replace("')", '')
         intro = video.find('div', class_='teaser-intro').string
         user = video.find('span', class_='teaser-user').string.strip().replace('from ', '')
         uploaded = video.find('span', class_='teaser-date')['datetime']
         views = list(video.find('span', class_='teaser-counter').strings)[0]
         views = int(views.strip().replace('Views', '').replace(' ', ''))
         try:
            likes = int(video.find('span', class_='teaser-counter-likes').string.strip())
         except:
            likes = 0
         info = '<title>{}</title><br>' \
                '<small><name>{}</name> {} <name>/ {} {}</name></small><br>' \
                '<small><success>{} {}</success> <name>/</> ' \
                '<info>{} {}</info></small><br>' \
                '{}'.format(title,
                   _('user'), user, _('uploaded'), relative_date(uploaded),
                   views, ngettext('view', 'views', views),
                   likes, ngettext('like', 'likes', likes),
                   intro.replace('&amp;', '&') if intro else '')
         
         item_add(ST_PLAY, title, url, poster=thumb, info=info, icon='icon/play')
      except:
         traceback.print_exc()

   try:
      cur_page = soup.find('li', class_='active')
      next_page = cur_page.next_sibling.a['href']
      item_add(ST_VIDEO_LIST, 'More items...', 'http://www.zapiks.com' + next_page, icon='icon/next', action=ACT_MORE)
   except:
      pass


# extract the video link from the video page
elif STATE == ST_PLAY:
   video_url = call_ydl(URL)
   play_url(video_url)
