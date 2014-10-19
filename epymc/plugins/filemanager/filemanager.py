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

import os

from efl.elementary.list import List

from epymc.modules import EmcModule
from epymc.gui import EXPAND_BOTH, EXPAND_HORIZ, FILL_BOTH, FILL_HORIZ
import epymc.mainmenu as mainmenu
import epymc.input_events as input_events
import epymc.utils as utils
import epymc.gui as gui
import epymc.ini as ini

# TODO increment theme generation

def DBG(msg):
   print('FILEMAN: %s' % msg)
   pass


class FilemanList(List):
   def __init__(self):
      # TODO rename style to be more generic
      List.__init__(self, gui.layout, style='fileman', focus_allow=False)
      self.last_focused_item = None
      self.callback_activated_add(self.item_activated_cb)

   def focus(self):
      if not self.last_focused_item:
         self.last_focused_item = self.first_item
      self.last_focused_item.selected = True

   def unfocus(self):
      if self.selected_item:
         self.last_focused_item = self.selected_item
         self.selected_item.selected = False

   def focus_move(self, direction):
      if direction == 'd':
         if self.selected_item.next:
               self.selected_item.next.selected = True
      elif direction == 'u':
         if self.selected_item.prev:
               self.selected_item.prev.selected = True
      self.last_focused_item = self.selected_item

   def item_activated_cb(self, li=None, item=None):
      if item is None:
         item = self.selected_item
      if os.path.isdir(item.data['path']):
         self.populate(item.data['path'])
      elif item.data['path'] == 'fav':
         gui.EmcSourcesManager('filemanager')

   def populate_root(self, favorites):
      self.clear()
      for path in favorites:
         if path.startswith('file://'):
            path = path[7:]
         if path == os.path.expanduser('~'):
            icon = gui.load_icon('icon/home')
         else:
            icon = gui.load_icon('icon/folder')
         it = self.item_append(path, icon)
         it.data['path'] = path

      it = self.item_append(_('Manage favorites'), gui.load_icon('icon/plus'))
      it.data['path'] = 'fav'
      self.go()
      self.first_item.selected = True

   def populate(self, folder):
      self.clear()

      # parent folder item
      parent_folder = os.path.normpath(os.path.join(folder, '..'))
      if folder != parent_folder:
         it = self.item_append(_('Parent folder'), gui.load_icon('icon/arrowU'))
         it.data['path'] = parent_folder

      # build folders and files lists
      folders = []
      files = []
      for fname in utils.natural_sort(os.listdir(folder)):
         fullpath = os.path.join(folder, fname)
         if fname[0] != '.':
            if os.path.isdir(fullpath):
               folders.append(fullpath)
            else:
               files.append(fullpath)

      # populate folders
      for fullpath in folders:
         name = os.path.basename(fullpath)
         it = self.item_append(name, gui.load_icon('icon/folder'))
         it.data['path'] = fullpath

      # populate files
      for fullpath in files:
         name = os.path.basename(fullpath)
         it = self.item_append(name)
         it.data['path'] = fullpath

      self.go()
      self.first_item.selected = True


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

      ini.add_section('filemanager')
      if not ini.get_string_list('filemanager', 'folders', ';'):
         favs = ['file://' + os.path.expanduser("~")]
         ini.set_string_list('filemanager', 'folders', favs, ';')

   def __shutdown__(self):
      mainmenu.item_del('fileman')

   def cb_mainmenu(self, url=None):
      self.build_ui()
      mainmenu.hide()
      gui.signal_emit('fileman,show')
      gui.signal_emit('topbar,show')
      gui.text_set('topbar.title', _('File Manager'))
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
      b.data['cb'] = self.bt_rename_cb
      gui.box_append('fileman.buttons.box', b)

      b = gui.EmcButton(_('Delete'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      gui.box_append('fileman.buttons.box', b)

      b = gui.EmcButton(_('Favorites'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      b.callback_clicked_add(self.bt_favorites_cb)
      b.data['cb'] = self.bt_favorites_cb
      gui.box_append('fileman.buttons.box2', b)

      b = gui.EmcButton(_('Close'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      b.callback_clicked_add(self.bt_close_cb)
      b.data['cb'] = self.bt_close_cb
      gui.box_append('fileman.buttons.box2', b)

      li = FilemanList() 
      gui.swallow_set('fileman.list1.swallow', li)
      li.populate_root(ini.get_string_list('filemanager', 'folders', ';'))
      li.callback_selected_add(self.list_item_selected_cb)
      self.list1 = li

      li = FilemanList()
      gui.swallow_set('fileman.list2.swallow', li)
      li.populate_root(ini.get_string_list('filemanager', 'folders', ';'))
      li.callback_selected_add(self.list_item_selected_cb)
      self.list2 = li

      self.list1.first_item.selected = True
      self.focused = self.list1
      self.focusman.unfocus()
      self.ui_built = True

   def bt_rename_cb(self, bt):
      gui.EmcVKeyboard()

   def bt_favorites_cb(self, bt):
      li = self.list1 if self.list1.selected_item else self.list2
      li.populate_root(ini.get_string_list('filemanager', 'folders', ';'))

   def bt_close_cb(self, bt):
      input_events.listener_del('fileman')
      mainmenu.show()
      gui.signal_emit('fileman,hide')
      gui.signal_emit('topbar,hide')

   def list_item_selected_cb(self, li, it):
      if li == self.list1:
         self.list2.unfocus()
      else:
         self.list1.unfocus()
      self.focused = li
      self.focusman.unfocus()

   def input_event_cb(self, event):
      DBG(event)
      if event == 'DOWN':
         self.focused.focus_move('d')
            
      elif event == 'UP':
         self.focused.focus_move('u')

      elif event == 'RIGHT':
         if self.focused == self.list1:
            self.focused = self.focusman
            self.focusman.focus()
         elif self.focused == self.focusman:
            self.list2.focus()
            self.focusman.unfocus()
            self.focused = self.list2

      elif event == 'LEFT':
         if self.focused == self.list2:
            self.focused = self.focusman
            self.focusman.focus()
         elif self.focused == self.focusman:
            self.list1.focus()
            self.focusman.unfocus()
            self.focused = self.list1

      elif event in ('OK'):
         if self.focused in (self.list1, self.list2):
            self.focused.item_activated_cb()
         else:
            bt = self.focusman.focused_obj_get()
            bt.data['cb'](bt)

      else:
         return input_events.EVENT_CONTINUE

      # elif event in ('BACK', 'EXIT'):
         # self.close()
         # return input_events.EVENT_CONTINUE
# 
      return input_events.EVENT_BLOCK
