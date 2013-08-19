#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2013 Davide Andreoli <dave@gurumeditation.it>
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

import os, sys, urllib, urllib2, json, re
# from BeautifulSoup import BeautifulSoup

AGENT='Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
ITEMS_PER_PAGE = 50

### API V.3  ###################################################################
STATE = int(sys.argv[1])
URL = sys.argv[2]

ACT_NONE = 0; ACT_FOLDER = 1; ACT_MORE = 2; ACT_PLAY = 3; ACT_SEARCH = 4

def addItem(next_state, label, url, info = None, icon = None, poster = None, action = ACT_NONE):
   print((next_state, label, url, info, icon, poster, action))

def playUrl(url):
   print('PLAY!' + url)

### API END  ###################################################################


# youtube api reference:
# https://developers.google.com/youtube/2.0/developers_guide_protocol


def open_url(url):
   req = urllib2.Request(url)
   # req.addheaders = [('Referer', 'http://www.zapiks.com'), (AGENT)]
   content = urllib2.urlopen(req)
   data = content.read()
   content.close()
   return data

def seconds_to_time_string(seconds):
   seconds = int(seconds)
   h = int(seconds / 3600)
   m = int(seconds / 60) % 60
   s = int(seconds % 60)
   if h > 0:
      return "%d:%02d:%02d" % (h,m,s)
   else:
      return "%d:%02d" % (m,s)

CATS = ['Film', 'Autos', 'Music', 'Animals', 'Sports', 'Shortmov', 'Travel',
'Games', 'Videoblog', 'People', 'Comedy', 'Entertainment', 'News', 'Howto',
'Education', 'Tech', 'Nonprofit', 'Movies', 'Shows', 'Trailers']


# this is the first page, show fixed categories
if STATE == 0:
   # b = 'http://gdata.youtube.com/feeds/api/standardfeeds/IT/'
   std = 'http://gdata.youtube.com/feeds/api/standardfeeds/'
   e = 'v=2&alt=jsonc&max-results=' + str(ITEMS_PER_PAGE)
   # e = 'v=2&alt=json'
   # d = os.path.dirname(__file__)
   addItem(4, 'Search videos', 'search', None, action=ACT_SEARCH)
   addItem(4, 'Search channels (TODO)', 'search', None, action=ACT_SEARCH)
   addItem(2, 'Categories :/', 'cats', None, action=ACT_FOLDER)
   addItem(1, 'Top rated', std+'top_rated?'+e, None, action=ACT_FOLDER)
   addItem(1, 'Top favorites', std+'top_favorites?'+e, None, action=ACT_FOLDER)
   addItem(1, 'Most shared', std+'most_shared?'+e, None, action=ACT_FOLDER)
   addItem(1, 'Most popular', std+'most_popular?'+e, None, action=ACT_FOLDER)
   # addItem(1, 'Most recent', std+'most_recent?'+e, None, action=ACT_FOLDER)
   addItem(1, 'Most discussed', std+'most_discussed?'+e, None, action=ACT_FOLDER)
   addItem(1, 'Most viewed', std+'most_viewed?'+e, None, action=ACT_FOLDER)
   


# show the list of categories
elif STATE == 2:
   std = 'http://gdata.youtube.com/feeds/api/standardfeeds/'
   e = 'v=2&alt=jsonc&max-results=' + str(ITEMS_PER_PAGE)
   for cat in CATS:
      url = '%stop_rated_%s?%s' % (std, cat, e)
      addItem(1, cat, url, None, action=ACT_FOLDER)

