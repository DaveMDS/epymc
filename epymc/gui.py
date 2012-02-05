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

import evas
import elementary

import utils
import ini
import mediaplayer
import gui
import input_events


win = None
layout = None
theme_file = None
backdrop_im = None

def DBG(msg):
   print ('GUI: ' + msg)
   pass

def init():
   global win
   global layout
   global theme_file

   # set default theme in config file
   if not ini.has_option('general', 'theme'):
      ini.set('general', 'theme', 'default')
   name = ini.get('general', 'theme');

   # search the theme file, or use the default one
   theme_file = utils.get_resource_file('themes', name + '.edj', 'default.edj')
   if not theme_file:
      print "ERROR: can't find a working theme file, exiting..."
      return False
   
   #~ elementary.theme_overlay_add(theme_file) # TODO REMOVE ME!!!
   elementary.theme_extension_add(theme_file)

   # window
   win = elementary.Window("epymc", elementary.ELM_WIN_BASIC)
   win.title_set("Enlightenment Media Center")
   win.callback_destroy_add(_cb_win_del)
   if ini.has_option('general', 'fullscreen'):
      if ini.get_bool('general', 'fullscreen') == True:
         win.fullscreen_set(1)
   else:
      ini.set('general', 'fullscreen', False)

   # main layout (main theme)
   layout = elementary.Layout(win)
   layout.file_set(theme_file, "epymc_main_layout")
   layout.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
   win.resize_object_add(layout)
   layout.show()

   win.show()


   # fill view buttons box in topbar
   bt = elementary.Button(win)
   bt.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
   bt.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
   bt.icon_set(load_icon('icon/list'))
   bt.callback_clicked_add(_cb_btn_change_view, "VIEW_LIST")
   layout.edje_get().part_box_append('topbar/box', bt)
   bt.show()

   bt = elementary.Button(win)
   bt.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
   bt.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
   bt.icon_set(load_icon('icon/grid'))
   bt.callback_clicked_add(_cb_btn_change_view, "VIEW_GRID")
   layout.edje_get().part_box_append('topbar/box', bt)
   bt.show()

   input_events.listener_add('gui', input_event_cb)

   return True

def shoutdown():
   input_events.listener_del('gui')

def input_event_cb(event):
   if event == "TOGGLE_FULLSCREEN":
      win.fullscreen = not win.fullscreen
      return input_events.EVENT_BLOCK
   elif event == 'VOLUME_UP':
      mediaplayer.volume_set(mediaplayer.volume_get() + 10)
      mediaplayer.volume_show(hidein=3)
      return input_events.EVENT_BLOCK
   elif event == 'VOLUME_DOWN':
      mediaplayer.volume_set(mediaplayer.volume_get() - 10)
      mediaplayer.volume_show(hidein=3)
      return input_events.EVENT_BLOCK
   elif event == 'VOLUME_MUTE':
      mediaplayer.volume_mute()
      mediaplayer.volume_show(hidein=3)
      return input_events.EVENT_BLOCK

   input_events.EVENT_CONTINUE

def _cb_win_del(win):
   ask_to_exit()

def _cb_btn_change_view(btn, view):
   input_events.event_emit(view)

def load_icon(icon):
   """
   icon can be a full path (if start with a '/' or
   can be a theme icon (ex: icon/folder).
   see icons.edc for all the existing icon
   """
   #TODO if icon in an EvasObject just return it
   ic = elementary.Icon(gui.win)
   if icon[0] == '/':
      ic.file_set(icon)
   else:
      ic.file_set(theme_file, icon)
   ic.size_hint_aspect_set(evas.EVAS_ASPECT_CONTROL_VERTICAL, 1, 1)
   return ic
    
def ask_to_exit():
   d = EmcDialog(title = 'Exit MediaCenter ?', style = 'yesno',
                 done_cb = _cb_exit_yes)

def _cb_exit_yes(button):
   elementary.exit()

def toggle_fullscreen():
   pass

def mouse_hide():
   pass
   # print "MOUSE HIDE"
   # elm coursor
   # from elementary import cursors
   # layout.cursor_set(cursors.ELM_CURSOR_CLOCK)

   #ecore win cursor
   # import ecore
   # ecore.x.Window.cursor_hide()

def mouse_show():
   print "MOUSE SHOW"

def part_get(name):
   global layout
   return layout.edje_get().part_external_object_get(name)

