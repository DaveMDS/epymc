#!/usr/bin/env python
#
# Copyright (C) 2010 Davide Andreoli <dave@gurumeditation.it>
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


def DBG(msg):
   print('UITESTS: ' + msg)
   pass


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

      self._browser.item_add('uitests://brdump', 'Dump Browser pages')
      self._browser.item_add('uitests://vkbd', 'Virtual Keyboard')
      self._browser.item_add('uitests://sselector', 'Source Selector')
      self._browser.item_add('uitests://dlg-info', 'Dialog - Info')
      self._browser.item_add('uitests://dlg-warning', 'Dialog - Warning')
      self._browser.item_add('uitests://dlg-error', 'Dialog - Error')
      self._browser.item_add('uitests://dlg-yesno', 'Dialog - YesNo')
      self._browser.item_add('uitests://dlg-cancel', 'Dialog - Cancel')

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

      # VKeyboard
      elif item_url == 'uitests://vkbd':
         DBG('Testing Virtual Keyboard')
         EmcVKeyboard(title = 'Virtual Keyboard', text = 'This is the keyboard test!')

      # Source Selector
      elif item_url == 'uitests://sselector':
         DBG('Testing Source Selector')
         EmcSourceSelector(title = "Source Selector Test")

      # Dialog - Info
      elif item_url == 'uitests://dlg-info':
         DBG('Testing Dialog - Info')
         text = 'This is an <br><br><b>Info</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Info', text = text, style = 'info')

      # Dialog - Warning
      elif item_url == 'uitests://dlg-warning':
         DBG('Testing Dialog - Warning')
         text = 'This is an <br><br><b>Warning</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Info', text = text, style = 'warning')

      # Dialog - Error
      elif item_url == 'uitests://dlg-error':
         DBG('Testing Dialog - Error')
         text = 'This is an <br><br><b>Error</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Error', text = text, style = 'error')

      # Dialog - YesNo
      elif item_url == 'uitests://dlg-yesno':
         DBG('Testing Dialog - YesNo')
         text = 'This is an <br><br><b>Yes/No</><br>dialog<br>'
         EmcDialog(title = 'Dialog - YesNo', text = text, style = 'yesno',
                   done_cb =  (lambda btn: DBG('done')))

      # Dialog - Cancel
      elif item_url == 'uitests://dlg-cancel':
         DBG('Testing Dialog - Cancel')
         text = 'This is an <br><br><b>Cancel operation</><br>dialog<br>'
         EmcDialog(title = 'Dialog - Cancel', text = text, style = 'cancel',
                   spinner = True)

      # Browser Dump
      elif item_url == 'uitests://brdump':
         DBG('Dumping Browser')
         browser.dump_everythings()

