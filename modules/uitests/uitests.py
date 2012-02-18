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

import ecore

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser
from epymc.gui import EmcDialog, EmcVKeyboard, EmcSourceSelector
import epymc.mainmenu as mainmenu
import epymc.utils as utils
import epymc.ini as ini
import epymc.gui as gui
import epymc.browser as browser

from films import TMDB_WithGui


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


class UiTestsModule(EmcModule):
   name = 'uitests'
   label = 'UI tests'
   icon = 'icon/module'
   info = """This module serve as test for the various epymc components."""

   _browser = None

   def __init__(self):
      mainmenu.item_add('uitests', 5, 'UI tests', None, self.cb_mainmenu)
      self._browser = EmcBrowser('UI tests', 'List',
                           item_selected_cb = self.cb_item_selected,
                           poster_get_cb = self.cb_poster_get,
                           info_get_cb = self.cb_info_get)

   def __shutdown__(self):
      mainmenu.item_del('uitests')
      self._browser.delete()

   def cb_mainmenu(self):
      self.make_root_page()
      mainmenu.hide()
      self._browser.show()

   def make_root_page(self):
      self._browser.page_add('uitests://root', 'UI tests')

      self._browser.item_add('uitests://tmdb', 'Themoviedb.org query with gui (need fix for non ascii)')
      self._browser.item_add('uitests://vkbd', 'Virtual Keyboard (need some fixes)')
      self._browser.item_add('uitests://sselector', 'Source Selector')
      self._browser.item_add('uitests://dlg-info', 'Dialog - Info')
      self._browser.item_add('uitests://dlg-warning', 'Dialog - Warning')
      self._browser.item_add('uitests://dlg-error', 'Dialog - Error')
      self._browser.item_add('uitests://dlg-yesno', 'Dialog - YesNo')
      self._browser.item_add('uitests://dlg-cancel', 'Dialog - Cancel')
      self._browser.item_add('uitests://dlg-progress', 'Dialog - Progress')
      self._browser.item_add('uitests://dlg-panel1', 'Dialog - Panel full')
      self._browser.item_add('uitests://dlg-panel2', 'Dialog - Panel no buttons')
      self._browser.item_add('uitests://dlg-panel3', 'Dialog - Panel no title')
      self._browser.item_add('uitests://brdump', 'Dump Browser pages')

   def cb_poster_get(self, page_url, item_url):
      return None

   def cb_info_get(self, page_url, item_url):
      text  = '<title>System info:</><br>'
      text += '<b>base dir</b> %s<br>' % (utils.base_dir_get())
      text += '<b>config dir</b> %s<br>' % (utils.config_dir_get())
      text += '<b>download available</b> %s<br>' % (ecore.file.download_protocol_available("http://"))
      text += '<b>theme</b> %s<br>' % (ini.get('general', 'theme'))
      text += '<b>theme file</b> %s<br>' % (gui.theme_file)
      return text
      
   def cb_item_selected(self, page_url, item_url):

      if item_url == 'uitests://root':
         self.make_root_page()

      # TMDB
      elif item_url == 'uitests://tmdb':
         s = TMDB_WithGui()
         s.movie_search('alien')

      # VKeyboard
      elif item_url == 'uitests://vkbd':
         EmcVKeyboard(title = 'Virtual Keyboard', text = 'This is the keyboard test!')

      # Source Selector
      elif item_url == 'uitests://sselector':
         EmcSourceSelector(title = "Source Selector Test")

      # Dialog - Info
      elif item_url == 'uitests://dlg-info':
         text = 'This is an <br><br><b>Info</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Info', text = text, style = 'info')

      # Dialog - Warning
      elif item_url == 'uitests://dlg-warning':
         text = 'This is an <br><br><b>Warning</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Warning', text = text, style = 'warning')

      # Dialog - Error
      elif item_url == 'uitests://dlg-error':
         text = 'This is an <br><br><b>Error</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Error', text = text, style = 'error')

      # Dialog - YesNo
      elif item_url == 'uitests://dlg-yesno':
         text = 'This is an <br><br><b>Yes/No</><br>dialog<br>'
         EmcDialog(title = 'Dialog - YesNo', text = text, style = 'yesno',
                   done_cb =  (lambda btn: DBG('done')))

      # Dialog - Cancel
      elif item_url == 'uitests://dlg-cancel':
         text = 'This is an <br><br><b>Cancel operation</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Cancel', text = text, style = 'cancel',
                   spinner = True)

      # Dialog - Progress
      elif item_url == 'uitests://dlg-progress':
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
      elif item_url == 'uitests://dlg-panel1':
         text = LOREM
         d = EmcDialog(title = 'Dialog - Panel full', text = text, style = 'panel',
                       spinner = True)
         d.button_add("One")
         d.button_add("Two")
         d.button_add("Tree")

      # Dialog - Panel no buttons
      elif item_url == 'uitests://dlg-panel2':
         text = LOREM
         d = EmcDialog(title = 'Dialog - Panel full', text = text, style = 'panel',
                       spinner = True)

      # Dialog - Panel no title
      elif item_url == 'uitests://dlg-panel3':
         text = LOREM
         d = EmcDialog(text = text, style = 'panel',
                       spinner = True)

      # Browser Dump
      elif item_url == 'uitests://brdump':
         DBG('Dumping Browser')
         browser.dump_everythings()