def signal_emit(sig, src = 'emc'):
   global layout
   layout.edje_get().signal_emit(sig, src)

def text_set(part, text):
   global layout
   layout.edje_get().part_text_set(part, text)

def swallow_set(part, obj):
   old = layout.edje_get().part_swallow_get(part)
   if old: old.delete()
   layout.edje_get().part_swallow(part, obj)

################################################################################
def background_set(image):
   global backdrop_im

   if not backdrop_im:
      backdrop_im = elementary.Image(gui.win)
      backdrop_im.fill_outside_set(True)
      swallow_set("backdrop/1", backdrop_im)

   backdrop_im.file_set(image)

################################################################################
class EmcRemoteImage(elementary.Image):
   """ TODO doc this """

   def __init__(self, parent):
      elementary.Image.__init__(self, parent)
      self._parent = parent
      self._pb = elementary.Progressbar(parent)
      self._pb.style_set("wheel")
      self.on_move_add(self._cb_move_resize)
      self.on_resize_add(self._cb_move_resize)

   def show(self):
      print 'SHOW %d %d %d %d' % self.geometry_get()
      elementary.Image.show(self)

   def hide(self):
      self._pb.hide()
      elementary.Image.hide(self)

   def url_set(self, url, dest = None):
      if dest and os.path.exists(dest):
         # if dest exists then just set the image
         self.file_set(dest)
      else:
         # else start spin & download
         self.file_set('')
         self.start_spin()
         utils.download_url_async(url, dest if dest else "tmp",
                                  complete_cb = self._cb_download_complete)

   def start_spin(self):
      self.show()
      self._pb.show()
      self._pb.pulse(True)

   def stop_spin(self):
      self._pb.hide()
      self._pb.pulse(False)

   def _cb_move_resize(self, obj):
      (x, y, w, h) = self.geometry_get()
      print ('MOVE %d %d %d %d' % (x, y, w, h))
      self._pb.resize(w, h)
      self._pb.move(x, y)
      # self._pb.raise_()  :/
      if self._pb.clip != self.clip:
         self._pb.clip = self.clip

   def _cb_download_complete(self, dest, status):
      self.stop_spin()
      if status == 200: # Successfull HTTP code
         self.file_set(dest)
         self.size_hint_min_set(100, 100) #TODO FIXME (needed by tmdb search results list)
      else:
         self.file_set("")
         # TODO show a dummy image

   #TODO on image_set abort the download ? 

