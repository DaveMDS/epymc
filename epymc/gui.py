#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
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

import evas
import ecore
import ecore.x #used only to show/hide the cursor
import edje
import elementary

import utils
import ini
import gui
import input_events

win = None
xwin = None
layout = None
theme_file = None
backdrop_im = None


DEBUG = True
DEBUGN = 'GUI'
def LOG(sev, msg):
   if   sev == 'err': print('%s ERROR: %s' % (DEBUGN, msg))
   elif sev == 'inf': print('%s: %s' % (DEBUGN, msg))
   elif sev == 'dbg' and DEBUG: print('%s: %s' % (DEBUGN, msg))

def init():
   global win
   global xwin
   global layout
   global theme_file

   # set default theme in config file
   if not ini.has_option('general', 'theme'):
      ini.set('general', 'theme', 'default')
   name = ini.get('general', 'theme')

   # set default scale
   if not ini.has_option('general', 'scale'):
      ini.set('general', 'scale', '1.0')

   # set default elm engine
   if not ini.has_option('general', 'evas_engine'):
      ini.set('general', 'evas_engine', 'software_x11')

   # search the theme file, or use the default one
   theme_file = utils.get_resource_file('themes', name + '.edj', 'default.edj')
   if not theme_file:
      print 'ERROR: can\'t find a working theme file, exiting...'
      return False

   # custom elementary theme
   elementary.theme_overlay_add(theme_file) # TODO REMOVE ME!!! is here for buttons
   elementary.theme_extension_add(theme_file)

   # preferred evas engine
   # this seems totally buggy in elm, I should just do the preferred one
   elementary.preferred_engine_set(ini.get('general', 'evas_engine'))
   elementary.engine_set(ini.get('general', 'evas_engine'))



   # window
   win = elementary.Window('epymc', elementary.ELM_WIN_BASIC)
   win.title_set('Enlightenment Media Center')
   win.callback_delete_request_add(_cb_win_del)
   if ini.has_option('general', 'fullscreen'):
      if ini.get_bool('general', 'fullscreen') == True:
         win.fullscreen_set(1)
   else:
      ini.set('general', 'fullscreen', False)

   # get the X window object, we need it to show/hide the mouse cursor
   xwin = ecore.x.Window_from_xid(win.xwindow_xid_get())


   # main layout (main theme)
   layout = elementary.Layout(win)
   layout.file_set(theme_file, 'emc/main/layout')
   layout.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
   win.resize_object_add(layout)
   layout.show()

   # show the mouse when moved
   layout.edje.signal_callback_add("mouse,move", "*", (lambda o,e,s: mouse_show()))


   win.show()
   win.scale_set(ini.get_float('general', 'scale'))


   # fill view buttons box in topbar
   bt = EmcButton(win, icon='icon/list')
   bt.callback_clicked_add(_cb_btn_change_view, 'VIEW_LIST')
   layout.edje_get().part_box_append('topbar.box', bt)
   bt.show()

   bt = EmcButton(win, icon='icon/grid')
   bt.callback_clicked_add(_cb_btn_change_view, 'VIEW_GRID')
   layout.edje_get().part_box_append('topbar.box', bt)
   bt.show()

   input_events.listener_add('gui', input_event_cb)

   # once a minute ping the screensaver to prevent it disturbing
   def _sscb():
      try:
         ecore.exe_run('xdg-screensaver reset')
         return True
      except:
         return False
   ecore.Timer(59, _sscb)

   return True

def shoutdown():
   input_events.listener_del('gui')

def input_event_cb(event):
   if event == 'TOGGLE_FULLSCREEN':
      win.fullscreen = not win.fullscreen
      return input_events.EVENT_BLOCK
   elif event == 'SCALE_BIGGER':
      scale_bigger()
      return input_events.EVENT_BLOCK
   elif event == 'SCALE_SMALLER':
      scale_smaller()
      return input_events.EVENT_BLOCK
   elif event == 'SCALE_RESET':
      scale_reset()
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

