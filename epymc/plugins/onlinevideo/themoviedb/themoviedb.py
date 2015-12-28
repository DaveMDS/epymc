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


from epymc.extapi.onlinevideo import api_version, state_get, \
   fetch_url, play_url, item_add, call_ydl, url_encode, language_get, \
   ACT_NONE, ACT_FOLDER, ACT_MORE, ACT_PLAY, ACT_SEARCH


API_KEY = '19eef197b81231dff0fd1a14a8d5f863' # Key of the user DaveMDS
API_BASE = 'http://api.themoviedb.org/3'
IMG_BASE = 'http://image.tmdb.org/t/p' # this should be queried and cached :/

ST_HOME = 0
ST_SEARCH = 1
ST_MOVIES_LIST = 2
ST_MOVIE_INFO = 3
ST_CAST_LIST = 4
ST_NONE = 9
ST_PLAY_YOUTUBE = 10


STATE, URL = state_get()
LANG = language_get()


def v3_request(url):
   if not '?' in url: url += '?'
   url = API_BASE + url + '&api_key=' + API_KEY + '&language=' + LANG
   print("URL " + url)
   return fetch_url(url, parser='json')

def full_img_url(img, size='w500'):
   return (IMG_BASE + '/' + size + img) if img else None

def movie_item(movie_data):
   title = movie_data['title']
   poster = full_img_url(movie_data['poster_path'])
   url = '/movie/%d?append_to_response=credits,videos' % movie_data['id']
   item_add(ST_MOVIE_INFO, title, url, poster=poster)

def next_page_item(url, data, next_state):
   if data['page'] < data['total_pages']:
      page = data['page']
      if '&page=' in url:
         next_url = url.replace('&page=%d'%(page), '&page=%d'%(page+1))
      else:
         if not '?' in url: url += '?'
         next_url = url + '&page=%d' % (page + 1)
      text = _('Load more results (page {0} of {1})').format(page, data['total_pages'])
      item_add(next_state, text, next_url, action=ACT_MORE)
   

################################################################################
# home page
################################################################################
if STATE == ST_HOME:
   item_add(ST_SEARCH, _('Search movies'), 'search', action=ACT_SEARCH)
   item_add(ST_MOVIES_LIST, _('Popular movies'), '/movie/popular', action=ACT_FOLDER)
   item_add(ST_MOVIES_LIST, _('Top rated movies'), '/movie/top_rated', action=ACT_FOLDER)
   item_add(ST_MOVIES_LIST, _('Upcoming movies'), '/movie/upcoming', action=ACT_FOLDER)
   item_add(ST_MOVIES_LIST, _('Now playing movies'), '/movie/now_playing', action=ACT_FOLDER)


################################################################################
# search movies
################################################################################
elif STATE == ST_SEARCH:
   if not '&page=' in URL:
      data = v3_request('/search/movie?' + url_encode({'query':URL}))
   else:
      data = v3_request('/search/movie?query=' + URL)

   for m in data['results']:
      movie_item(m)

   next_page_item(URL, data, ST_SEARCH)


################################################################################
# movies list
################################################################################
elif STATE == ST_MOVIES_LIST:
   data = v3_request(URL)
   for m in data['results']:
      movie_item(m)

   next_page_item(URL, data, ST_MOVIES_LIST)


################################################################################
# movie infos
################################################################################
elif STATE == ST_MOVIE_INFO:
   data = v3_request(URL)

   # movie info
   title = data['title']
   poster = full_img_url(data['poster_path'])
   try:
      overview = data['overview']
   except:
      overview = ''

   try:
      genres = ', '.join([ g['name'] for g in data['genres'] ])
   except:
      genres = _('Unknown')

   try:
      country = data['production_countries'][0]['iso_3166_1']
   except:
      country = ''

   try:
      year = data['release_date'][:4]
   except:
      year = ''

   try:
      directors = [d['name'] for d in data['credits']['crew'] if d['job'] == 'Director']
   except:
      directors = [_('Unknown')]

   try:
      casts = [ d['name'] for i,d in enumerate(data['credits']['cast']) if i < 5 ]
   except:
      casts = [_('Unknown')]

   info = '<title>{}</title> <small>({} {})</small><br>' \
          '<small><name>{}:</name> {}</small><br>' \
          '<small><name>{}:</name> {}</small><br>' \
          '<small><name>{}:</name> {}</small><br>' \
          '<small><name>{}:</name> {}/10 ({} {})</small><br>' \
          '<small><name>{}:</name> {}</small><br>' \
          '{}'.format(title, country, year,
             _('Director'), ', '.join(directors),
             _('Cast'), ', '.join(casts),
             _('Genres'), genres,
             _('Rating'), data['vote_average'], data['vote_count'], _('votes'),
             _('Released'), data['release_date'],
             overview)
   item_add(ST_NONE, title, None, poster=poster,
            info=info, icon='icon/info', action=ACT_NONE)

   # trailers
   for video in data['videos']['results']:
      if video['site'] == 'YouTube':
         url = 'https://www.youtube.com/watch?v=%s' % video['key']
         info = '<title>{}</title><br>' \
                '<name>{}:</name> <value>{}</value><br>' \
                '<name>{}:</name> <value>{}</value><br>' \
                '<name>{}:</name> <value>{}</value>'.format(
                   video['name'],
                   _('Language'), video['iso_639_1'],
                   _('Source'), video['site'],
                   _('Resolution'), video['size'])
         item_add(ST_PLAY_YOUTUBE, video['name'], url,
                  info=info,poster=poster, icon='icon/play')

   # cast
   item_add(ST_CAST_LIST, _('Cast'), '/movie/%d/credits' % data['id'],
            poster=poster, icon='icon/head')


################################################################################
# Cast list
################################################################################
elif STATE == ST_CAST_LIST:
   data = v3_request(URL)
   for c in data['cast']:
      title = _('%(name)s <i>as %(character)s</i>') % c
      poster = full_img_url(c['profile_path'], size='h632')
      item_add(ST_NONE, title, 'url', poster=poster, action=ACT_NONE)


################################################################################
# Play youtube video
################################################################################
elif STATE == ST_PLAY_YOUTUBE:
   real_url = call_ydl(URL)
   play_url(real_url)