# parse a list of video (jsonc)
elif STATE == 1 or STATE == 4:

   # STATE 4 = search query in place of the url
   if STATE == 4:
      print "search for:" , URL
      URL = 'http://gdata.youtube.com/feeds/api/videos?q=%s&v=2&alt=jsonc&max-results=%d' % (URL, ITEMS_PER_PAGE)

   jsdata = open_url(URL)
   data = json.loads(jsdata)

   for item in data['data']['items']:
      try:
         # see https://developers.google.com/youtube/2.0/developers_guide_jsonc
         author = item['uploader']
         title = item['title']
         desc = item['description']
         rat_max = 5
         rat_avg = item['rating']
         duration = item['duration']
         videoid = item['id']
         viewed = item['viewCount']
         favorited = item['favoriteCount']
         likes = item['likeCount']
         published = item['uploaded']
         url = item['player']['default']
         # if '1' in item['content']:
         #    url = item['content']['5']
         # else:
         #    url = 'restricted'
         #    title += '(RES)'
         poster = item['thumbnail']['hqDefault']
         icon = item['thumbnail']['sqDefault']

         info = '<hilight>Author:</> %s<br>' \
                '<hilight>Published:</> %s<br>' \
                '<hilight>Duration:</> %s<br>' \
                '<hilight>Rating:</> %.1f/%d<br>' \
                '<hilight>Viewed:</> %s  <hilight>Likes: </>+%s<br>' \
                '%s' % \
                (author, published, 
                 seconds_to_time_string(duration),
                 rat_avg, rat_max, viewed, likes,
                 desc.replace('\r\n', '<br>'))

         addItem(3, title, url, info=info, icon=None, poster=poster)

      except:
         addItem(0, 'error parsing data', None)

   total_items = data['data']['totalItems']
   start_index = data['data']['startIndex']

   # more items
   if start_index + ITEMS_PER_PAGE < total_items:
      if 'start-index' in URL:
         URL = re.sub('&start-index=[0-9]+', '', URL)
      URL += '&start-index=%d' % (start_index + ITEMS_PER_PAGE)
      addItem(1, 'more of the %d results...' % (total_items), URL, action=ACT_MORE)

 # try:
      # nextPage = soup.find('span', attrs={'class' : "next"})('a')[1]['href']
      # addItem(1, 'More items...', 'http://www.zapiks.com' + nextPage, icon='icon/next', action=ACT_MORE)
   # except:
      # pass

# parse a list of video (json)
elif STATE == 111: # __UNUSED__
   jsdata = open_url(URL)
   data = json.loads(jsdata)

   # see https://developers.google.com/youtube/2.0/developers_guide_jsonc
   for e in data['feed']['entry']:
      try:
         author = e['author'][0]['name']['$t']
         title = e['title']['$t']
         desc = e['media$group']['media$description']['$t']
         rat_max = e['gd$rating']['max']
         rat_avg = e['gd$rating']['average']
         duration = e['media$group']['yt$duration']['seconds']
         videoid = e['media$group']['yt$videoid']['$t']
         viewed = e['yt$statistics']['viewCount']
         favorited = e['yt$statistics']['favoriteCount']
         likes = e['yt$rating']['numLikes']
         dislikes = e['yt$rating']['numDislikes']
         published = e['published']['$t']

         for media in e['media$group']['media$content']:
            if media['medium'] == 'video' and media['expression'] == 'full':
               if media['yt$format'] == 1:
                  url = media['url']

         for t in e['media$group']['media$thumbnail']:
            if t['yt$name'] == 'default':
               icon = t['url']
            elif t['yt$name'] == 'hqdefault':
               poster = t['url']

         info = '<hilight>Author:</> %s<br>' \
                '<hilight>Published:</> %s<br>' \
                '<hilight>Duration:</> %s<br>' \
                '<hilight>Rating:</> %.1f/%d<br>' \
                '<hilight>Viewed:</> %s  <hilight>Likes: </>+%s -%s<br>' \
                '%s' % \
                (author, published, 
                 seconds_to_time_string(duration),
                 rat_avg, rat_max, viewed, likes, dislikes,
                 desc.replace('\r\n', '<br>'))
         addItem(2, title, url, info=info, icon=None, poster=poster, action=ACT_PLAY)
      except:
         addItem(0, 'error parsing data', None)


