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
import threading
try:
   import queue
except:
   import Queue as queue

from efl import ecore
from efl.elementary.list import List

from epymc.modules import EmcModule
from epymc.gui import EXPAND_BOTH, EXPAND_HORIZ, FILL_BOTH, FILL_HORIZ
import epymc.mainmenu as mainmenu
import epymc.input_events as input_events
import epymc.utils as utils
import epymc.gui as gui
import epymc.ini as ini


def DBG(msg):
   print('FILEMAN: %s' % msg)
   pass


class FilemanList(List):
   def __init__(self):
      List.__init__(self, gui.layout, style='browser', focus_allow=False)
      self.last_focused_item = None
      self.current_folder = None
      self.fmonitor = None
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

   def clear(self):
      self.last_focused_item = None
      if self.fmonitor is not None:
         self.fmonitor.delete()
         self.fmonitor = None
      List.clear(self)

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
      self.current_folder = None

   def populate(self, folder):
      self.clear()

      # parent folder item
      parent_folder = os.path.normpath(os.path.join(folder, '..'))
      if folder != parent_folder:
         it = self.item_append(_('Parent folder'), gui.load_icon('icon/arrowU'))
         it.data['path'] = parent_folder
         it.data['isfolder'] = True

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
         it.data['isfolder'] = True

      # populate files
      for fullpath in files:
         name = os.path.basename(fullpath)
         it = self.item_append(name)
         it.data['path'] = fullpath

      # start the list and select the first item
      self.go()
      self.first_item.selected = True
      self.current_folder = folder

      # keep the folder monitored for changes
      self.fmonitor = ecore.FileMonitor(folder, self._fmonitor_cb)

   # FileMonitor callback and utils
   def _fmonitor_cb(self, event, path):
      if utils.is_py2():
         path = path.encode('utf8')

      if event == ecore.ECORE_FILE_EVENT_CREATED_FILE:
         self._file_insert_sorted(path)

      elif event == ecore.ECORE_FILE_EVENT_CREATED_DIRECTORY:
         self._folder_insert_sorted(path)

      elif event == ecore.ECORE_FILE_EVENT_DELETED_FILE or \
           event == ecore.ECORE_FILE_EVENT_DELETED_DIRECTORY:
         self._path_remove(path)

      elif event == ecore.ECORE_FILE_EVENT_DELETED_SELF:
         # TODO... goto up ???
         pass

   def _file_insert_sorted(self, path):
      s = self.first_item

      # skip all the folders
      while s and s.data.get('isfolder', False) is True:
         s = s.next

      # search ordered position between files
      while s and utils.natural_cmp(s.data['path'], path) < 0:
         s = s.next

      # insert the new file before search or at the end
      name = os.path.basename(path)
      it = self.item_insert_before(s, name) if s else \
           self.item_append(name)
      it.data['path'] = path
      self.go()

   def _folder_insert_sorted(self, path):
      s = self.first_item
      
      # search ordered position only between folders
      while s and s.data.get('isfolder', False) is True and \
            utils.natural_cmp(s.data['path'], path) < 0:
         s = s.next

      # insert the new folder before search or before the first file
      name = os.path.basename(path)
      icon = gui.load_icon('icon/folder')
      it = self.item_insert_before(s, name, icon) if s else \
           self.item_append(name, icon)
      it.data['path'] = path
      it.data['isfolder'] = True
      self.go()

   def _path_remove(self, path):
      item = self.first_item
      while item and item.data.get('path') != path:
         item = item.next
      if item:
         if item == self.last_focused_item:
            self.last_focused_item = item.prev
         item.delete()

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
      self.worker = FileManagerWorker()
      mainmenu.item_add('fileman', 60, _('File Manager'), 'icon/folder',
                        self.cb_mainmenu)

      ini.add_section('filemanager')
      if not ini.get_string_list('filemanager', 'folders', ';'):
         favs = ['file://' + os.path.expanduser("~")]
         ini.set_string_list('filemanager', 'folders', favs, ';')

   def __shutdown__(self):
      mainmenu.item_del('fileman')
      if self.list1: self.list1.clear()
      if self.list2: self.list2.clear()

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

      b = gui.EmcButton(_('New folder'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      b.callback_clicked_add(self.bt_newfolder_cb)
      b.data['cb'] = self.bt_newfolder_cb
      gui.box_append('fileman.buttons.box', b)

      b = gui.EmcButton(_('Copy'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      b.callback_clicked_add(self.bt_copy_cb)
      b.data['cb'] = self.bt_copy_cb
      gui.box_append('fileman.buttons.box', b)

      b = gui.EmcButton(_('Move (*)'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      b.callback_clicked_add(self.bt_move_cb)
      b.data['cb'] = self.bt_move_cb
      gui.box_append('fileman.buttons.box', b)

      b = gui.EmcButton(_('Rename'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      b.callback_clicked_add(self.bt_rename_cb)
      b.data['cb'] = self.bt_rename_cb
      gui.box_append('fileman.buttons.box', b)

      b = gui.EmcButton(_('Delete'), size_hint_align=FILL_HORIZ)
      self.focusman.obj_add(b)
      b.callback_clicked_add(self.bt_delete_cb)
      b.data['cb'] = self.bt_delete_cb
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
      it = self.list1.selected_item or self.list2.selected_item
      src = it.data['path']
      if src and src != it.text and os.access(src, os.W_OK):
         gui.EmcVKeyboard(title=_('Rename'), text=it.text,
                          accept_cb=self.rename_vkeyb_cb, user_data=it)

   def rename_vkeyb_cb(self, vkeyb, new_name, it):
      src = it.data['path']
      dst = os.path.join(os.path.dirname(src), new_name)
      self.worker.rename(src, dst)

   def bt_copy_cb(self, bt):
      it = self.list1.selected_item or self.list2.selected_item
      src = it.data['path']
      if self.list1.selected_item:
         dst = self.list2.current_folder
      else:
         dst = self.list1.current_folder
      if src and dst:
         self.worker.copy(src, dst)

   def bt_move_cb(self, bt):
      it = self.list1.selected_item or self.list2.selected_item
      src = it.data['path']
      if self.list1.selected_item:
         dst = self.list2.current_folder
      else:
         dst = self.list1.current_folder
      if src and dst:
         self.worker.move(src, dst)

   def bt_delete_cb(self, bt):
      it = self.list1.selected_item or self.list2.selected_item
      self.worker.delete(it.data['path'])

   def bt_newfolder_cb(self, bt):
      li = self.list1 if self.list1.selected_item else self.list2
      if li and li.current_folder:
         gui.EmcVKeyboard(title=_('New folder'),
                          accept_cb=self.newfolder_vkeyb_cb,
                          user_data=li.current_folder)

   def newfolder_vkeyb_cb(self, vkeyb, new_name, path):
      full_path = os.path.join(path, new_name)
      DBG("MKDIR: " + full_path)
      os.mkdir(full_path)

   def bt_favorites_cb(self, bt):
      li = self.list1 if self.list1.selected_item else self.list2
      li.populate_root(ini.get_string_list('filemanager', 'folders', ';'))

   def bt_close_cb(self, bt=None):
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

      elif event == 'BACK':
         self.bt_close_cb()

      else:
         return input_events.EVENT_CONTINUE

      return input_events.EVENT_BLOCK


class FileManagerWorker(object):
   def __init__(self):
      self.src = None
      self.dst = None
      self.op = None
      self.dia = None
      self.block_size = 8388608 # 1024x1024x8 = 8 MB
      self.progress_queue = queue.Queue() # (cur_name, cur_file, total_files, bytes_done, bytes_tot) or 'done'

   def rename(self, src, dst):
      DBG('RENAME: "%s" -> "%s"' % (src, dst))
      try:
         os.rename(src, dst)
      except Exception as e:
         gui.EmcDialog(style='error', title='Cannot rename file', text=str(e))

   def copy(self, src, dst):
      if not self.check_src_and_dest(src, dst):
         return
      DBG('COPY: "%s" -> "%s"' % (src,dst))
      self.op, self.src, self.dst = 'copy', src, dst
      self._start_operation_in_thread(self._copy_thread)

   def delete(self, path):
      DBG('DELETE: %s' % (path))
      self.op, self.src = 'delete', path
      if os.path.isdir(path):
         txt = _('Are you sure you want to delete the folder?')
      else:
         txt = _('Are you sure you want to delete the file?')
      gui.EmcDialog(style='yesno', title=_('File Manager'),
                    text=txt + '<br>' + path,
                    done_cb=self._delete_confirmed)

   def _delete_confirmed(self, dia):
      DBG('DELETE CONFIRMED: %s' % (self.src))
      dia.delete()
      self._start_operation_in_thread(self._delete_thread)


   def move(self, src, dst):
      if not self.check_src_and_dest(src, dst):
         return
      if os.stat(src).st_dev == os.stat(dst).st_dev:
         DBG('MOVE (same part): %s -> %s' % (src, dst))
         dst = os.path.join(dst, os.path.basename(src))
         self.rename(src, dst)
      else:
         DBG('MOVE (different part): %s -> %s' % (src, dst))
         # TODO

   def _start_operation_in_thread(self, func):
      self.dia = gui.EmcDialog(style='progress', title=_('File Manager'),
                               text=_('Operation is starting...'),
                               canc_cb=self.abort_operation)
      t = threading.Thread(target=func)
      t.start()
      ecore.Timer(0.2, self._progress_timer_cb)


   def abort_operation(self, dia=None):
      DBG('TODO Abort')
      # TODO

   def check_src_and_dest(self, src, dest):
      # src must be readable
      if not os.access(src, os.R_OK):
         gui.EmcDialog(style='error', text=_('Source is not readable'))
         return False

      # dest folder must be writable
      if not os.path.isdir(dest) or not os.access(dest, os.W_OK):
         gui.EmcDialog(style='error', text=_('Destination folder is not writable'))
         return False

      # src folder and dest must be different
      src_folder = os.path.dirname(src)
      if src_folder == dest:
         gui.EmcDialog(style='error', text=_('Invalid destination folder'))
         return False

      # do not overwrite destination
      dest_name = os.path.join(dest, os.path.basename(src))
      if os.path.exists(dest_name):
         gui.EmcDialog(style='error', text=_('Destination already exists'))
         return False

      return True

   def _dialog_update(self, fname, cur_file, tot_files, progress):
      if self.op == 'copy':
         txt = _('Copying file {0} of {1}:').format(cur_file, tot_files)
      elif self.op == 'delete':
         txt = _('Deleting file {0} of {1}:').format(cur_file, tot_files)
      txt += '<br>' + os.path.basename(fname) + '<br>'
      self.dia.text_set(txt)
      self.dia.progress_set(progress)

   def _progress_timer_cb(self):
      # queue empty, nothing to do
      if self.progress_queue.empty():
         return ecore.ECORE_CALLBACK_RENEW

      # get only the LAST item in the queue
      while not self.progress_queue.empty():
         item = self.progress_queue.get_nowait()

      # operation finished ?
      if isinstance(item, str) and item == 'done':
         self.dia.delete()
         self.dia = self.op = self.src = self.dst = None
         return ecore.ECORE_CALLBACK_CANCEL

      # update progress dialog
      cur_name, cur_file, tot_files, done_bytes, tot_bytes = item
      self._dialog_update(cur_name, cur_file, tot_files,
                          float(done_bytes) / float(tot_bytes))

      return ecore.ECORE_CALLBACK_RENEW


   def _delete_thread(self):
      tobedone = []

      # build tobedone list: [path1, path2, ... ]
      if os.path.isdir(self.src):
         for (path, dirs, files) in os.walk(self.src,topdown=False):
            for f in files:
               full_path = os.path.join(path, f)
               tobedone.append(full_path)
            tobedone.append(path) # also delete the folder after the files
      else:
         tobedone.append(self.src)

      total_files = len(tobedone)
      cur_file = 0

      # delete files one by one
      for path in tobedone:
         cur_file += 1

         if os.path.isdir(path):
            DBG("RMDIR: "+ path)
            os.rmdir(path)
         else:
            DBG("UNLINK: "+ path)
            os.unlink(path)

         item = (path, cur_file, total_files, cur_file, total_files)
         self.progress_queue.put(item)

      self.progress_queue.put('done')


   def _copy_thread(self):

      total_bytes = 0
      tobedone = []

      # build tobedone list: [(src_file, dst_file), ... ]
      if os.path.isdir(self.src):
         src_folder = self.src
         base = os.path.dirname(src_folder)
         dst_folder = self.dst
         for (path, dirs, files) in os.walk(src_folder):
            for f in files:
               src_file = os.path.join(path, f)
               dst_file = os.path.join(dst_folder, path[len(base)+1:], f)
               tobedone.append((src_file, dst_file))
               total_bytes += os.stat(src_file).st_size
      else:
         src_file = self.src
         dst_file = os.path.join(self.dst, os.path.basename(src_file))
         tobedone.append((src_file, dst_file))
         total_bytes = os.stat(src_file).st_size

      total_files = len(tobedone)
      cur_file = 0
      done_bytes = 0

      # copy files one by one
      for src_file, dst_file in tobedone:
         cur_file += 1

         # create dest folder if needed
         dst_folder = os.path.dirname(dst_file)
         if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)

         # open
         fsrc = open(src_file, "rb")
         fdst = open(dst_file, "wb")
         cur_pos = 0

         while True:
            # read
            data = fsrc.read(self.block_size)
            if not data:
               break

            # write
            fdst.write(data)

            # report progress
            done_bytes += len(data)
            item = (src_file, cur_file, total_files, done_bytes, total_bytes)
            self.progress_queue.put(item)

            # advance to next 'block'
            cur_pos += self.block_size

         # close
         fsrc.close()
         fdst.close()

      self.progress_queue.put('done')