################################################################################
class EmcDialog(elementary.InnerWindow):
   """ TODO doc this
   style can be 'default', 'minimal' or 'minimal_vertical'

   you can also apply special style that perform specific task:
      'info', 'error', 'warning', 'yesno', 'cancel'
   note that special style don't need activate() to be called

   TODO does we need activate at all?
   """

   special_styles = ['info', 'error', 'warning', 'yesno', 'cancel']
   dialogs_counter = 0
   
   def __init__(self, title = None, text = None, content = None,
                spinner = False, style = 'default', done_cb = None):
      elementary.InnerWindow.__init__(self, gui.win)
      EmcDialog.dialogs_counter += 1

      if style in EmcDialog.special_styles:
         self.style_set('minimal')
      else:
         self.style_set('panel')

      self._name = 'Dialog-' + str(EmcDialog.dialogs_counter)
      self._content = content
      self._done_cb = done_cb

      # vbox
      self._vbox = elementary.Box(gui.win)
      self._vbox.horizontal_set(False)
      self._vbox.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      self._vbox.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      self._vbox.show()
      elementary.InnerWindow.content_set(self, self._vbox)

      # hbox (buttons)
      self._hbox = elementary.Box(gui.win)
      self._hbox.horizontal_set(True)
      self._vbox.pack_end(self._hbox)
      self._hbox.show()

      # focus manageer
      self.fman = EmcFocusManager()
      
      if text is not None:
         self._textentry = elementary.Entry(gui.win)
         self._textentry.style_set('dialog')
         self._textentry.editable_set(False)
         self._textentry.context_menu_disabled_set(True)
         self._textentry.entry_set(text)
         self._textentry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         self._textentry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
         #~ self._textentry.size_hint_align_set(0.5, 0.5)
         self._vbox.pack_start(self._textentry)
         self._textentry.show()
      elif content:
         frame = elementary.Frame(gui.win)
         frame.style_set("pad_medium")
         frame.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         frame.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
         frame.content_set(content)
         frame.show()
         self._vbox.pack_start(frame)

      if spinner:
         self._spinner = elementary.Progressbar(gui.win)
         self._spinner.style_set('wheel')
         self._spinner.pulse(True)
         self._spinner.show()
         self._vbox.pack_start(self._spinner)

      if title is not None:
         self._title = elementary.Label(gui.win)
         self._title.style_set("dialog")
         self._title.text_set("<title>" + title + "</>")
         self._vbox.pack_start(self._title)
         self._title.show()

      if style in ['info', 'error', 'warning']:
         self.button_add('Ok', (lambda btn: self.delete()))
         self.activate()

      if style in ['yesno']:
         self.button_add('No', (lambda btn: self.delete()))
         self.button_add('Yes', (lambda btn: self._done_cb(self)))
         self.activate()

      if style in ['cancel']:
         if done_cb:
            self.button_add('Cancel', (lambda btn: self._done_cb(self)))
         else:
            self.button_add('Cancel', (lambda btn: self.delete()))
         self.activate()

   def activate(self):
      input_events.listener_add(self._name, self._input_event_cb)
      elementary.InnerWindow.activate(self)

   def delete(self):
      input_events.listener_del(self._name)
      self.fman.delete()
      elementary.InnerWindow.delete(self)

   def content_get(self):
      return self._content

   def button_add(self, label, selected_cb = None, cb_data = None, icon = None):
      b = elementary.Button(self)
      b.text_set(label)
      if icon: b.icon_set(load_icon(icon))
      b.data['cb'] = selected_cb
      b.data['cb_data'] = cb_data
      b.callback_clicked_add(self._cb_buttons)
      b.focus_allow_set(False)
      self.fman.obj_add(b)
      self._hbox.pack_start(b)
      b.show()
      return b

   def text_set(self, text):
      self._textentry.entry_set(text)

   def text_get(self):
      return self._textentry.entry_get()

   def text_append(self, text):
      self._textentry.entry_set(self._textentry.entry_get() + text)

   def spinner_start(self):
      self._spinner.pulse(True)

   def spinner_stop(self):
      self._spinner.pulse(False)

   def _cb_buttons(self, button):
      if not button: return
      selected_cb = button.data['cb']
      cb_data = button.data['cb_data']

      if selected_cb and cb_data:
         selected_cb(button, cb_data)
      elif selected_cb:
         selected_cb(button)

   def _input_event_cb(self, event):

      if event in ['BACK', 'EXIT']:
         self.delete()
         return input_events.EVENT_BLOCK

      # if content is elm List or Genlist then automanage the events
      if self._content and type(self._content) in (elementary.List, elementary.Genlist):
         list = self._content
         item = list.selected_item_get()
         if not item:
            item = list.items_get()[0]

         if event == 'DOWN':
            next = item.next_get()
            if next:
               next.selected_set(1)
               next.show()
               return input_events.EVENT_BLOCK

         if event == 'UP':
            prev = item.prev_get()
            if prev:
               prev.selected_set(1)
               prev.show()
               return input_events.EVENT_BLOCK

      if event == 'OK':
         self._cb_buttons(self.fman.focused_get())

      elif event == 'LEFT':
         self.fman.focus_move('l')

      elif event == 'RIGHT':
         self.fman.focus_move('r')

      return input_events.EVENT_BLOCK

