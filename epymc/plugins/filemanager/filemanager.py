#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2014 Davide Andreoli <dave@gurumeditation.it>
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

from __future__ import absolute_import, print_function

# import os

from efl.elementary.list import List

from epymc.modules import EmcModule
from epymc.gui import EXPAND_BOTH, EXPAND_HORIZ, FILL_BOTH, FILL_HORIZ
import epymc.mainmenu as mainmenu
import epymc.input_events as input_events
import epymc.gui as gui

# TODO increment theme generation

def DBG(msg):
   print('FILEMAN: %s' % msg)
   pass

class FilemanList(List):
   def __init__(self):
      # TODO rename style to be more generic
      List.__init__(self, gui.layout, style='fileman', focus_allow=False)
      self.last_focused_item = None

   def focus(self):
      if not self.last_focused_item:
         self.last_focused_item = self.first_item
      self.last_focused_item.selected = True

   def unfocus(self):
      self.last_focused_item = self.selected_item
      self.selected_item.selected = False

   def focus_move(self, direction):
      if direction == 'd':
         if self.selected_item.next:
               self.selected_item.next.selected = True
      elif direction == 'u':
         if self.selected_item.prev:
               self.selected_item.prev.selected = True



class FileManagerModule(EmcModule):
   name = 'filemanager'
   label = _('File Manager')
   icon = 'icon/folder'
   info = _('A two panes filemanager.')

   def __init__(self):
      self.ui_built = False
      self.list1 = None
      self.list2 = None
      self.focused = None
      self.focusman = gui.EmcFocusManager()
      mainmenu.item_add('fileman', 60, _('File Manager'), 'icon/folder',
                        self.cb_mainmenu)

      

   def __shutdown__(self):
      mainmenu.item_del('fileman')

   def cb_mainmenu(self, url=None):
      print("HALO")
      self.build_ui()
      mainmenu.hide()
      gui.signal_emit('fileman,show')
      input_events.listener_add('fileman', self.input_event_cb)
      

   def build_ui(self):
      if self.ui_built:
         return

      b = gui.EmcButton(_('Copy'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      gui.box_append('fileman.buttons.box', b)

      b = gui.EmcButton(_('Move'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      gui.box_append('fileman.buttons.box', b)

      b = gui.EmcButton(_('Rename'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      b.callback_clicked_add(self.bt_rename_cb)
      gui.box_append('fileman.buttons.box', b)

      b = gui.EmcButton(_('Delete'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      gui.box_append('fileman.buttons.box', b)

      b = gui.EmcButton(_('Close'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      b.callback_clicked_add(self.bt_close_cb)
      gui.box_append('fileman.buttons.box2', b)

      li = FilemanList() 
      gui.swallow_set('fileman.list1.swallow', li)
      self.list1 = li

      li = FilemanList()
      gui.swallow_set('fileman.list2.swallow', li)
      self.list2 = li

      # TEST
      for i in range(20):
         self.list1.item_append("File name %d" % i)
         self.list2.item_append("File name %d" % i)

      self.list1.first_item.selected = True
      self.focused = self.list1
      self.focusman.unfocus()
      self.ui_built = True
         
   def bt_rename_cb(self, bt):
      gui.EmcVKeyboard()
      
   def bt_close_cb(self, bt):
      input_events.listener_del('fileman')
      mainmenu.show()
      gui.signal_emit('fileman,hide')
      

   def input_event_cb(self, event):
      DBG(event)
      if event == 'DOWN':
         self.focused.focus_move('d')
            
      if event == 'UP':
         self.focused.focus_move('u')

      if event == 'RIGHT':
         if self.focused == self.list1:
            self.focused = self.focusman
            self.focusman.focus()
            self.list1.unfocus()
         elif self.focused == self.focusman:
            self.focused = self.list2
            self.list2.focus()
            self.focusman.unfocus()

      if event == 'LEFT':
         if self.focused == self.list2:
            self.focused = self.focusman
            self.focusman.focus()
            self.list2.unfocus()
         elif self.focused == self.focusman:
            self.focused = self.list1
            self.list1.focus()
            self.focusman.unfocus()

      # elif event in ('BACK', 'EXIT'):
         # self.close()
         # return input_events.EVENT_CONTINUE
# 
      return input_events.EVENT_BLOCK