# search and play the real video stream from the youtube url
# credit: http://gitorious.org/minitube/minitube/blobs/master/src/video.cpp
elif STATE == 3:
   b = 'http://www.youtube.com/'
   e = '&ps=default&eurl=&gl=US&hl=en'

   # get the video id from the url
   # print '***', URL
   m = re.search('^http://www\\.youtube\\.com/watch\\?v=([0-9A-Za-z_-]+).*', URL)
   video_id = m.group(1)

   # try video_info 1 (el=embedded)
   url = '%sget_video_info?video_id=%s&el=%s%s' %(b, video_id, 'embedded', e)
   videoinfo = open_url(url)
   m = re.search('^.*&token=([^&]+).*$', videoinfo)
   if not m:
      # try video_info 2 (el=vevo)
      url = '%sget_video_info?video_id=%s&el=%s%s' %(b, video_id, 'vevo', e)
      videoinfo = open_url(url)
      m = re.search('^.*&token=([^&]+).*$', videoinfo)
      if not m:
          # try video_info 3 (el=detailpage)
         url = '%sget_video_info?video_id=%s&el=%s%s' %(b, video_id, 'detailpage', e)
         videoinfo = open_url(url)
         m = re.search('^.*&token=([^&]+).*$', videoinfo)
         if not m:
            exit # TODO fixme
   video_token = urllib.unquote(m.group(1))

   # parse video_info response
   m = re.search('^.*&url_encoded_fmt_stream_map=([^&]+).*$', videoinfo)
   formatmap = urllib.unquote(m.group(1))
   L = []
   url_360p = url_720p = url_1080p = None
   for media in formatmap.split(','):
      # print "-----------------------------------------------------"
      itag = -1
      murl = None
      sig = None
      for param in media.split('&'):
         if param.startswith('itag='):
            itag = int(param[5:])
         elif param.startswith('url='):
            murl = urllib.unquote(param[4:])
         elif param.startswith('sig='):
            sig = param[4:]
      if (itag == -1) or (murl is None) or (sig is None):
         continue

      # print "ITAG->",itag
      # print "MURL->",murl
      # print "SIG->",sig
      murl += '&signature=' + sig

      # :/
      if itag == 18: # 360p
         url_360p = murl
      elif itag == 22: # 720p
         url_720p = murl
      elif itag == 37: # 1080p
         url_1080p = murl
      else:
         L.append(murl)

   # choose the wanted resolution :/
   res = 'low' # ini_get('youtube', 'resolution') # low, medium or high
   if url_1080p and res == 'high':
      print "HI"
      playUrl(url_1080p)
   elif url_720p and res in ('medium', 'high'):
      print "MED"
      playUrl(url_720p)
   elif url_360p:
      print "LOW"
      playUrl(url_360p)
   else:
      print "UNKNOWN"
      playUrl(L[0])


   sys.exit(0)
   # now make the list of related videos
   print "ADSASDASDAS"
   url = 'http://gdata.youtube.com/feeds/api/videos/%s/related?v=2&alt=jsonc' % (video_id)
   # print url
   jsdata = open_url(url)
   data = json.loads(jsdata)
   for item in data['data']['items']:
      # print item
      # addItem(2, 'sug1', 'url')
      author = item['uploader']
      title = item['title']
      desc = item['description']
      duration = item['duration']
      videoid = item['id']
      url = item['player']['default']
      poster = item['thumbnail']['hqDefault']
      icon = item['thumbnail']['sqDefault']
# 
      addItem(3, title, url, poster=poster)










   # download the video page
   # html = open_url(URL)

   # extract the video token
   # m = re.search('.*, \"t\": \"([^\"]+)\".*', html)
   # video_token =  m.group(1)

   # print " ", video_id, video_token, formatmap
   # url = 'http://www.youtube.com/get_video?video_id=%s&t=%s&eurl=&el=&ps=&asv=&fmt=%s' % \
         # (video_id, video_token, 18)
   
   # playUrl(url)