###############################################################################
class EmcSourceSelector(EmcDialog):
   """ TODO doc this
   """

   def __init__(self, title = "Source Selector", done_cb = None):
      self._selected_cb = done_cb
      self._glist = elementary.Genlist(gui.win)
      self._glist.homogeneous_set(True)
      self._glist.always_select_mode_set(True)
      self._glist.focus_allow_set(False)
      self._glist.callback_clicked_double_add(self._cb_item_selected)
      self._glist_itc = elementary.GenlistItemClass(item_style="default",
                                 text_get_func = self._genlist_folder_label_get,
                                 content_get_func = self._genlist_folder_icon_get)
      self._glist_itc_back = elementary.GenlistItemClass(item_style="default",
                                 text_get_func = self._genlist_back_label_get,
                                 content_get_func = self._genlist_back_icon_get)
      
      EmcDialog.__init__(self, title, content=self._glist, style='panel')
      self.button_add('select', selected_cb = self._cb_done_selected)
      btn = self.button_add('browse', selected_cb = self._cb_browse_selected)
      self.button_add('close', (lambda btn: self.delete()))
      self.fman.focused_set(btn)

      self.populate(os.getenv('HOME'))
      self.activate()

   def populate(self, folder):
      self._glist.clear()

      parent_folder = os.path.normpath(os.path.join(folder, ".."))
      if folder != parent_folder:
         self._glist.item_append(self._glist_itc_back, parent_folder)

      for fname in sorted(os.listdir(folder)):
         fullpath = os.path.join(folder, fname)
         if fname[0] != '.' and os.path.isdir(fullpath):
            self._glist.item_append(self._glist_itc, fullpath)

      self._glist.first_item.selected = True;

   def _cb_item_selected(self, list, item):
      self.populate(item.data_get())

   def _cb_done_selected(self, button):
      item = self._glist.selected_item_get()
      if item and callable(self._selected_cb):
         self._selected_cb('file://' + item.data_get())
      self.delete()

   def _cb_browse_selected(self, button):
      item = self._glist.selected_item_get()
      self.populate(item.data_get())

   def _genlist_folder_label_get(self, obj, part, item_data):
      return os.path.basename(item_data)

   def _genlist_folder_icon_get(self, obj, part, item_data):
      if part == 'elm.swallow.icon':
         return gui.load_icon('icon/folder')
      return None
   
   def _genlist_back_label_get(self, obj, part, item_data):
      return "back"

   def _genlist_back_icon_get(self, obj, part, data):
      if part == 'elm.swallow.icon':
         return gui.load_icon('icon/back')
      return None

###############################################################################
class EmcFocusManager(object):
   """
   This class manage a list of elementary objects, usually buttons.
   You provide all the objects that can receive focus and the class
   will take care of selecting the right object when you move the selection
   """
   def __init__(self):
      self.objs = []
      self.focused = None

   def delete(self):
      """
      Delete the FocusManager instance and free all the resources used
      """
      del self.objs

   def obj_add(self, obj):
      """
      Add an object to the chain, obj must be an evas object that support
      disabled_set() 'interface', usually an elementary obj will do the work.
      """
      if len(self.objs) == 0:
         self.focused = obj
      else:
         obj.disabled_set(True)
      obj.on_mouse_in_add(self._mouse_in_cb)
      self.objs.append(obj)

   def focused_set(self, obj):
      """
      Give focus to the given obj
      """
      if self.focused:
         self.focused.disabled_set(True)
      obj.disabled_set(False)
      self.focused = obj

   def focused_get(self):
      """
      Get the object that has focus
      """
      return self.focused

   def focus_move(self, direction):
      """
      Try to move the selection in th given direction.
      direction can be: 'l'eft, 'r'ight, 'u'p or 'd'own
      """
      x, y = self.focused.center
      nearest = None
      distance = 99999
      for obj in self.objs:
         if obj != self.focused:
            ox, oy = obj.center
            # discard objects in the wrong direction
            if   direction == 'l' and ox >= x: continue
            elif direction == 'r' and ox <= x: continue
            elif direction == 'u' and oy >= y: continue
            elif direction == 'd' and oy <= y: continue

            # simple calc distance (with priority in the current direction)
            if direction in ['l', 'r']:
               dis = abs(x - ox) + (abs(y - oy) * 10)
            else:
               dis = (abs(x - ox) * 10) + abs(y - oy)

            # remember the nearest object
            if dis < distance:
               distance = dis
               nearest = obj

      # select the new object if found
      if nearest:
         self.focused_set(nearest)

   def all_get(self):
      """
      Get the list of all the objects that was previously added
      """
      return self.objs

   def _mouse_in_cb(self, obj, event):
      if self.focused != obj:
         self.focused_set(obj)
   
