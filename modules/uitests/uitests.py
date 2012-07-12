#!/usr/bin/env python
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

import os

import ecore, elementary

from epymc.modules import EmcModule
from epymc.gui import EmcDialog, EmcVKeyboard, EmcSourceSelector
from epymc.gui import EmcButton, EmcFocusManager2, EmcNotify
import epymc.mainmenu as mainmenu
import epymc.utils as utils
import epymc.ini as ini
import epymc.gui as gui
import epymc.mediaplayer as mediaplayer
from films import TMDB_WithGui
import epymc.browser3 as browser3
from epymc.browser3 import EmcBrowser3, EmcItemClass


def DBG(msg):
   print('UITESTS: ' + msg)
   pass


LOREM = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vestibulum
consectetur est laoreet est consequat ultricies. Vivamus lectus tellus, egestas
condimentum sollicitudin dictum, congue ac quam. Proin eu erat arcu. Ut tellus
augue, consectetur at lacinia ac, pharetra ornare leo. Quisque ut metus sit
amet risus luctus condimentum. Suspendisse sodales suscipit arcu ut interdum.
Aenean luctus, leo in lacinia pretium, felis odio euismod sapien, eu varius
ipsum odio sit amet elit. Proin porta lectus sit amet ipsum pretium posuere.
<br><br>Sed vel nisi vitae est ultricies ullamcorper sed non purus. Donec porta
diam sed nulla volutpat non pretium ipsum lobortis. Donec quam mauris, porta
sit amet congue a, mollis et nulla. Nulla facilisi. In augue eros, elementum
quis interdum sed, tristique et dolor. Nam eget tempor nisi. Curabitur
sollicitudin fermentum tortor, at commodo ipsum egestas sit amet. Lorem ipsum
dolor sit amet, consectetur adipiscing elit. In urna neque, malesuada et
tempus ac, adipiscing et sapien. Ut arcu tellus, molestie sit amet feugiat
a, faucibus at dui. Aenean posuere ligula tellus. Cras interdum sollicitudin
posuere. Donec laoreet pretium purus malesuada rhoncus. Sed pulvinar volutpat
vulputate. 
"""


class MyItemClass(EmcItemClass):

   def label_get(self, url, user_data):
      return user_data

   def info_get(self, url, user_data):
      text  = '<title>System info:</><br>'
      text += '<b>Graphic engine</b> %s (%s)<br>' % (elementary.engine_get(), elementary.preferred_engine_get())
      text += '<b>base dir</b> %s<br>' % (utils.base_dir_get())
      text += '<b>config dir</b> %s<br>' % (utils.config_dir_get())
      text += '<b>download available</b> %s<br>' % (ecore.file.download_protocol_available('http://'))
      text += '<b>theme</b> %s<br>' % (ini.get('general', 'theme'))
      text += '<b>theme file</b> %s<br>' % (gui.theme_file)
      return text

   def item_selected(self, url, user_data):
      # Notify
      if url == 'uitests://notify':
         n = EmcNotify('<b>TITLE</b><br>maybe some other texts..')

      # TMDB
      elif url == 'uitests://tmdb':
         s = TMDB_WithGui()
         s.movie_search('alien')

      # Mediaplayer Local Video
      elif url == 'uitests://mpv':
         f = os.path.expanduser('~/Video/testvideo.avi')
         mediaplayer.play_video(f)
         mediaplayer.title_set('Testing title')
         mediaplayer.poster_set('dvd_cover_blank.png', self.path)

      # Mediaplayer Online Video (good)
      # elif url == 'uitests://mpvo':
         # mediaplayer.play_video('http://trailers.apple.com/movies/independent/airracers/airracers-tlr1_h480p.mov')

      # Mediaplayer Online Video (bad)
      elif url == 'uitests://mpvob':
         mediaplayer.play_video('http://www.archive.org/download/TheMakingOfSuzanneVegasSecondLifeGuitar/3-TheMakingOfSuzanneVega_sSecondLifeGuitar.mp4')

      # VKeyboard
      elif url == 'uitests://vkbd':
         EmcVKeyboard(title = 'Virtual Keyboard', text = 'This is the keyboard test!')

      # Source Selector
      elif url == 'uitests://sselector':
         EmcSourceSelector(title = 'Source Selector Test')

      # Dialog - Info
      elif url == 'uitests://dlg-info':
         text = 'This is an <br><br><b>Info</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Info', text = text, style = 'info')

      # Dialog - Warning
      elif url == 'uitests://dlg-warning':
         text = 'This is an <br><br><b>Warning</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Warning', text = text, style = 'warning')

      # Dialog - Error
      elif url == 'uitests://dlg-error':
         text = 'This is an <br><br><b>Error</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Error', text = text, style = 'error')

      # Dialog - YesNo
      elif url == 'uitests://dlg-yesno':
         text = 'This is an <br><br><b>Yes/No</><br>dialog<br>'
         EmcDialog(title = 'Dialog - YesNo', text = text, style = 'yesno',
                   done_cb =  (lambda btn: DBG('done')))

      # Dialog - Cancel
      elif url == 'uitests://dlg-cancel':
         text = 'This is an <br><br><b>Cancel operation</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Cancel', text = text, style = 'cancel',
                   spinner = True)

      # Dialog - Progress
      elif url == 'uitests://dlg-progress':
         def _canc_cb(dialog):
            t.delete()
            d.delete()

         def _progress_timer():
            d.progress_set(self._progress)
            self._progress += 0.01
            if self._progress > 1: self._progress = 0;
            return True # renew the callback

         text = 'This is a <br><br><b>Progress operation</><br>dialog<br>'
         d = EmcDialog(title = 'Dialog - Progress', text = text,
                         style = 'progress', canc_cb = _canc_cb)
         self._progress = 0.0
         d.progress_set(self._progress)
         t = ecore.Timer(0.2, _progress_timer)

      # Dialog - Panel full
      elif url == 'uitests://dlg-panel1':
         text = LOREM
         d = EmcDialog(title = 'Dialog - Panel full', text = text, style = 'panel',
                       spinner = True)
         d.button_add('One')
         d.button_add('Two')
         d.button_add('Tree')

      # Dialog - Panel no buttons
      elif url == 'uitests://dlg-panel2':
         text = LOREM
         d = EmcDialog(title = 'Dialog - Panel full', text = text, style = 'panel',
                       spinner = True)

      # Dialog - Panel no title
      elif url == 'uitests://dlg-panel3':
         text = LOREM
         d = EmcDialog(text = text, style = 'panel',
                       spinner = True)

      # Browser Dump
      elif url == 'uitests://brdump':
         DBG('Dumping Browser')
         browser3.dump_everythings()

      # Buttons Theme
      elif url == 'uitests://buttons':
         vbox0 = elementary.Box(gui.win)
         vbox0.show()

         hbox = elementary.Box(gui.win)
         hbox.horizontal_set(True)
         hbox.show()
         vbox0.pack_end(hbox)

         def _dialog_close_cb(dialog):
            fman.delete()
            dialog.delete()
         d = EmcDialog(title='button test', content=vbox0,
                       style='panel', canc_cb=_dialog_close_cb)
         fman = EmcFocusManager2('uitest-buttons')

         ### Active buttons
         vbox = elementary.Box(gui.win)
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
         vbox = elementary.Box(gui.win)
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
         hbox2 = elementary.Box(gui.win)
         hbox2.horizontal_set(True)
         hbox2.show()
         for i in xrange(0,8):
            b = EmcButton(str(i))
            fman.obj_add(b)
            b.show()
            hbox2.pack_end(b)
         vbox0.pack_end(hbox2)

         # 7 butttons in a row (icons)
         hbox2 = elementary.Box(gui.win)
         hbox2.horizontal_set(True)
         hbox2.show()
         icons = ['icon/star','icon/home','icon/folder']
         for i in xrange(0,8):
            b = EmcButton(None, icons[i % len(icons)])
            fman.obj_add(b)
            hbox2.pack_end(b)
         vbox0.pack_end(hbox2)

         # mediaplayer buttons
         hbox2 = elementary.Box(gui.win)
         hbox2.horizontal_set(True)
         hbox2.show()
         icons = ['icon/fbwd','icon/bwd','icon/stop','icon/play','icon/fwd','icon/ffwd']
         for i in icons:
            b = EmcButton(None, i)
            fman.obj_add(b)
            hbox2.pack_end(b)
         vbox0.pack_end(hbox2)


class UiTestsModule(EmcModule):
   name = 'uitests'
   label = 'UI tests'
   icon = 'icon/module'
   info = """This module serve as test for the various epymc components."""
   path = os.path.dirname(__file__)

   _browser = None

   def __init__(self):
      img = os.path.join(self.path, 'menu_bg.png')
      mainmenu.item_add('uitests', 5, 'UI tests', img, self.cb_mainmenu)
      self._browser = EmcBrowser3('UI tests', 'List')

   def __shutdown__(self):
      mainmenu.item_del('uitests')
      self._browser.delete()

   def cb_mainmenu(self):
      self._browser.page_add('uitests://root', 'UI tests', None, self.populate_root)
      mainmenu.hide()
      self._browser.show()

   def populate_root(self, browser, url):
      browser.item_add(MyItemClass(), 'uitests://notify', 'Notify Stack')
      browser.item_add(MyItemClass(), 'uitests://buttons', 'Buttons + FocusManager')
      browser.item_add(MyItemClass(), 'uitests://mpv', 'Mediaplayer - Local Video')
      browser.item_add(MyItemClass(), 'uitests://mpvo', 'Mediaplayer - Online Video (good)')
      browser.item_add(MyItemClass(), 'uitests://mpvob', 'Mediaplayer - Online Video (bad video)')
      browser.item_add(MyItemClass(), 'uitests://tmdb', 'Themoviedb.org query with gui (need fix for non ascii)')
      browser.item_add(MyItemClass(), 'uitests://vkbd', 'Virtual Keyboard')
      browser.item_add(MyItemClass(), 'uitests://sselector', 'Source Selector')
      browser.item_add(MyItemClass(), 'uitests://dlg-info', 'Dialog - Info')
      browser.item_add(MyItemClass(), 'uitests://dlg-warning', 'Dialog - Warning')
      browser.item_add(MyItemClass(), 'uitests://dlg-error', 'Dialog - Error')
      browser.item_add(MyItemClass(), 'uitests://dlg-yesno', 'Dialog - YesNo')
      browser.item_add(MyItemClass(), 'uitests://dlg-cancel', 'Dialog - Cancel')
      browser.item_add(MyItemClass(), 'uitests://dlg-progress', 'Dialog - Progress')
      browser.item_add(MyItemClass(), 'uitests://dlg-panel1', 'Dialog - Panel full')
      browser.item_add(MyItemClass(), 'uitests://dlg-panel2', 'Dialog - Panel no buttons')
      browser.item_add(MyItemClass(), 'uitests://dlg-panel3', 'Dialog - Panel no title')
      browser.item_add(MyItemClass(), 'uitests://brdump', 'Dump Browser pages')