def load_image(name, path = None):
   """
   @name include the ext but not the path (es 'my_image.png')
   @name can also be a full_path
   @path is searched if the image is not found in the theme
   @return ElmImage
   @example: load_image('my_image.png', os.path.dirname(__file__))
   """
   LOG('dbg', 'Requested image: ' + str(name))
   LOG('dbg', 'Estra path: ' + str(path))

   im = elementary.Image(gui.win)

   # if it's a full path load load it
   if os.path.exists(name):
      LOG('dbg', 'Found image:' + name)
      im.file_set(name)
      return im

   # try in main theme file (as group: image/$name)
   if edje.file_group_exists(theme_file, 'image/' + name):
      LOG('dbg', 'Found image in theme group: image/' + name)
      im.file_set(theme_file, 'image/' + name)
      return im

   # TODO search in some system dirs
   
   # try in caller path
   if path:
      full = os.path.join(path, name)
      if os.path.exists(full):
         LOG('dbg', 'Found image in extra path: image/' + name)
         im.file_set(full)
         return im

   LOG('err', 'Cannot load image: ' + str(name))
   return im

def ask_to_exit():
   d = EmcDialog(title = 'Exit MediaCenter ?', style = 'yesno',
                 done_cb = _cb_exit_yes)

def _cb_exit_yes(button):
   elementary.exit()

def toggle_fullscreen():
   pass

# mouse hide/show stuff
last_mouse_pos = (0, 0)
mouse_visible = True
mouse_skip_next = False

def mouse_hide():
   global last_mouse_pos
   global mouse_visible
   global mouse_skip_next
   
   if not mouse_visible: return

   xwin.cursor_hide()
   last_mouse_pos = xwin.pointer_xy_get()
   xwin.pointer_warp(2, 2)
   mouse_visible = False
   mouse_skip_next = True

def mouse_show():
   global last_mouse_pos
   global mouse_visible
   global mouse_skip_next

   if mouse_visible: return
   if mouse_skip_next:
      mouse_skip_next = False
      return

   xwin.pointer_warp(*last_mouse_pos)
   xwin.cursor_show()
   mouse_visible = True

def part_get(name):
   global layout
   return layout.edje_get().part_external_object_get(name)

def signal_emit(sig, src = 'emc'):
   global layout
   layout.edje_get().signal_emit(sig, src)

def signal_cb_add(emission, source, cb):
   layout.edje_get().signal_callback_add(emission, source, cb)

def text_set(part, text):
   global layout
   layout.edje_get().part_text_set(part, text)

def swallow_set(part, obj):
   old = layout.edje_get().part_swallow_get(part)
   if old: old.delete()
   layout.edje_get().part_swallow(part, obj)

def slider_val_set(part, value):
   layout.edje_get().part_drag_value_set(part, value, value)

def slider_val_get(part):
   return layout.edje_get().part_drag_value_get(part)

def box_append(part, obj):
   layout.edje_get().part_box_append(part, obj)

def box_prepend(part, obj):
   layout.edje_get().part_box_prepend(part, obj)

def box_remove(part, obj):
   layout.edje_get().part_box_remove(part, obj)

def scale_set(scale):
   win.scale_set(scale)

def scale_get():
   return win.scale_get()

def scale_bigger():
   win.scale_set(win.scale_get() + 0.1)

def scale_smaller():
   win.scale_set(win.scale_get() - 0.1)

def scale_reset():
   win.scale_set(1.0)

################################################################################
def background_set(image):
   global backdrop_im

   if not backdrop_im:
      backdrop_im = elementary.Image(gui.win)
      backdrop_im.fill_outside_set(True)
      swallow_set('bg.swallow.backdrop1', backdrop_im)

   backdrop_im.file_set(image)

################################################################################
class EmcButton(elementary.Button):
   """ TODO doc this """
   def __init__(self, label=None, icon = None):
      elementary.Button.__init__(self, layout)
      self.style_set('emc')
      self.focus_allow_set(False)
      if label:
         self.text_set(label)
      if icon:
         self.content_set(load_icon(icon))
      self.show()

   # def color_set(self, r, g, b):
      # self.ARGHHH

