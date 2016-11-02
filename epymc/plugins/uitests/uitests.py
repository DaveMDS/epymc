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

from __future__ import absolute_import, print_function, unicode_literals

import os
import time
import pprint

from efl import ecore, edje, elementary
from efl.elementary.box import Box
from efl.elementary.entry import utf8_to_markup
from efl.evas import EXPAND_BOTH, FILL_BOTH, FILL_HORIZ

from epymc.modules import EmcModule
from epymc.gui import EmcSlider, EmcVKeyboard, EmcFileSelector, EmcButton, \
   EmcDialog, EmcInfoDialog, EmcWarningDialog, EmcErrorDialog, EmcYesNoDialog, \
   EmcConfirmDialog, EmcNotify, EmcMenu, DownloadManager

import epymc.mainmenu as mainmenu
import epymc.utils as utils
import epymc.events as events
import epymc.ini as ini
import epymc.gui as gui
import epymc.mediaplayer as mediaplayer
import epymc.storage as storage
import epymc.browser as browser
from epymc.browser import EmcBrowser, EmcItemClass, FolderItemClass, BackItemClass
from epymc.musicbrainz import MusicBrainz

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
      elif url == 'special_cd':
         return 'special/cd/My album without a cover'
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
      if url == 'uitests://styles':
         return 'Text styles <small>(<b>bold</b> <i>italic</i> <info>info</info> ' \
                '<success>success</success> <failure>failure</failure> <warning>warning</warning>)</small>'
      else:
         return user_data

   def info_get(self, url, user_data):
      if url == 'uitests://styles':
         return TEST_STYLE

   def item_selected(self, url, user_data):

      # Sub-pages
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
         def _cb_menu(menu, item):
            print("Selected item: " + item.text)

         m = EmcMenu()
         m.item_add("Item 1", callback=_cb_menu)
         m.item_add("Item 2", callback=_cb_menu)
         m.item_add("Item 3", callback=_cb_menu)
         m.item_separator_add()
         m.item_add("Item 4", "icon/evas", callback=_cb_menu)
         m.item_add("Item 5", "icon/home", "icon/volume", callback=_cb_menu)
         m.item_separator_add()
         it = m.item_add("Disabled", callback=_cb_menu)
         it.disabled = True
         it = m.item_add("Disabled", 'icon/home', callback=_cb_menu)
         it.disabled = True
         m.item_add("Item 8", None, 'icon/volume', callback=_cb_menu)
         it = m.item_add("Item 9 (disabled)", callback=_cb_menu)
         it.disabled = True
         m.show()

      elif url == 'uitests://menu_long':
         def _cb_menu(menu, item):
            print('Selected item: ' + item.text)

         m = EmcMenu(dismiss_on_select=False)
         for i in range(1, 100):
            m.item_add('Item %d' % i, 'icon/home', 'icon/volume', callback=_cb_menu)
         m.show()

      # TMDB
      # elif url == 'uitests://tmdb':
         # s = TMDB_WithGui()
         # s.movie_search('alien')

      # Download Manager
      elif url == 'uitests://dm':
         DownloadManager().queue_download('http://fredrik.hubbe.net/plugger/xvidtest.avi', 'dm_test1')
         DownloadManager().queue_download('http://www.archive.org/download/TheMakingOfSuzanneVegasSecondLifeGuitar/3-TheMakingOfSuzanneVega_sSecondLifeGuitar.mp4', 'TheMakingOfSuzanneVega')

      elif url == 'uitests://dm2':
         DownloadManager().in_progress_show()

      # Mediaplayer Local Video
      elif url == 'uitests://mpv':
         f = os.path.expanduser('~/Video/testvideo.avi')
         # f = os.path.expanduser('~/Video/testvideo.mp4')
         mediaplayer.play_url(f)#, start_from=0)
         mediaplayer.title_set('Testing title')
         mediaplayer.poster_set('image/dvd_cover_blank.png')

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

      # Mediaplayer DVD
      elif url == 'uitests://dvd':
         mediaplayer.play_url('dvd:///dev/cdrom')
         
      # VKeyboard
      elif url == 'uitests://vkbd':
         EmcVKeyboard(title='Virtual Keyboard', text='This is the keyboard test!',
                      accept_cb=lambda vk, t: print('ACCEPT "%s"' % t),
                      dismiss_cb=lambda vk: print('DISMISS'))

      # File Selector (only folders)
      elif url == 'uitests://folder_sel':
         EmcFileSelector(title='Folder Selector Test',
                         done_cb=lambda p: DBG('Selected: ' + p))

      # File Selector (*)
      elif url == 'uitests://file_sel':
         EmcFileSelector(title='File Selector Test (*)', file_filter='*',
                         done_cb=lambda p: DBG('Selected: ' + p))

      # File Selector (*.jpg|*.png)
      elif url == 'uitests://file_sel_filter':
         EmcFileSelector(title='File Selector Test (*.jpg|*.png)', file_filter='*.jpg|*.png',
                         done_cb=lambda p: DBG('Selected: ' + p))

      # Dialog - Info
      elif url == 'uitests://dlg-info':
         EmcInfoDialog(LOREM)

      # Dialog - Warning
      elif url == 'uitests://dlg-warning':
         EmcWarningDialog('This is an <br><br><b>Warning</><br>dialog<br>')

      # Dialog - Warning (custom title)
      elif url == 'uitests://dlg-warning2':
         EmcWarningDialog('This is an <br><br><b>Warning</><br>dialog<br>',
                          title='Custom warning title')

      # Dialog - Error
      elif url == 'uitests://dlg-error':
         EmcErrorDialog('This is an <br><br><b>Error</><br>dialog<br>')

      # Dialog - Confirm
      elif url == 'uitests://dlg-confirm':
         def _confirm_cb(confirmed, asd_1, asd_2):
            print('Confirmed:', confirmed, 'kargs:', asd_1, asd_2)
         EmcConfirmDialog('This is a <br><br><b>confirmation</><br><br>dialog<br>',
                          _confirm_cb, asd_1='asd1', asd_2='asd2')
      
      # Dialog - YesNo
      elif url == 'uitests://dlg-yesno':
         text = 'This is a <br><br><b>Yes/No</><br><br>dialog<br>'
         EmcYesNoDialog('Dialog - YesNo', text, lambda res: DBG(res),
                        yeslabel='Custom yes label')

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
            d.button_add("btn1", selected_cb=lambda b: print('btn1 callback'))
            d.button_add("btn2", selected_cb=lambda b: print('btn2 callback'))
            d.button_add("btn3", selected_cb=lambda b: print('btn3 callback'))
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
         d.list_item_append('item 3 <b>bold</> <info>info</> <success>success</> <failure>failure</> <i>etc...</>',
                            'icon/star', 'icon/check_on')
         d.list_item_append('item 4', 'icon/tag', 'text/End Text')
         d.list_item_append('item 5', 'icon/tag', 'text/<b>End</> <info>Text</>')
         for i in range(6, 101):
            d.list_item_append('item %d'%i)
         d.list_go()

      # Dialog - Panel full
      elif url == 'uitests://dlg-panel1':
         text = LOREM*4
         d = EmcDialog(title='Dialog - Panel full', text=text, style='panel',
                       spinner=True)
         d.button_add('One', selected_cb=lambda b: print('btn1 callback'))
         d.button_add('Two', selected_cb=lambda b: print('btn2 callback'))
         d.button_add('Tree', selected_cb=lambda b: print('btn3 callback'))

      # Dialog - Panel full more
      elif url == 'uitests://dlg-panel4':
         text = LOREM*8
         
         d = EmcDialog(title='Dialog - Panel full', text=text, style='panel',
                       spinner=False, content=gui.load_image('dvd_cover_blank.png'))
         d.button_add('One', selected_cb=lambda b: print('btn1 callback'))
         d.button_add('Two', selected_cb=lambda b: print('btn2 callback'))
         d.button_add('Tree', selected_cb=lambda b: print('btn3 callback'))

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

      # Buttons Theme + Focus
      elif url == 'uitests://buttons':
         def _buttons_cb(btn):
            print(btn)

         vbox0 = Box(gui.win)
         vbox0.show()

         hbox = Box(gui.win)
         hbox.horizontal_set(True)
         hbox.show()
         vbox0.pack_end(hbox)

         d = EmcDialog(title='button test', content=vbox0, style='panel')

         ### Active buttons
         vbox = Box(gui.win)
         vbox.show()
         # label
         b = EmcButton('only label', cb=_buttons_cb)
         vbox.pack_end(b)
         # icon
         b = EmcButton(icon='icon/star', cb=_buttons_cb)
         vbox.pack_end(b)
         # label + icon
         b = EmcButton('label + icon', 'icon/star', cb=_buttons_cb)
         vbox.pack_end(b)
         hbox.pack_end(vbox)

         ### Disabled buttons
         vbox = Box(gui.win)
         vbox.show()
         # label
         b = EmcButton('only label disabled', cb=_buttons_cb)
         b.disabled_set(True)
         vbox.pack_end(b)
         # icon
         b = EmcButton(icon='icon/mame', cb=_buttons_cb)
         b.disabled_set(True)
         vbox.pack_end(b)
         # label + icon
         b = EmcButton('label + icon disabled', 'icon/back', cb=_buttons_cb)
         b.disabled_set(True)
         vbox.pack_end(b)
         hbox.pack_end(vbox)

         # toggle buttons
         hbox2 = Box(gui.win)
         hbox2.horizontal_set(True)
         hbox2.show()
         b = EmcButton('toggle label', toggle=True, cb=_buttons_cb)
         hbox2.pack_end(b)
         b = EmcButton('toggle label + icon', 'icon/star', toggle=True, cb=_buttons_cb)
         hbox2.pack_end(b)
         b = EmcButton(icon='icon/star', toggle=True, cb=_buttons_cb)
         hbox2.pack_end(b)
         b = EmcButton(icon='icon/star', toggle=True, cb=_buttons_cb)
         b.toggled = True
         hbox2.pack_end(b)
         b = EmcButton('toggle disabled', 'icon/star', toggle=True, cb=_buttons_cb)
         b.disabled_set(True)
         hbox2.pack_end(b)
         vbox0.pack_end(hbox2)

         # 7 butttons in a row (numbers)
         hbox2 = Box(gui.win)
         hbox2.horizontal_set(True)
         hbox2.show()
         for i in range(0,8):
            b = EmcButton(str(i), cb=_buttons_cb)
            hbox2.pack_end(b)
         vbox0.pack_end(hbox2)

         # mediaplayer buttons
         hbox2 = Box(gui.win)
         hbox2.horizontal_set(True)
         hbox2.show()
         icons = ['icon/prev', 'icon/fbwd','icon/bwd','icon/stop','icon/play','icon/fwd','icon/ffwd','icon/next']
         for i in icons:
            b = EmcButton(icon=i, cb=_buttons_cb)
            hbox2.pack_end(b)
         vbox0.pack_end(hbox2)

         # all the icons of the theme in buttons
         i = 0
         for group in edje.file_collection_list(gui.theme_file):
            if group.startswith('icon/'):
               if i % 16 == 0:
                  hbox2 = Box(gui.win, horizontal=True)
                  vbox0.pack_end(hbox2)
                  hbox2.show()
               b = EmcButton(icon=group, cb=_buttons_cb)
               hbox2.pack_end(b)
               i += 1

      # Sliders
      elif url == 'uitests://sliders':
         vbox = Box(gui.win)
         d = EmcDialog(title='Slider test', content=vbox, style='panel')

         # normal
         sl = EmcSlider(vbox, value=0.5, indicator_show=False,
                        size_hint_fill=FILL_HORIZ)
         vbox.pack_end(sl)
         sl.focus = True

         # icons
         sl = EmcSlider(vbox, value=0.5,  indicator_show=False,
                        size_hint_fill=FILL_HORIZ)
         sl.part_content_set('icon', gui.load_icon('icon/evas'))
         sl.part_content_set('end', gui.load_icon('icon/check_on'))
         vbox.pack_end(sl)

         # with text
         sl = EmcSlider(vbox, text='with text', value=0.5, indicator_show=False,
                        size_hint_fill=FILL_HORIZ)
         vbox.pack_end(sl)

         # no focus
         sl = EmcSlider(vbox, text='no focus', value=0.5, indicator_show=False,
                        focus_allow=False, size_hint_fill=FILL_HORIZ)
         vbox.pack_end(sl)

         # unit + indicator format
         sl = EmcSlider(vbox, text='indicator', min_max=(-1.0, 3.0),
                        unit_format='%.2f u', indicator_format='%.1f u',
                        indicator_show_on_focus=True,
                        size_hint_fill=FILL_HORIZ)
         vbox.pack_end(sl)

         # disabled
         sl = EmcSlider(vbox, text='disabled', unit_format='unit', value=0.5,
                        disabled=True, size_hint_fill=FILL_HORIZ)
         vbox.pack_end(sl)

      # Icons gallery
      elif url == 'uitests://icons':
         d = EmcDialog(title='Icons gallery', style='list')
         for group in sorted(edje.file_collection_list(gui.theme_file)):
            if group.startswith('icon/'):
               d.list_item_append(group[5:], group)
         d.list_go()

      # Images gallery
      elif url == 'uitests://imagegal':
         d = EmcDialog(title='Images gallery (names in console)',
                       style='image_list_horiz',
                       done_cb=lambda x, t: print(t))
         for group in sorted(edje.file_collection_list(gui.theme_file)):
            if group.startswith('image/'):
               d.list_item_append(group[6:], group, t=group)
         d.list_go()

      # Text style in dialog
      elif url == 'uitests://styles':
         EmcDialog(title='Text styles', text=TEST_STYLE)

      # Storage devices
      elif url == 'uitests://storage':

         def storage_events_cb(event):
            if event != 'STORAGE_CHANGED':
               return
            dia.list_clear()
            for device in storage.list_devices():
               txt = '{0.label} [ {0.device} ➙ {0.mount_point} ]'.format(device)
               dia.list_item_append(txt, device.icon, device=device)
            dia.list_go()

         def dia_canc_cb(dia):
            events.listener_del('uit_storage')
            dia.delete()

         def dia_sel_cb(dia, device):
            print(device)
            txt = '<small>{}</>'.format(utf8_to_markup(str(device)))
            EmcDialog(style='info', title='Device info', text=txt)

         dia = EmcDialog(title='Storage devices', style='list',
                         done_cb=dia_sel_cb, canc_cb=dia_canc_cb)
         storage_events_cb('STORAGE_CHANGED')
         events.listener_add('uit_storage', storage_events_cb)

      # Music Brainz AudioCD 
      elif url == 'uitests://mbrainz':
         def info_cb(album):
            txt = utf8_to_markup(pprint.pformat(album))
            EmcDialog(title='Result', text='<small>{}</>'.format(txt))

         # musicbrainz.calculate_discid('/dev/sr0')
         MusicBrainz().get_cdrom_info('/dev/cdrom', info_cb, ignore_cache=True)



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
      self._browser = EmcBrowser('UI tests', 'List', 'icon/star')

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
      browser.item_add(MyItemClass(), 'uitests://buttons', 'Buttons + Focus')
      browser.item_add(MyItemClass(), 'uitests://storage', 'Storage devices')
      browser.item_add(MyItemClass(), 'uitests://folder_sel', 'File Selector (folders only)')
      browser.item_add(MyItemClass(), 'uitests://file_sel', 'File Selector (*)')
      browser.item_add(MyItemClass(), 'uitests://file_sel_filter', 'File Selector (*.jpg|*.png)')
      browser.item_add(MyItemClass(), 'uitests://mbrainz', 'Music Brainz AudioCD (/dev/cdrom)')
      browser.item_add(MyItemClass(), 'uitests://menu', 'Menu small (dismiss on select)')
      browser.item_add(MyItemClass(), 'uitests://menu_long', 'Menu long (no dismiss on select)')
      browser.item_add(MyItemClass(), 'uitests://sliders', 'Sliders')
      browser.item_add(MyItemClass(), 'uitests://mpv', 'Mediaplayer - Local Video')
      browser.item_add(MyItemClass(), 'uitests://mpvo', 'Mediaplayer - Online Video (good)')
      browser.item_add(MyItemClass(), 'uitests://mpvom', 'Mediaplayer - Online Video (med)')
      browser.item_add(MyItemClass(), 'uitests://mpvob', 'Mediaplayer - Online Video (bad video)')
      browser.item_add(MyItemClass(), 'uitests://dvd', 'Mediaplayer - DVD Playback (/dev/cdrom)')
      browser.item_add(MyItemClass(), 'uitests://vkbd', 'Virtual Keyboard')
      browser.item_add(MyItemClass(), 'uitests://encoding', 'Various string encoding tests')
      browser.item_add(MyItemClass(), 'uitests://views', 'Browser Views')
      browser.item_add(MyItemClass(), 'uitests://images', 'Browser + EmcImage')
      browser.item_add(MyItemClass(), 'uitests://movies_name', 'Movies name test')
      browser.item_add(MyItemClass(), 'uitests://sniffer', 'Event Sniffer')
      browser.item_add(MyItemClass(), 'uitests://ev_emit', 'Event Emit')
      browser.item_add(MyItemClass(), 'uitests://notify', 'Notify Stack')
      browser.item_add(MyItemClass(), 'uitests://icons', 'Icons gallery')
      browser.item_add(MyItemClass(), 'uitests://imagegal', 'Images gallery')
      browser.item_add(MyItemClass(), 'uitests://styles', 'Text styles')
      browser.item_add(MyItemClass(), 'uitests://dm', 'Download Manager - start')
      browser.item_add(MyItemClass(), 'uitests://dm2', 'Download Manager - show')
      browser.item_add(MyItemClass(), 'uitests://tmdb', 'Themoviedb.org query with gui')
      browser.item_add(MyItemClass(), 'uitests://dlg-info', 'Dialog - Info')
      browser.item_add(MyItemClass(), 'uitests://dlg-warning', 'Dialog - Warning')
      browser.item_add(MyItemClass(), 'uitests://dlg-warning2', 'Dialog - Warning (custom title)')
      browser.item_add(MyItemClass(), 'uitests://dlg-error', 'Dialog - Error')
      browser.item_add(MyItemClass(), 'uitests://dlg-confirm', 'Dialog - Confirm')
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
      _mod._browser.item_add(ImagesItemClass(), 'special_cd', 'Special Compact-disk')
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
