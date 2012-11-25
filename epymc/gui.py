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

import evas, ecore, edje, elementary
import ecore.x #used only to show/hide the cursor

import utils, ini, gui, events, input_events
from widgets import EmcButton, EmcDialog


win = None
xwin = None
layout = None
theme_file = None
backdrop_im = None

_volume_hide_timer = None
_last_mouse_pos = (0, 0)
_mouse_visible = True
_mouse_skip_next = False


DEBUG = True
DEBUGN = 'GUI'
def LOG(sev, msg):
   if   sev == 'err': print('%s ERROR: %s' % (DEBUGN, msg))
   elif sev == 'inf': print('%s: %s' % (DEBUGN, msg))
   elif sev == 'dbg' and DEBUG: print('%s: %s' % (DEBUGN, msg))


def init():
   global win, xwin, layout, theme_file

   # get config values, setting defaults if needed
   theme_name = ini.get('general', 'theme', default_value = 'default')
   evas_engine = ini.get('general', 'evas_engine', default_value = 'software_x11')
   scale = ini.get('general', 'scale', default_value = 1.0)
   fullscreen = ini.get('general', 'fullscreen', False)

   # search the theme file, or use the default one
   theme_file = utils.get_resource_file('themes', theme_name + '.edj', 'default.edj')
   if not theme_file:
      LOG('err', 'cannot find a working theme file, exiting...')
      return False
   LOG('inf', 'Using theme: ' + theme_file)
   
   # custom elementary theme
   elementary.theme_overlay_add(theme_file) # TODO REMOVE ME!!! it's here for buttons
   elementary.theme_extension_add(theme_file)

   # preferred evas engine
   # this seems totally buggy in elm, I should just do the preferred one
   elementary.preferred_engine_set(evas_engine)
   elementary.engine_set(evas_engine)

   # create the elm window
   win = elementary.Window('epymc', elementary.ELM_WIN_BASIC)
   win.title_set('Enlightenment Media Center')
   win.callback_delete_request_add(lambda w: ask_to_exit())
   if fullscreen == 'True':
      win.fullscreen_set(1)
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
   win.scale_set(float(scale))

   # fill view buttons box in topbar
   bt = EmcButton(win, icon = 'icon/list')
   bt.callback_clicked_add(lambda b: input_events.event_emit('VIEW_LIST'))
   gui.box_append('topbar.box', bt)
   bt.show()

   bt = EmcButton(win, icon = 'icon/grid')
   bt.callback_clicked_add(lambda b: input_events.event_emit('VIEW_GRID'))
   gui.box_append('topbar.box', bt)
   bt.show()
   
   # listen to events and input_events
   input_events.listener_add('gui', _input_event_cb)
   events.listener_add('gui', _event_cb)

   # once a minute ping the screensaver to prevent it disturbing
   def _sscb():
      try:
         ecore.exe_run('xdg-screensaver reset')
         return True # renew the timer
      except:
         return False # abort the timer
   ecore.Timer(59, _sscb)

   return True

def shutdown():
   events.listener_del('gui')
   input_events.listener_del('gui')


### Various externally accessible functions ###
def load_icon(icon):
   """
   @icon can be a full path (if start with a '/' or
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
   LOG('dbg', 'Extra path: ' + str(path))

   im = elementary.Image(gui.win)

   # if it's a full path just load it
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
                 done_cb = lambda b: elementary.exit())

def volume_show(hidein = 0):
   global _volume_hide_timer
   gui.signal_emit('volume,show')
   if hidein > 0:
      if _volume_hide_timer: _volume_hide_timer.delete()
      _volume_hide_timer = ecore.Timer(hidein, volume_hide)

def volume_hide():
   global _volume_hide_timer
   gui.signal_emit('volume,hide')
   _volume_hide_timer = None

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

def background_set(image):
   global backdrop_im

   if not backdrop_im:
      backdrop_im = elementary.Image(gui.win)
      backdrop_im.fill_outside_set(True)
      swallow_set('bg.swallow.backdrop1', backdrop_im)

   backdrop_im.file_set(image)

def mouse_hide():
   global _last_mouse_pos, _mouse_visible, _mouse_skip_next
   
   if not _mouse_visible: return

   xwin.cursor_hide()
   _last_mouse_pos = xwin.pointer_xy_get()
   xwin.pointer_warp(2, 2)
   _mouse_visible = False
   _mouse_skip_next = True

def mouse_show():
   global _last_mouse_pos, _mouse_visible, _mouse_skip_next

   if _mouse_visible:
      return
   
   if _mouse_skip_next:
      _mouse_skip_next = False
      return

   xwin.pointer_warp(*_last_mouse_pos)
   xwin.cursor_show()
   _mouse_visible = True


### Simple edje abstraction ###
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


### Internal functions ###
def _input_event_cb(event):
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

def _event_cb(event):
   if event == 'VOLUME_CHANGED':
      volume_show(hidein = 3)