###############################################################################
class EmcVKeyboard(elementary.InnerWindow):
   """ TODO doc this """
   def __init__(self, accept_cb = None, dismiss_cb = None,
                title = None, text = None):
      """ TODO doc this """
      elementary.InnerWindow.__init__(self, gui.win)
      self.style_set('minimal')

      self.current_button = None
      self.accept_cb = accept_cb
      self.dismiss_cb = dismiss_cb

      # table
      tb = elementary.Table(gui.win)
      tb.homogenous_set(True)
      tb.show()

      # title
      label = elementary.Label(gui.win)
      label.style_set('dialog')
      label.label_set('<title>%s</>' % (title or 'Insert text'))
      label.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      label.size_hint_align_set(0.5, evas.EVAS_HINT_FILL)
      label.show()
      tb.pack(label, 0, 0, 10, 1)

      # entry
      self.entry = elementary.Entry(gui.win) # TODO use scrolled_entry instead
      self.entry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      self.entry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      self.entry.single_line_set(True)
      if text: self.text_set(text)
      tb.pack(self.entry, 0, 1, 10, 1)
      self.entry.show()

      # focus manager
      efm = EmcFocusManager()
      self.efm = efm

      # standard keyb
      for i, c in enumerate(['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']):
         self._pack_btn(tb, i, 2, 1, 1, c, cb = self._default_btn_cb)
      for i, c in enumerate(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']):
         if c == 'a': b = self._pack_btn(tb, i, 3, 1, 1, c, cb = self._default_btn_cb, focused = True)
         else:        b = self._pack_btn(tb, i, 3, 1, 1, c, cb = self._default_btn_cb)
      for i, c in enumerate(['k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't']):
         self._pack_btn(tb, i, 4, 1, 1, c, cb = self._default_btn_cb)
      for i, c in enumerate(['u', 'v', 'w', 'x', 'y', 'z', '.', '@', '-', '_']):
         self._pack_btn(tb, i, 5, 1, 1, c, cb = self._default_btn_cb)

      self._pack_btn(tb, 0, 6, 3, 1, 'ERASE', cb = self._erase_cb)
      self._pack_btn(tb, 3, 6, 4, 1, 'SPACE', cb = self._space_cb)
      self._pack_btn(tb, 7, 6, 3, 1, 'UPPERCASE', cb = self._uppercase_cb)

      self._pack_btn(tb, 0, 7, 4, 1, 'Dismiss', 'icon/cancel', self._dismiss_cb)
      self._pack_btn(tb, 6, 7, 4, 1, 'Accept',  'icon/ok',     self._accept_cb)

      # activate the inwin
      self.content_set(tb)
      self.activate()
      self.entry.focus()

      # catch input events
      input_events.listener_add("vkbd", self.input_event_cb)

   def _pack_btn(self, tb, x, y, w, h, label, icon = None, cb = None, focused = False):
      b = elementary.Button(gui.win)
      b.size_hint_weight_set(evas.EVAS_HINT_EXPAND, 0.0)
      b.size_hint_align_set(evas.EVAS_HINT_FILL, 0.0)
      if icon: b.icon_set(gui.load_icon(icon))
      if cb: b.callback_clicked_add(cb)
      b.label_set(label)
      self.efm.obj_add(b)
      if focused: self.efm.focused_set(b)
      b.show()
      tb.pack(b, x, y, w, h)
      return b

   def delete(self):
      input_events.listener_del("vkbd")
      self.efm.delete()
      elementary.InnerWindow.delete(self)

   def text_set(self, text):
      self.entry.entry_set(text)
      self.entry.cursor_end_set()
      self.entry.focus()

   def _dismiss_cb(self, button):
      if self.dismiss_cb and callable(self.dismiss_cb):
         self.dismiss_cb(self)
      self.delete()

   def _accept_cb(self, button):
      if self.accept_cb and callable(self.accept_cb):
         self.accept_cb(self, self.entry.entry_get())
      self.delete()

   def _default_btn_cb(self, button):
      self.entry.focus()
      self.entry.entry_insert(button.label)

   def _erase_cb(self, button):
      self.entry.focus()
      gui.win.evas_get().feed_key_down('BackSpace', 'BackSpace', '\b', '\b', 0)

   def _space_cb(self, button):
      self.entry.focus()
      self.entry.entry_insert(' ')

   def _uppercase_cb(self, button):
      for btn in self.efm.all_get():
         c = btn.label
         if len(c) == 1 and c.isalpha():
            if c.islower():
               btn.label = c.upper()
               button.label = "LOWERCASE"
            else:
               btn.label = c.lower()
               button.label = "UPPERCASE"

   def input_event_cb(self, event):
      if event == 'OK':
         btn = self.efm.focused_get()
         btn.callback_call('clicked') # TODO COMMIT THIS
      elif event == 'EXIT':
         self._dismiss_cb(None)
      elif event == 'LEFT':  self.efm.focus_move('l')
      elif event == 'RIGHT': self.efm.focus_move('r')
      elif event == 'UP':    self.efm.focus_move('u')
      elif event == 'DOWN':  self.efm.focus_move('d')         
      
      return input_events.EVENT_BLOCK
  