################################################################################
class EmcRemoteImage(elementary.Image):
   """ TODO doc this """

   def __init__(self, parent):
      elementary.Image.__init__(self, parent)
      self._parent = parent
      self._pb = elementary.Progressbar(parent)
      self._pb.style_set('wheel')
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
         utils.download_url_async(url, dest if dest else 'tmp',
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
      # print ('MOVE %d %d %d %d' % (x, y, w, h))
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
         self.file_set('')
         # TODO show a dummy image

   #TODO on image_set abort the download ? 

################################################################################
class EmcDialog(edje.Edje):
   """ TODO doc this
   style can be 'panel' or 'minimal'

   you can also apply special style that perform specific task:
      'info', 'error', 'warning', 'yesno', 'cancel', 'progress'
   """

   special_styles = ['info', 'error', 'warning', 'yesno', 'cancel', 'progress']
   dialogs_counter = 0

   fman = None
   
   def __init__(self, title = None, text = None, content = None,
                spinner = False, style = 'panel',
                done_cb = None, canc_cb = None):
      # load the right edje object
      if style in EmcDialog.special_styles or style == 'minimal':
         group = 'emc/dialog/minimal'
      else:
         group = 'emc/dialog/panel'
      edje.Edje.__init__(self, gui.layout.evas, file = theme_file, group = group)
      self.signal_callback_add('emc,dialog,close', '', self._close_pressed)
      self.signal_callback_add('emc,dialog,hide,done', '',
                               (lambda a,S,d: self._delete_real()))
      self.signal_callback_add('emc,dialog,show,done', '',
                               (lambda a,s,D: None))

      # put the dialog in the dialogs box of the main edje obj,
      # this way we only manage one edje and don't have stacking problems.
      # otherwise dialogs will stole the mouse events.
      self.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      self.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      box_append('dialogs.box.stack', self)

      EmcDialog.dialogs_counter += 1
      self._name = 'Dialog-' + str(EmcDialog.dialogs_counter)
      self._content = content
      self._done_cb = done_cb
      self._canc_cb = canc_cb
      self._buttons = []
      self.fman = EmcFocusManager2()

      # vbox
      self._vbox = elementary.Box(gui.win)
      self._vbox.horizontal_set(False)
      self._vbox.size_hint_align_set(evas.EVAS_HINT_FILL, 0.0)
      self._vbox.size_hint_weight_set(evas.EVAS_HINT_EXPAND, 0.0)
      self._vbox.show()
      self.part_swallow('emc.swallow.content', self._vbox)

      if title is not None:
         self.part_text_set('emc.text.title', title)
         self.signal_emit('emc,dialog,title,show', 'emc')
         # TODO hide the title in None
      
      if text is not None:
         self._textentry = elementary.Entry(gui.win)
         self._textentry.style_set('dialog')
         self._textentry.editable_set(False)
         self._textentry.context_menu_disabled_set(True)
         self._textentry.entry_set(text)
         self._textentry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         self._textentry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
         #~ self._textentry.size_hint_align_set(0.5, 0.5)
         self._vbox.pack_end(self._textentry)
         self._textentry.show()
      elif content is not None:
         frame = elementary.Frame(gui.win)
         frame.style_set('pad_medium')
         frame.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         frame.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
         frame.content_set(content)
         frame.show()
         self._vbox.pack_end(frame)

      if spinner:
         self._spinner = elementary.Progressbar(gui.win)
         self._spinner.style_set('wheel')
         self._spinner.pulse(True)
         self._spinner.show()
         self._vbox.pack_end(self._spinner)

      if style in EmcDialog.special_styles:
         self.signal_emit('emc,dialog,%s,set' % (style), 'emc')
         if title is None:
            self.part_text_set('emc.text.title', style)
            self.signal_emit('emc,dialog,title,show', 'emc')

      if style in ('info', 'error', 'warning'):
         self.button_add('Ok', (lambda btn: self.delete()))

      if style in ('yesno'):
         self.button_add('No', (lambda btn: self.delete()))
         self.button_add('Yes', (lambda btn: self._done_cb(self)))

      # Do we want the cancel button? we have the red-round-close...
      # if style in ('cancel'):
         # if canc_cb:
            # self.button_add('Cancel', (lambda btn: self._canc_cb(self)))
         # else:
            # self.button_add('Cancel', (lambda btn: self.delete()))

      input_events.listener_add(self._name, self._input_event_cb)
      
      self.show()
      self.signal_emit('emc,dialog,show', 'emc')

   def activate(self):
      print 'DEPRECATED EmcDialog.activate()'

   def delete(self):
      input_events.listener_del(self._name)
      self.fman.delete()
      self.signal_emit('emc,dialog,hide', 'emc')

   def _delete_real(self):
      if self.part_swallow_get('emc.swallow.content'):
         self.part_swallow_get('emc.swallow.content').delete()
      for b in self._buttons:
         b.delete()
      box_remove('dialogs.box.stack', self)
      edje.Edje.delete(self)
      del self

   def _close_pressed(self, a, s, d):
      if self._canc_cb:
         self._canc_cb(self)
      else:
         self.delete()

   def content_get(self):
      return self._content

   def button_add(self, label, selected_cb = None, cb_data = None, icon = None):
      if not self._buttons:
         self.signal_emit('emc,dialog,buttons,show', 'emc')

      b = EmcButton(label, icon)
      b.data['cb'] = selected_cb
      b.data['cb_data'] = cb_data
      b.callback_clicked_add(self._cb_buttons)
      self.fman.obj_add(b)
      self.part_box_prepend('emc.box.buttons', b)
      self._buttons.append(b)
      return b

   def buttons_clear(self):
      self.fman.delete()
      self.fman = EmcFocusManager()
      for b in self._buttons:
         b.delete()
      del self._buttons
      self._buttons = []

   def title_set(self, text):
      if text is not None:
         self.part_text_set('emc.text.title', text)
         self.signal_emit('emc,dialog,title,show', 'emc')
      else:
         self.signal_emit('emc,dialog,title,hide', 'emc')

   def title_get(self):
      return self.part_text_get('emc.text.title')

   def text_set(self, text):
      self._textentry.entry_set(text)

   def text_get(self):
      return self._textentry.entry_get()

   def text_append(self, text):
      self._textentry.entry_set(self._textentry.entry_get() + text)

   def spinner_start(self):
      self._spinner.show()
      self._spinner.pulse(True)

   def spinner_stop(self):
      self._spinner.pulse(False)
      self._spinner.hide()

   def progress_set(self, val):
      self.part_external_object_get('emc.dialog.progress').value_set(val)

   def _cb_buttons(self, button):
      selected_cb = button.data['cb']
      cb_data = button.data['cb_data']

      if selected_cb and cb_data:
         selected_cb(button, cb_data)
      elif selected_cb:
         selected_cb(button)

   def _input_event_cb(self, event):

      if event in ['BACK', 'EXIT']:
         if self._canc_cb:
            self._canc_cb(self)
         else:
            self.delete()
         return input_events.EVENT_BLOCK

      # if content is elm List or Genlist then automanage the events
      if self._content and type(self._content) in (elementary.List, elementary.Genlist):
         list = self._content
         item = list.selected_item_get()
         if not item:
            item = list.items_get()[0]

         horiz = False
         if type(self._content) is elementary.List:
            horiz = list.horizontal

         if (horiz and event == 'RIGHT') or \
            (not horiz and event == 'DOWN'):
            next = item.next_get()
            if next:
               next.selected_set(1)
               next.show()
               return input_events.EVENT_BLOCK

         if (horiz and event == 'LEFT') or \
            (not horiz and event == 'UP'):
            prev = item.prev_get()
            if prev:
               prev.selected_set(1)
               prev.show()
               return input_events.EVENT_BLOCK

      if self._buttons:
         if event == 'LEFT':
            self.fman.focus_move('l')
         if event == 'RIGHT':
            self.fman.focus_move('r')
   
      if event == 'OK':
         if self._buttons:
            self._cb_buttons(self.fman.focused_get())
         elif self._done_cb:
            self._done_cb(self)

      if event in ('LEFT', 'RIGHT', 'UP', 'DOWN', 'OK'):
         return input_events.EVENT_BLOCK
      else:
         return input_events.EVENT_CONTINUE

################################################################################
class EmcNotify(edje.Edje):
   """ TODO doc this"""

   def __init__(self, text, hidein=5.0):
      group = 'emc/notify/default'
      edje.Edje.__init__(self, gui.layout.evas, file = theme_file, group = group)
      self.part_text_set('emc.text.caption', text)
      gui.box_append('notify.box.stack', self)
      if hidein > 0.0:
         self.timer = ecore.Timer(hidein, self.hide_timer_cb)
      else:
         self.timer = None
      self.show()

   def hide_timer_cb(self):
      box_remove('notify.box.stack', self)
      self.delete()
      return ecore.ECORE_CALLBACK_CANCEL

   def close(self):
      if self.timer:
         self.timer.delete()
      self.hide_timer_cb()


###############################################################################
class EmcSourceSelector(EmcDialog):
   """ TODO doc this
   """

   def __init__(self, title = 'Source Selector', done_cb=None, cb_data=None):
      self._selected_cb = done_cb
      self._selected_cb_data = cb_data
      self._glist = elementary.Genlist(gui.win)
      self._glist.style_set('dialog')
      self._glist.homogeneous_set(True)
      self._glist.select_mode_set(elementary.ELM_OBJECT_SELECT_MODE_ALWAYS)
      self._glist.focus_allow_set(False)
      self._glist.callback_clicked_double_add(self._cb_item_selected)
      self._glist_itc = elementary.GenlistItemClass(item_style = 'default',
                                 text_get_func = self._genlist_folder_label_get,
                                 content_get_func = self._genlist_folder_icon_get)
      self._glist_itc_back = elementary.GenlistItemClass(item_style = 'default',
                                 text_get_func = self._genlist_back_label_get,
                                 content_get_func = self._genlist_back_icon_get)
      
      EmcDialog.__init__(self, title, content=self._glist, style='panel')
      self.button_add('select', selected_cb = self._cb_done_selected)
      btn = self.button_add('browse', selected_cb = self._cb_browse_selected)
      self.fman.focused_set(btn)

      self.populate(os.getenv('HOME'))

   def populate(self, folder):
      self._glist.clear()

      parent_folder = os.path.normpath(os.path.join(folder, '..'))
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
         if self._selected_cb_data:
            self._selected_cb('file://' + item.data_get(), self._selected_cb_data)
         else:
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
      return 'back'

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
   # this is here to hide another bug somewhere, seems __init__ is
   # not executed as I get:
   #   'EmcFocusManager' object has no attribute 'objs'
   # happend when the delete() method is executed...
   # ...obj should always exists, also without this line.  :/
   objs = []

   def __init__(self):
      self.objs = []
      self.focused = None

   def delete(self):
      """
      Delete the FocusManager instance and free all the resources used
      """
      if self.objs:
         for o in self.objs:
            o.on_mouse_in_del(self._mouse_in_cb)
         del self.objs
      del self

   def obj_add(self, obj):
      """
      Add an object to the chain, obj must be an evas object that support
      disabled_set() 'interface', usually an elementary obj will do the work.
      """
      if not self.focused:
         self.focused = obj
         obj.disabled_set(False)
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
class EmcFocusManager2(object):
   """
   This class manage a list of elementary objects, usually buttons.
   You provide all the objects that can receive focus and the class
   will take care of selecting the right object when you move the selection
   Dont forget to call the delete() method when not needed anymore!!
   If you want the class to automanage input events just pass an unique name
   as the autoeventsname param. 
   """

   def __init__(self, autoeventsname=None):
      self.objs = []
      self.focused = None
      self.autoeventsname = autoeventsname
      if autoeventsname is not None:
         input_events.listener_add(autoeventsname, self._input_event_cb)

   def delete(self):
      """ Delete the FocusManager instance and free all the used resources """
      if self.autoeventsname is not None:
         input_events.listener_del(self.autoeventsname)

      if self.objs:
         for o in self.objs:
            o.on_mouse_in_del(self._mouse_in_cb)
         del self.objs
      del self

   def obj_add(self, obj):
      """
      Add an object to the chain, obj must be an evas object that support
      the focus_set() 'interface', usually an elementary obj will do the work.
      """
      if not self.focused:
         self.focused = obj
         # obj.focus_set(True)
         obj.disabled_set(False)
      else:
         # obj.focus_set(False)
         obj.disabled_set(True)
      obj.on_mouse_in_add(self._mouse_in_cb)
      self.objs.append(obj)

   def focused_set(self, obj):
      """ Give focus to the given obj """
      # obj.focus_set(True)
      if self.focused:
         self.focused.disabled_set(True)
      obj.disabled_set(False)
      self.focused = obj

   def focused_get(self):
      """ Get the object that has focus """
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
      """ Get the list of all the objects that was previously added """
      return self.objs

   def _mouse_in_cb(self, obj, event):
      if self.focused != obj:
         self.focused_set(obj)

   def _input_event_cb(self, event):
      if event == 'LEFT':
         self.focus_move('l')
         return input_events.EVENT_BLOCK
      if event == 'RIGHT':
         self.focus_move('r')
         return input_events.EVENT_BLOCK
      if event == 'UP':
         self.focus_move('u')
         return input_events.EVENT_BLOCK
      if event == 'DOWN':
         self.focus_move('d')
         return input_events.EVENT_BLOCK
      return input_events.EVENT_CONTINUE

###############################################################################
# class EmcVKeyboard(elementary.InnerWindow):
class EmcVKeyboard(EmcDialog):
   """ TODO doc this """
   def __init__(self, accept_cb = None, dismiss_cb = None,
                title = None, text = None):
      """ TODO doc this """

      self.accept_cb = accept_cb
      self.dismiss_cb = dismiss_cb
      self.current_button = None

      # table
      tb = elementary.Table(gui.win)
      tb.homogeneous_set(True)
      tb.show()

      # set dialog title
      self.part_text_set('emc.text.title', title or 'Insert text')

      # entry
      self.entry = elementary.Entry(gui.win) # TODO use scrolled_entry instead
      self.entry.style_set('vkeyboard')
      self.entry.editable_set(False)
      self.entry.single_line_set(True)
      self.entry.focus_allow_set(False)
      self.entry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      self.entry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      if text: self.text_set(text)
      tb.pack(self.entry, 0, 0, 10, 1)
      self.entry.show()

      # focus manager
      self.efm = EmcFocusManager2()

      # standard keyb
      for i, c in enumerate(['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']):
         self._pack_btn(tb, i, 1, 1, 1, c, cb = self._default_btn_cb)
      for i, c in enumerate(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']):
         self._pack_btn(tb, i, 2, 1, 1, c, cb = self._default_btn_cb)
      for i, c in enumerate(['k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't']):
         self._pack_btn(tb, i, 3, 1, 1, c, cb = self._default_btn_cb)
      for i, c in enumerate(['u', 'v', 'w', 'x', 'y', 'z', '.', '@', '-', '_']):
         self._pack_btn(tb, i, 4, 1, 1, c, cb = self._default_btn_cb)

      self._pack_btn(tb, 0, 5, 3, 1, 'ERASE', cb = self._erase_cb)
      self._pack_btn(tb, 3, 5, 4, 1, 'SPACE', cb = self._space_cb)
      self._pack_btn(tb, 7, 5, 3, 1, 'UPPERCASE', cb = self._uppercase_cb)

      self._pack_btn(tb, 0, 6, 4, 1, 'Dismiss', 'icon/cancel', self._dismiss_cb)
      self._pack_btn(tb, 6, 6, 4, 1, 'Accept',  'icon/ok',     self._accept_cb)

      # init the parent EmcDialog class
      EmcDialog.__init__(self, title = title, style = 'minimal', content = tb)

       # catch input events
      input_events.listener_add('vkbd', self.input_event_cb)

   def _pack_btn(self, tb, x, y, w, h, label, icon = None, cb = None):
      b = EmcButton(label=label, icon=icon)
      b.size_hint_weight_set(evas.EVAS_HINT_EXPAND, 0.0)
      b.size_hint_align_set(evas.EVAS_HINT_FILL, 0.0)
      if cb: b.callback_clicked_add(cb)
      b.data['cb'] = cb
      self.efm.obj_add(b)
      tb.pack(b, x, y, w, h)
      return b

   def delete(self):
      input_events.listener_del('vkbd')
      self.efm.delete()
      EmcDialog.delete(self)

   def text_set(self, text):
      self.entry.text = text
      self.entry.cursor_end_set()

   def _dismiss_cb(self, button):
      if self.dismiss_cb and callable(self.dismiss_cb):
         self.dismiss_cb(self)
      self.delete()

   def _accept_cb(self, button):
      if self.accept_cb and callable(self.accept_cb):
         self.accept_cb(self, self.entry.entry_get())
      self.delete()

   def _default_btn_cb(self, button):
      self.entry.cursor_end_set()
      self.entry.entry_insert(button.text)

   def _erase_cb(self, button):
      if len(self.entry.text) > 0:
         self.entry.text = self.entry.text[0:-1]

   def _space_cb(self, button):
      self.entry.entry_insert(' ')

   def _uppercase_cb(self, button):
      for btn in self.efm.all_get():
         c = btn.label
         if len(c) == 1 and c.isalpha():
            if c.islower():
               btn.label = c.upper()
               button.label = 'LOWERCASE'
            else:
               btn.label = c.lower()
               button.label = 'UPPERCASE'
      self.entry.cursor_end_set()

   def input_event_cb(self, event):
      if event == 'OK':
         btn = self.efm.focused_get()
         if callable(btn.data['cb']):
            btn.data['cb'](btn)
      elif event == 'EXIT':
         self._dismiss_cb(None)
      elif event == 'LEFT':  self.efm.focus_move('l')
      elif event == 'RIGHT': self.efm.focus_move('r')
      elif event == 'UP':    self.efm.focus_move('u')
      elif event == 'DOWN':  self.efm.focus_move('d')         
      
      return input_events.EVENT_BLOCK
  
