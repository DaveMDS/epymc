#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2012 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of EpyMC.
#
# EpyMC is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# EpyMC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with EpyMC. If not, see <http://www.gnu.org/licenses/>.

# CREDITS:
#  this is a rude copy from the xbmc addons by:
#      stacked <stacked.xbmc@gmail.com>
#  all the credits goes to him...thanks!

# REFERENCE:
# From app: "cmd STATE URL"
# To app: (label,url,state,icon,is_folder)  one item per line
#  or
# To app: PLAY!http://bla.bla.bla/coolvideo.ext

import os, sys, urllib2, re
from BeautifulSoup import BeautifulSoup

AGENT='Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
STATUS = int(sys.argv[1])
URL = sys.argv[2]


def addItem(label, url, state, icon, is_folder=False):
   print((label, url, state, icon, is_folder))

def playUrl(url):
   print 'PLAY!' + url

def open_url(url):
   req = urllib2.Request(url)
   content = urllib2.urlopen(req)
   data = content.read()
   content.close()
   return data

def clean(name):
   list = [( '&amp;', '&' ), ( '&quot;', '"' ), ( '<em>', '' ), ( '</em>', '' ), ( '&#39;', '\'' )]
   for search, replace in list:
      name = name.replace(search, replace)
   return name

# this is the first page, show fixed categories and film in main page
if STATUS == 0:
   addItem('Coming soon','http://www.traileraddict.com/comingsoon', 2, None, True)
   addItem('Top Films','http://www.traileraddict.com/top150', 2, None, True)
   addItem('Top Trailers','http://www.traileraddict.com/attraction/1', 6, None, True)

   data = open_url('http://www.traileraddict.com/')
   regexp = '<a href="/trailer/(.+?)"><img src="(.+?)" border="0" alt="(.+?)"' + \
            ' title="(.+?)" style="margin:2px 10px 8px 10px;">'
   url_thumb_x_title = re.compile(regexp).findall(data)
   for url, thumb, x, title in url_thumb_x_title:
      title = title.rsplit(' - ')
      name1 = clean(title[0])
      if len(title) > 1:
         name2 = clean(title[0]) + ' (' + clean(title[1]) + ')'
      else:
         name2 = clean(title[0])
      url = 'http://www.traileraddict.com/trailer/' + url
      thumb = 'http://www.traileraddict.com' + thumb
      addItem(name1, url.encode('ascii'), 5, thumb)

# ComingSoon/Top150 pages
elif STATUS == 2:
   data = open_url(URL)
   soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)

   arrows = soup.findAll('img', attrs = {'class' : 'arrow'})
   for arrow in arrows:
      title = arrow.nextSibling.nextSibling.contents[0]
      url = arrow.nextSibling.nextSibling['href']
      url = 'http://www.traileraddict.com' + url
      # print title, url
      addItem(title, url.encode('ascii'), 4, None)

# find trailers in film page
elif STATUS == 4:
   data = open_url(URL)
   soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)

   for div in soup.findAll('div', attrs = {'class' : 'info'}):
      a = div.find('h2').contents[0]
      title = a.contents[0]
      url = 'http://www.traileraddict.com' + a['href']
      # print title, url
      addItem(title, url.encode('ascii'), 5, 'icon/play')


# top trailers page
elif STATUS == 6:
   data = open_url(URL)
   soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)

   leftcolumn = soup.find('div', attrs = {'class' : 'leftcolumn'})
   for a in leftcolumn.findAll('a'):
      if a['href'].startswith('/trailer/'):
         title = a.find('img')['title']
         url = 'http://www.traileraddict.com' + a['href']
         # print title, url
         addItem(title, url.encode('ascii'), 5, 'icon/play')

# play video
elif STATUS == 5:
   data = open_url(URL)
   url = re.compile('<param name="movie" value="http://www.traileraddict.com/emb/(.+?)">').findall(data)[0]
   if data.find('black-tab-hd.png') > 0:
      url = 'http://www.traileraddict.com/fvarhd.php?tid=' + url
   else:
      url = 'http://www.traileraddict.com/fvar.php?tid=' + url

   data = open_url(url)
   url = re.compile('fileurl=(.+?)&vidwidth').findall(data)[0]
   thumb = re.compile('&image=(.+?)').findall(data)[0]
   url = url.replace('%3A', ':').replace('%2F', '/').replace('%3F', '?').replace('%3D', '=').replace('%26', '&').replace('%2F', '//')

   req = urllib2.Request(url)
   content = urllib2.urlopen(req)
   url = content.geturl()
   content.close()
   playUrl(str(url))