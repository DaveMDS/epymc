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

from __future__ import absolute_import, print_function, unicode_literals

import os, time

from efl import ecore, edje, elementary
from efl.elementary.box import Box

from epymc.modules import EmcModule
from epymc.gui import EmcDialog, EmcVKeyboard, EmcFolderSelector, \
   EmcButton, EmcFocusManager, EmcNotify, EmcMenu, DownloadManager

import epymc.mainmenu as mainmenu
import epymc.utils as utils
import epymc.events as events
import epymc.ini as ini
import epymc.gui as gui
import epymc.mediaplayer as mediaplayer
import epymc.browser as browser
from epymc.browser import EmcBrowser, EmcItemClass, FolderItemClass, BackItemClass

# from .movies import TMDB_WithGui, get_movie_name_from_url


def DBG(msg):
   print('UITESTS: %s' % msg)
   pass


LOREM = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vestibulum
consectetur est laoreet est consequat ultricies. Vivamus lectus tellus, egestas
condimentum sollicitudin dictum, congue ac quam. Proin eu erat arcu. Ut tellus
augue, consectetur at lacinia ac, pharetra ornare leo. Quisque ut metus sit
amet risus luctus condimentum. Suspendisse sodales suscipit arcu ut interdum.
Aenean luctus, leo in lacinia pretium, felis odio euismod sapien, eu varius
ipsum odio sit amet elit.
"""

TEST_STYLE = """
<center>
<title>Title</title><br>
<subtitle>Subtitle</><br>
<hilight>hilight</> <b>bold</> <i>italic</> <link>link</><br>
<name>name</> <info>info</> <success>success</> <warning>warning</> <failure>failure</><br>
<bigger>bigger</> <big>big</> normal <small>small</> <smaller>smaller</>
</center>
"""

_mod = None # global module class instance


class EncodingItemClass(EmcItemClass):
   TMDB_API_KEY = '19eef197b81231dff0fd1a14a8d5f863'

   def label_get(self, url, user_data):
      return(user_data)

   def info_get(self, url, user_data):
      from epymc.extapi.onlinevideo import fetch_url, call_ydl, url_encode
      
      if url == 'test1': # tmdb.org json parser
         try:
            url = 'http://api.themoviedb.org/3/movie/129?api_key={}&language=it'.format(self.TMDB_API_KEY)
            data = fetch_url(url, parser='json')
            info = 'Test 1 OK<br>Title: {}<br>Original: {}'.format(data['title'], data['original_title'])
            return info
         except Exception as e:
            return repr(e)

      if url == 'test2': # tmdb.org url encode
         try:
            url = 'http://api.themoviedb.org/3/search/movie/?{}'.format(
                   url_encode({'query':'la città incantata',
                               'api_key':self.TMDB_API_KEY,
                               'language': 'it'}))
            data = fetch_url(url, parser='json')['results'][0]
            info = 'Test 2 OK<br>Title: {}<br>Original: {}'.format(data['title'], data['original_title'])
            return info
         except Exception as e:
            return repr(e)

      if url == 'test3': # tmdb.org virtual keyboard
         def _done_cb(keyb, text):
            try:
               url = 'http://api.themoviedb.org/3/search/movie/?{}'.format(
                      url_encode({'query':text,
                                  'api_key':self.TMDB_API_KEY,
                                  'language': 'it'}))
               data = fetch_url(url, parser='json')['results'][0]
               info = 'Test 3 OK<br>Title: {}<br>Original: {}'.format(data['title'], data['original_title'])
               EmcDialog(title='test3 result', text=info)
            except Exception as e:
               EmcDialog(title='test3 result', text=repr(e))

         EmcVKeyboard(title='Just press Accept!', text='千と千尋の神隠し',
                      accept_cb=_done_cb)

class ImagesItemClass(EmcItemClass):
   path = os.path.dirname(__file__)

   def label_get(self, url, user_data):
      return(user_data)

   def icon_get(self, url, user_data):
      if url == 'special_icon':
         return 'icon/home'

   def poster_get(self, url, user_data):
      if url == 'local_path':
         return os.path.join(self.path, 'menu_bg.png')
      elif url == 'remote_url':
         return 'https://image.tmdb.org/t/p/original/3bKHPDte16BeNLo57W2FwO0jRJZ.jpg', '/tmp/asdasdas'
      elif url == 'remote_url_cache':
         return 'https://image.tmdb.org/t/p/original/cUKn61e7bUUglIGNGBEtzyuCDR4.jpg'
      elif url == 'special_bd':
         return 'special/bd/My super cool movie without a poster'
      elif url == 'special_folder':
         return 'special/folder/This is my special/folder/name <br>' \
                '(can also include "/" and other special chars)<br>' \
                'àèìòù<br>నాన్నకు ప్రేమతో<br>もののけ姫<br><br>...and tags:<br>' \
                + TEST_STYLE
      elif url == 'special_null':
         return None
      #TODO failure for local and remote

class ViewsItemClass(EmcItemClass):
   path = os.path.dirname(__file__)

   def label_get(self, url, user_data):
      return user_data

   def label_end_get(self, url, user_data):
      if url in ('two_labels', 'two_labels_one_icon', 'two_labels_two_icon'):
         return 'second'

   def info_get(self, url, user_data):
      return '<title>Testing:</title><br>' + user_data

   def icon_get(self, url, user_data):
      if url in ('one_icon', 'two_icons', 'two_labels_one_icon', 'two_labels_two_icon'):
         return 'icon/home'
      if url in ('poster', 'cover', 'poster_cover'):
         return 'icon/views'

   def icon_end_get(self, url, user_data):
      if url in ('two_icons', 'two_labels_two_icon'):
         return 'icon/evas'

   def poster_get(self, url, user_data):
      if url in ('poster', 'poster_cover'):
         return os.path.join(self.path, 'poster.jpg')

   def cover_get(self, url, user_data):
      if url in ('cover', 'poster_cover'):
         return os.path.join(self.path, 'cover.jpg')
         

class MyItemClass(EmcItemClass):

   def label_get(self, url, user_data):
      return user_data

   def info_get(self, url, user_data):
      if url == 'uitests://styles':
         return TEST_STYLE

   def item_selected(self, url, user_data):
      
      if url == 'uitests://encoding':
         _mod._browser.page_add('uitests://encoding', 'Encoding tests', None,
                                _mod.populate_encoding_page)

      elif url == 'uitests://images':
         _mod._browser.page_add('uitests://images', 'Image tests',
                                ('List', 'PosterGrid'),
                                _mod.populate_image_page)

      elif url == 'uitests://views':
         _mod._browser.page_add('uitests://views', 'Browser Views',
                                ('List', 'PosterGrid', 'CoverGrid'),
                                _mod.populate_views_page)

      # Events Sniffer
      elif url == 'uitests://sniffer':
         events.listener_add('sniffer', lambda ev: EmcNotify('<title>Event sniffer</><br>' + ev))
         n = EmcNotify('Sniffer enabled.', hidein = 2)

      # Event Emit
      elif url == 'uitests://ev_emit':
         events.event_emit('TEST_EVENT')

      # Notify
      elif url == 'uitests://notify':
         EmcNotify('<title>Title 1</><br>' \
             'Without icon.<br>' \
             'Will hide in 10 seconds.',
              hidein=20)
         EmcNotify('<title>Title 2</><br>' \
             'This one with an image.',
              icon = 'dvd_cover_blank.png')
         EmcNotify('<title>Title 3</><br>' \
             'This one with an icon',
              icon = 'icon/movie')
         EmcNotify('<title>Title 4</><br>' \
             'Test longer text and tags.<br>' \
             '<b>bold</b> <i>italic</i> <u>underline</u> <link>link</link> ' \
             '<info>info</info> <success>success</success> ' \
             '<warning>warning</warning> <failure>failure</failure>.',
              icon = 'icon/movie')

      # Menu
      elif url == 'uitests://menu':
         def _cb_menu(menu, item, name):
            print("Selected item: " + name)

         m = EmcMenu()
         m.item_add(None, "Item 1", None, _cb_menu, "item1")
         m.item_add(None, "Item 2", None, _cb_menu, "item2")
         m.item_add(None, "Item 3", None, _cb_menu, "item3")
         m.item_separator_add()
         m.item_add(None, "Item 4", "clock", _cb_menu, "item4")
         m.item_add(None, "Item 5", "home", _cb_menu, "item5")
         m.item_separator_add()
         it = m.item_add(None, "Disabled", None, _cb_menu, "disabled")
         it.disabled = True
         it = m.item_add(None, "Disabled", 'home', _cb_menu, "disabled2")
         it.disabled = True
         m.item_add(None, "Item 7", None, _cb_menu, "item7")
         it = m.item_add(None, "Item 8 (disabled)", None, _cb_menu, "item8")
         it.disabled = True

      # TMDB
      # elif url == 'uitests://tmdb':
         # s = TMDB_WithGui()
         # s.movie_search('alien')

      # Download Manager
      elif url == 'uitests://dm':
         DownloadManager().queue_download('http://fredrik.hubbe.net/plugger/xvidtest.avi', 'dm_test1')
         DownloadManager().queue_download('http://www.archive.org/download/TheMakingOfSuzanneVegasSecondLifeGuitar/3-TheMakingOfSuzanneVega_sSecondLifeGuitar.mp4', 'TheMakingOfSuzanneVega')
         

      # Mediaplayer Local Video
      elif url == 'uitests://mpv':
         f = os.path.expanduser('~/Video/testvideo.avi')
         mediaplayer.play_url(f, start_from=0)
         mediaplayer.title_set('Testing title')
         mediaplayer.poster_set('dvd_cover_blank.png')

      # Mediaplayer Online Video (good)
      # elif url == 'uitests://mpvo':
         # mediaplayer.play_url('http://trailers.apple.com/movies/independent/airracers/airracers-tlr1_h480p.mov')

      # http://samples.mplayerhq.hu/
      # http://download.wavetlan.com/SVV/Media/HTTP/http-mp4.htm
      
      # Mediaplayer Online Video (med)
      elif url == 'uitests://mpvom':
         mediaplayer.play_url('http://fredrik.hubbe.net/plugger/xvidtest.avi')

      # Mediaplayer Online Video (bad)
      elif url == 'uitests://mpvob':
         mediaplayer.play_url('http://www.archive.org/download/TheMakingOfSuzanneVegasSecondLifeGuitar/3-TheMakingOfSuzanneVega_sSecondLifeGuitar.mp4')

      # VKeyboard
      elif url == 'uitests://vkbd':
         EmcVKeyboard(title='Virtual Keyboard', text='This is the keyboard test!')

      # Source Selector
      elif url == 'uitests://sselector':
         EmcFolderSelector(title='Source Selector Test',
                           done_cb=lambda p: DBG('Selected: ' + p))

      # Dialog - Info
      elif url == 'uitests://dlg-info':
         EmcDialog(title='Dialog - Info', text=LOREM, style='info')

      # Dialog - Warning
      elif url == 'uitests://dlg-warning':
         text = 'This is an <br><br><b>Warning</><br>dialog<br>'
         EmcDialog(title='Dialog - Warning', text=text, style='warning')

      # Dialog - Warning (no title)
      elif url == 'uitests://dlg-warning2':
         text = 'This is an <br><br><b>Warning</><br>dialog<br>'
         EmcDialog(text=text, style='warning')

      # Dialog - Error
      elif url == 'uitests://dlg-error':
         text = 'This is an <br><br><b>Error</><br>dialog<br>'
         EmcDialog(title='Dialog - Error', text=text, style='error')

      # Dialog - YesNo
      elif url == 'uitests://dlg-yesno':
         text = 'This is an <br><br><b>Yes/No</><br>dialog<br>'
         EmcDialog(title='Dialog - YesNo', text=text, style='yesno',
                   done_cb=lambda btn: DBG('done'))

      # Dialog - Cancel
      elif url == 'uitests://dlg-cancel':
         text = 'This is an <br><br><b>Cancel operation</><br>dialog<br>'
         EmcDialog(title='Dialog - Cancel', text=text, style='cancel',
                   spinner=True)

      # Dialog - Progress
      elif url.startswith('uitests://dlg-progress'):
         def _canc_cb(dialog):
            t.delete()
            d.delete()

         def _progress_timer():
            d.progress_set(self._progress)
            self._progress += 0.01
            if self._progress > 1: self._progress = 0;
            return True # renew the callback

         text = 'This is a <br><br><b>Progress operation</><br>dialog<br>'
         d = EmcDialog(title='Dialog - Progress', text=text,
                       style='progress', done_cb=_canc_cb, canc_cb=_canc_cb)
         if url.endswith('btn'):
            d.button_add("btn1")
            d.button_add("btn2")
            d.button_add("btn3")
         self._progress = 0.0
         t = ecore.Timer(0.2, _progress_timer)

      # Dialog - List
      elif url == 'uitests://dlg-list':
         def _dia_list_cb(dia):
            item = dia.list_item_selected_get()
            print('Selected: ' + str(item))
            # dia.delete()
         d = EmcDialog(title='Dialog - List', style='list', done_cb=_dia_list_cb)
         d.list_item_append('item 1', 'icon/home')
         d.list_item_append('item 2', 'icon/star', 'icon/check_on')
         for i in range(3, 101):
            d.list_item_append('item %d'%i)
         d.list_go()

      # Dialog - Panel full
      elif url == 'uitests://dlg-panel1':
         text = LOREM*4
         d = EmcDialog(title='Dialog - Panel full', text=text, style='panel',
                       spinner=True)
         d.button_add('One')
         d.button_add('Two')
         d.button_add('Tree')

      # Dialog - Panel full more
      elif url == 'uitests://dlg-panel4':
         text = LOREM*8
         
         d = EmcDialog(title='Dialog - Panel full', text=text, style='panel',
                       spinner=False, content=gui.load_image('dvd_cover_blank.png'))
         d.button_add('One')
         d.button_add('Two')
         d.button_add('Tree')

      # Dialog - Panel no buttons
      elif url == 'uitests://dlg-panel2':
         text = LOREM
         d = EmcDialog(title='Dialog - Panel full', text=text, style='panel',
                       spinner=True)

      # Dialog - Panel no title
      elif url == 'uitests://dlg-panel3':
         text = LOREM
         d = EmcDialog(text=text, style='panel', spinner=True)

      # Dialog - Buffering
      elif url == 'uitests://dlg-buffering':
         def _progress_timer2():
            self._progress += 0.05
            d.progress_set(self._progress)
            if self._progress >= 1.0:
               d.delete()
               return False # stop the timer
            else:
               return True # renew the callback

         d = EmcDialog(style='buffering', title=_('Buffering'))
         self._progress = 0.0
         ecore.Timer(0.2, _progress_timer2)

      # Browser Dump
      elif url == 'uitests://brdump':
         DBG('Dumping Browser')
         browser.dump_everythings()

      # Buttons Theme
      elif url == 'uitests://buttons':
         vbox0 = Box(gui.win)
         vbox0.show()

         hbox = Box(gui.win)
         hbox.horizontal_set(True)
         hbox.show()
         vbox0.pack_end(hbox)

         def _dialog_close_cb(dialog):
            fman.delete()
            dialog.delete()
         d = EmcDialog(title='button test', content=vbox0, style='panel',
                       done_cb=_dialog_close_cb, canc_cb=_dialog_close_cb)
         fman = EmcFocusManager('uitest-buttons')

         ### Active buttons
         vbox = Box(gui.win)
         vbox.show()
         # label
         b = EmcButton('only label')
         fman.obj_add(b)
         vbox.pack_end(b)
         # icon
         b = EmcButton(None, 'icon/star')
         fman.obj_add(b)
         vbox.pack_end(b)
         # label + icon
         b = EmcButton('label + icon', 'icon/star')
         fman.obj_add(b)
         vbox.pack_end(b)
         hbox.pack_end(vbox)

         ### Disabled buttons
         vbox = Box(gui.win)
         vbox.show()
         # label
         b = EmcButton('only label disabled')
         b.disabled_set(True)
         fman.obj_add(b)
         vbox.pack_end(b)
         # icon
         b = EmcButton(None, 'icon/mame')
         b.disabled_set(True)
         fman.obj_add(b)
         vbox.pack_end(b)
         # label + icon
         b = EmcButton('label + icon disabled', 'icon/back')
         b.disabled_set(True)
         fman.obj_add(b)
         vbox.pack_end(b)
         hbox.pack_end(vbox)

         # 7 butttons in a row (labels)
         hbox2 = Box(gui.win)
         hbox2.horizontal_set(True)
         hbox2.show()
         for i in range(0,8):
            b = EmcButton(str(i))
            fman.obj_add(b)
            b.show()
            hbox2.pack_end(b)
         vbox0.pack_end(hbox2)

         # mediaplayer buttons
         hbox2 = Box(gui.win)
         hbox2.horizontal_set(True)
         hbox2.show()
         icons = ['icon/fbwd','icon/bwd','icon/stop','icon/play','icon/fwd','icon/ffwd']
         for i in icons:
            b = EmcButton(None, i)
            fman.obj_add(b)
            hbox2.pack_end(b)
         vbox0.pack_end(hbox2)

         # all the icons of the theme in buttons
         i = 0
         for group in edje.file_collection_list(gui.theme_file):
            if group.startswith('icon/'):
               if i % 12 == 0:
                  hbox2 = Box(gui.win, horizontal=True)
                  vbox0.pack_end(hbox2)
                  hbox2.show()
               b = EmcButton(None, group)
               fman.obj_add(b)
               hbox2.pack_end(b)
               i += 1

      # Icons gallery
      elif url == 'uitests://icons':
         d = EmcDialog(title='Icons gallery', style='list')
         for group in sorted(edje.file_collection_list(gui.theme_file)):
            if group.startswith('icon/'):
               d.list_item_append(group[5:], group)
         d.list_go()

      # Text style in dialog
      elif url == 'uitests://styles':
         EmcDialog(title='Text styles', text=TEST_STYLE)
   
      # Movie name test
      # elif url == 'uitests://movies_name':
         # urls = [ 'alien.avi',
                  # 'alien (1978).avi',
                  # '(2003)alien 3.avi',
                  # '[DivX - ITA] alien 3.avi',
                  # '[DivX - ITA] ali]en 3.avi',
                  # '[DivX - ITA] al[i]en 3.avi',
                  # '[DivX - ITA]alien3.avi',
                  # '[DivX - ITA]   alien3   .avi',
                  # '[DivX - ITA]alien.3.la.clonazione.avi',
                  # '[DivX - ITA]alien 3 - la clonazione.avi',
                  # '{DivX - ITA} alien 3.avi',
                  # 'alien {DivX - ITA}.avi',
                  # '[DivX - ITA] Die Hard I - Trappola di Cristallo.avi',
                # ]
         # t = ''
         # for u in urls:
            # t += '<hilight>URL:</> ' + u + '<br>'
            # t += '<hilight>name/year:</> ' + str(get_movie_name_from_url(u)) + '<br><br>'
         # EmcDialog(title = 'Movie name test', text = t)


class UiTestsModule(EmcModule):
   name = 'uitests'
   label = 'UI tests'
   icon = 'icon/star'
   info = 'This module serve as test for the various epymc components.'
   path = os.path.dirname(__file__)

   _browser = None

   def __init__(self):
      img = os.path.join(self.path, 'menu_bg.png')
      mainmenu.item_add('uitests', 3, 'UI tests', img, self.cb_mainmenu)
      self._browser = EmcBrowser('UI tests', 'List')

      global _mod
      _mod = self

   def __shutdown__(self):
      mainmenu.item_del('uitests')
      self._browser.delete()

   def cb_mainmenu(self):
      self._browser.page_add('uitests://root', 'UI tests', None, self.populate_root)
      mainmenu.hide()
      self._browser.show()

   def populate_root(self, browser, url):
      browser.item_add(MyItemClass(), 'uitests://encoding', 'Various string encoding tests')
      browser.item_add(MyItemClass(), 'uitests://views', 'Browser Views')
      browser.item_add(MyItemClass(), 'uitests://images', 'Browser + EmcImage')
      browser.item_add(MyItemClass(), 'uitests://movies_name', 'Movies name test')
      browser.item_add(MyItemClass(), 'uitests://sniffer', 'Event Sniffer')
      browser.item_add(MyItemClass(), 'uitests://ev_emit', 'Event Emit')
      browser.item_add(MyItemClass(), 'uitests://notify', 'Notify Stack')
      browser.item_add(MyItemClass(), 'uitests://menu', 'Menu')
      browser.item_add(MyItemClass(), 'uitests://buttons', 'Buttons + FocusManager')
      browser.item_add(MyItemClass(), 'uitests://icons', 'Icons gallery')
      browser.item_add(MyItemClass(), 'uitests://styles', 'Text styles')
      browser.item_add(MyItemClass(), 'uitests://dm', 'Download Manager')
      browser.item_add(MyItemClass(), 'uitests://mpv', 'Mediaplayer - Local Video')
      browser.item_add(MyItemClass(), 'uitests://mpvo', 'Mediaplayer - Online Video (good)')
      browser.item_add(MyItemClass(), 'uitests://mpvom', 'Mediaplayer - Online Video (med)')
      browser.item_add(MyItemClass(), 'uitests://mpvob', 'Mediaplayer - Online Video (bad video)')
      browser.item_add(MyItemClass(), 'uitests://tmdb', 'Themoviedb.org query with gui')
      browser.item_add(MyItemClass(), 'uitests://vkbd', 'Virtual Keyboard')
      browser.item_add(MyItemClass(), 'uitests://sselector', 'Source Selector')
      browser.item_add(MyItemClass(), 'uitests://dlg-info', 'Dialog - Info')
      browser.item_add(MyItemClass(), 'uitests://dlg-warning', 'Dialog - Warning')
      browser.item_add(MyItemClass(), 'uitests://dlg-warning2', 'Dialog - Warning (no title)')
      browser.item_add(MyItemClass(), 'uitests://dlg-error', 'Dialog - Error')
      browser.item_add(MyItemClass(), 'uitests://dlg-yesno', 'Dialog - YesNo')
      browser.item_add(MyItemClass(), 'uitests://dlg-cancel', 'Dialog - Cancel')
      browser.item_add(MyItemClass(), 'uitests://dlg-progress', 'Dialog - Progress')
      browser.item_add(MyItemClass(), 'uitests://dlg-progress-btn', 'Dialog - Progress with buttons')
      browser.item_add(MyItemClass(), 'uitests://dlg-list', 'Dialog - List')
      browser.item_add(MyItemClass(), 'uitests://dlg-panel1', 'Dialog - Panel full')
      browser.item_add(MyItemClass(), 'uitests://dlg-panel4', 'Dialog - Panel full more')
      browser.item_add(MyItemClass(), 'uitests://dlg-panel2', 'Dialog - Panel no buttons')
      browser.item_add(MyItemClass(), 'uitests://dlg-panel3', 'Dialog - Panel no title')
      browser.item_add(MyItemClass(), 'uitests://dlg-buffering', 'Dialog - Buffering')
      browser.item_add(MyItemClass(), 'uitests://brdump', 'Dump Browser pages')

   def populate_encoding_page(self, browser, url):
      _mod._browser.item_add(EncodingItemClass(), 'test1', 'Test 1: tmdb.org json parser')
      _mod._browser.item_add(EncodingItemClass(), 'test2', 'Test 2: tmdb.org url encode')
      _mod._browser.item_add(EncodingItemClass(), 'test3', 'Test 3: tmdb.org virtual keyboard')

   def populate_image_page(self, browser, url):
      _mod._browser.item_add(ImagesItemClass(), 'local_path', 'From a local path')
      _mod._browser.item_add(ImagesItemClass(), 'remote_url', 'From a remote url (with local dest)')
      _mod._browser.item_add(ImagesItemClass(), 'remote_url_cache', 'From a remote url (with auto cache)')
      _mod._browser.item_add(ImagesItemClass(), 'special_folder', 'Special Folder')
      _mod._browser.item_add(ImagesItemClass(), 'special_bd', 'Special Blu-ray')
      _mod._browser.item_add(ImagesItemClass(), 'special_icon', 'Special Icon (in PosterGrid view)')
      _mod._browser.item_add(ImagesItemClass(), 'special_null', 'Special Null (transparent)')

   def populate_views_page(self, browser, url):
      _mod._browser.item_add(BackItemClass(), 'back', 'special BackItemClass')
      _mod._browser.item_add(FolderItemClass(), 'folder', 'special FolderItemClass')
      _mod._browser.item_add(ViewsItemClass(), 'one_label', 'one label')
      _mod._browser.item_add(ViewsItemClass(), 'one_icon', 'one icon')
      _mod._browser.item_add(ViewsItemClass(), 'two_icons', 'two icons')
      _mod._browser.item_add(ViewsItemClass(), 'two_labels', 'two labels')
      _mod._browser.item_add(ViewsItemClass(), 'two_labels_one_icon', 'two labels + one icon')
      _mod._browser.item_add(ViewsItemClass(), 'two_labels_two_icon', 'two labels + two icon')
      _mod._browser.item_add(ViewsItemClass(), 'poster', 'with poster only')
      _mod._browser.item_add(ViewsItemClass(), 'cover', 'with cover only')
      _mod._browser.item_add(ViewsItemClass(), 'poster_cover', 'with poster and cover')
