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

def open_url( url ):
   req = urllib2.Request( url )
   content = urllib2.urlopen( req )
   data = content.read()
   content.close()
   return data

def clean( name ):
   list = [( '&amp;', '&' ), ( '&quot;', '"' ), ( '<em>', '' ), ( '</em>', '' ), ( '&#39;', '\'' )]
   for search, replace in list:
      name = name.replace(search, replace)
   return name

# this is the first page, show fixed categories and film in main page
if STATUS == 0:
   d = os.path.dirname(__file__)
   addItem('Coming soon','url', 2, os.path.join(d,'surf.png'), True) # FIXME surf

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
      addItem(name1, url, 5, thumb)

# Coming soon page
elif STATUS == 2:
   data = open_url( 'http://www.traileraddict.com/comingsoon' )

   urls = []
   margin_right = re.compile( '<div style=\"float:right(.*?)<div style="float:left; width:300px;', re.DOTALL ).findall( data )[0]
   margin_left = re.compile( '<div style=\"float:left; width:300px;(.*?)<div style="clear:both;">', re.DOTALL ).findall( data )[0]
   link_title = re.compile( '<img src="/images/arrow2.png" class="arrow"> <a href="(.+?)">(.+?)</a>' ).findall( margin_left )
   
   
   for url, title in link_title:
      url = 'http://www.traileraddict.com/' + url
      urls.append(url)
      # addItem(clean(title), urllib.quote_plus(url), 4, thumb)
      # listitem = xbmcgui.ListItem( label = clean( title ), iconImage = "DefaultFolder.png", thumbnailImage = "DefaultFolder.png" )
		# u = sys.argv[0] + "?mode=4&name=" + urllib.quote_plus( clean( title ) ) + "&url=" + urllib.quote_plus( url )
		# ok = xbmcplugin.addDirectoryItem( handle = int( sys.argv[1] ), url = u, listitem = listitem, isFolder = True )

   

   link_title = re.compile( '<img src="/images/arrow2.png" class="arrow"> <a href="(.+?)">(.+?)</a>' ).findall( margin_right )
   
   for url, title in link_title:
      url = 'http://www.traileraddict.com/' + url
      urls.append(url)
      # listitem = xbmcgui.ListItem( label = clean( title ), iconImage = "DefaultFolder.png", thumbnailImage = "DefaultFolder.png" )
		# u = sys.argv[0] + "?mode=4&name=" + urllib.quote_plus( clean( title ) ) + "&url=" + urllib.quote_plus( url )
		# ok = xbmcplugin.addDirectoryItem( handle = int( sys.argv[1] ), url = u, listitem = listitem, isFolder = True )

   for url in urls:
      find_trailers()

   # xbmcplugin.addSortMethod( handle = int( sys.argv[1] ), sortMethod = xbmcplugin.SORT_METHOD_NONE )
	# xbmcplugin.endOfDirectory( int( sys.argv[1] ) )

# find trailer
elif STATUS == 4:
   pass

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
   # addItem(url, url, 5, '')

def find_trailers( url, name ):
	save_name = name
	data = open_url( url )
	link_thumb = re.compile( '<a href="(.+?)"><img src="(.+?)" name="thumb' ).findall( data )
	thumbs = re.compile( 'img src="/psize\.php\?dir=(.+?)" style' ).findall( data )
	if len( thumbs ) == 0:
		thumb = "DefaultVideo.png"
	else:
		thumb = 'http://www.traileraddict.com/' + thumbs[0]
	title = re.compile( '<div class="abstract"><h2><a href="(.+?)">(.+?)</a></h2><br />', re.DOTALL ).findall( data )
	trailers = re.compile( '<dl class="dropdown">(.+?)</dl>', re.DOTALL ).findall( data )
	item_count = 0
	if len( trailers ) > 0:
		check1 = re.compile( '<a href="(.+?)"><img src="\/images\/usr\/arrow\.png" border="0" style="float:right;" \/>(.+?)</a>' ).findall( trailers[0] )
		check2 = re.compile( '<a href="(.+?)"( style="(.*?)")?>(.+?)<br />' ).findall( trailers[0] )
		if len( check1 ) > 0:
			url_title = check1
			for url, title in url_title:
				url = 'http://www.traileraddict.com' + url
				listitem = xbmcgui.ListItem( label = clean( title ), iconImage = thumb, thumbnailImage = thumb )
				u = sys.argv[0] + "?mode=5&name=" + urllib.quote_plus( save_name + ' (' + clean( title ) + ')' ) + "&url=" + urllib.quote_plus( url )
				ok = xbmcplugin.addDirectoryItem( handle = int( sys.argv[1] ), url = u, listitem = listitem, isFolder = False )
			xbmcplugin.addSortMethod( handle = int(sys.argv[1]), sortMethod = xbmcplugin.SORT_METHOD_NONE )
			xbmcplugin.endOfDirectory( int( sys.argv[1] ) )
		elif len( check2 ) > 0:
			url_title = check2
			for url, trash1, trash2, title in url_title:
				url = 'http://www.traileraddict.com' + url
				listitem = xbmcgui.ListItem( label = clean( title ), iconImage = thumb, thumbnailImage = thumb )
				u = sys.argv[0] + "?mode=5&name=" + urllib.quote_plus( save_name + ' (' + clean( title ) + ')' ) + "&url=" + urllib.quote_plus( url )
				ok = xbmcplugin.addDirectoryItem( handle = int( sys.argv[1] ), url = u, listitem = listitem, isFolder = False )
			xbmcplugin.addSortMethod( handle = int(sys.argv[1]), sortMethod = xbmcplugin.SORT_METHOD_NONE )
			xbmcplugin.endOfDirectory( int( sys.argv[1] ) )
		else:
			dia = xbmcgui.Dialog()
			ok = dia.ok( __settings__.getLocalizedString(30005), __settings__.getLocalizedString(30006) )
	else:
		for url, thumb2 in link_thumb:
			if clean( title[item_count][1] ).find( 'Trailer' ) > 0: 
				url = 'http://www.traileraddict.com' + url
				listitem = xbmcgui.ListItem( label = clean( title[item_count][1] ), iconImage = thumb, thumbnailImage = thumb )
				u = sys.argv[0] + "?mode=5&name=" + urllib.quote_plus( save_name + ' (' + clean( title[item_count][1] ) + ')' ) + "&url=" + urllib.quote_plus( url )
				ok = xbmcplugin.addDirectoryItem( handle = int( sys.argv[1] ),url = u, listitem = item, isFolder = False )
			item_count = item_count + 1
		xbmcplugin.addSortMethod( handle = int( sys.argv[1] ), sortMethod = xbmcplugin.SORT_METHOD_NONE )
		xbmcplugin.endOfDirectory( int( sys.argv[1] ) )
