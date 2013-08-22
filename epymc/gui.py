#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2013 Davide Andreoli <dave@gurumeditation.it>
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

import os, time, re

try:
   from efl import evas, ecore, edje, elementary
   from efl.elementary.window import Window
   from efl.elementary.layout import Layout
   from efl.elementary.icon import Icon
   from efl.elementary.image import Image
   from efl.elementary.button import Button
   from efl.elementary.menu import Menu
   from efl.elementary.progressbar import Progressbar
   from efl.elementary.box import Box
   from efl.elementary.entry import Entry
   from efl.elementary.scroller import Scroller
   from efl.elementary.frame import Frame
   from efl.elementary.list import List
   from efl.elementary.table import Table
   from efl.elementary.genlist import Genlist, GenlistItemClass
except:
   import evas, ecore, edje, elementary
   import ecore.x #used only to show/hide the cursor
   from elementary import Window, Layout, Icon, Image, Button, Menu, \
      Progressbar, Box, Entry, Scroller, Frame, List, Table, Genlist, \
      GenlistItemClass

from . import utils, ini, events, input_events
# from .widgets import EmcButton, EmcDialog, EmcNotify, EmcRemoteImage


win = None
xwin = None
layout = None
theme_file = None
backdrop_im = None

_volume_hide_timer = None
_last_mouse_pos = (0, 0)
_mouse_visible = True
_mouse_skip_next = False
_screensaver_ts = 0
_screensaver_status = 0 # 0=inactive 1=active 2=monitor_off


DEBUG = False
DEBUGN = 'GUI'
def LOG(sev, msg):
   if   sev == 'err': print('%s ERROR: %s' % (DEBUGN, msg))
   elif sev == 'inf': print('%s: %s' % (DEBUGN, msg))
   elif sev == 'dbg' and DEBUG: print('%s: %s' % (DEBUGN, msg))


def init():
   """ return: 0=failed 1=ok 2=fallback_engine"""
   global win, xwin, layout, theme_file
   global _screensaver_ts, _screensaver_status

   # get config values, setting defaults if needed
   theme_name = ini.get('general', 'theme', default_value = 'default')
   evas_engine = ini.get('general', 'evas_engine', default_value = 'software_x11')
   fps = ini.get('general', 'fps', default_value = 30)
   scale = ini.get('general', 'scale', default_value = 1.0)
   fullscreen = ini.get('general', 'fullscreen', False)
   ini.add_section('screensaver')
   unused = ini.get('screensaver', 'on_after', 'never')
   unused = ini.get('screensaver', 'monitor_off_after', 'never')
   unused = ini.get('screensaver', 'keepalive_cmd', 'xdg-screensaver reset')
   unused = ini.get('screensaver', 'activate_cmd', 'xdg-screensaver activate')
   unused = ini.get('screensaver', 'monitor_off_cmd', 'xset dpms force off')
   unused = ini.get('screensaver', 'only_in_fs', 'True')

   # search the theme file, or use the default one
   if not os.path.isabs(theme_name):
      theme_file = utils.get_resource_file('themes', theme_name + '.edj', 'default.edj')
      if not theme_file:
         LOG('err', 'cannot find a working theme file, exiting...')
         return 0
   else:
      theme_file = theme_name

   # custom elementary theme
   set_theme_file(theme_file)

   # create the elm window
   try:
      elementary.preferred_engine_set(evas_engine)
      win = Window('epymc', elementary.ELM_WIN_BASIC)
      LOG('inf', 'Using evas engine: ' + evas_engine)
      ret = 1
   except:
      elementary.preferred_engine_set('software_x11')
      win = Window('epymc', elementary.ELM_WIN_BASIC)
      LOG('err', 'Falling back to standard_x11')
      ret = 2

   # configure the win
   win.title_set('Enlightenment Media Center')
   win.callback_delete_request_add(lambda w: ask_to_exit())
   if fullscreen == 'True':
      win.fullscreen_set(1)
   # get the X window object, we need it to show/hide the mouse cursor
   try:
      xwin = ecore.x.Window_from_xid(win.xwindow_xid_get())
   except:
      LOG('inf', 'ecore.x not available. Cannot hide / show the mouse pointer')
      xwin = None

   # main layout (main theme)
   layout = Layout(win)
   layout.file_set(theme_file, 'emc/main/layout')
   layout.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
   win.resize_object_add(layout)
   layout.show()
   # show the mouse when moved
   layout.edje.signal_callback_add("mouse,move", "*",
                                   (lambda o,e,s: mouse_show()))
   # right click for BACK
   layout.edje.signal_callback_add("mouse,up,3", "*",
                                   (lambda o,e,s: input_events.event_emit('BACK')))

   win.show()
   win.scale_set(float(scale))

   # fill view buttons box in topbar
   bt = EmcButton(icon = 'icon/list')
   bt.callback_clicked_add(lambda b: input_events.event_emit('VIEW_LIST'))
   box_append('topbar.box', bt)
   bt.show()

   bt = EmcButton(icon = 'icon/grid')
   bt.callback_clicked_add(lambda b: input_events.event_emit('VIEW_GRID'))
   box_append('topbar.box', bt)
   bt.show()
   
   # listen to events and input_events
   input_events.listener_add('gui', _input_event_cb)
   events.listener_add('gui', _event_cb)

   # set efl frames per second
   fps_set(fps)

   # timer that manage the screensaver/monitor policy
   _screensaver_ts = time.time()
   _screensaver_status = 0
   ecore.Timer(30, _screensaver_timer_cb)

   return ret

def shutdown():
   events.listener_del('gui')
   input_events.listener_del('gui')



### Various externally accessible functions ###
def get_available_themes():
   # search in user config dir
   d = os.path.join(utils.config_dir_get(), 'themes')
   L = [os.path.join(d, name) for name in os.listdir(d) if name.endswith('.edj')]

   # search relative to the script (epymc.py) dir
   d = os.path.join(utils.base_dir_get(), 'data', 'themes')
   L += [os.path.join(d, name) for name in os.listdir(d) if name.endswith('.edj')]

   return L

def get_theme_info(theme):
   D = {}
   D['name'] = edje.file_data_get(theme, 'theme.name') or 'Unknown'
   D['version'] = edje.file_data_get(theme, 'theme.version') or ''
   D['author'] = edje.file_data_get(theme, 'theme.author') or 'Unknown'
   D['info'] = edje.file_data_get(theme, 'theme.info') or 'Unknown'
   return D

def set_theme_file(path):
   global theme_file

   LOG('inf', 'Using theme: ' + path)
   elementary.theme_overlay_add(path) # TODO REMOVE ME!!! it's here for buttons, and others
   elementary.theme_extension_add(path)
   theme_file = path

def load_icon(icon):
   """
   @icon can be a full path (if start with a '/' or
         can be a theme icon (ex: icon/folder).
   see icons.edc for all the existing icon
   """
   if type(icon) in (Icon, Image, EmcRemoteImage, EmcRemoteImage2):
      return icon
   ic = Icon(win)
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

   im = Image(win)

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

   # try in main theme file (as group: $name) (thus you can load 'icon/*')
   if edje.file_group_exists(theme_file, name):
      LOG('dbg', 'Found image in theme group: ' + name)
      im.file_set(theme_file, name)
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
   text = '<center>' + credits.replace('\n', '<br>') + '</center>'
   d = EmcDialog(title = 'credits', style = 'minimal', text = text)
   d.button_add("Cancel", selected_cb = lambda b: d.delete())
   d.button_add("Suspend", selected_cb = None)
   d.button_add("Shutdown", selected_cb = None)
   d.button_add("Exit", selected_cb = lambda b: elementary.exit())
   d.autoscroll_enable()

def volume_show(hidein = 0):
   global _volume_hide_timer
   signal_emit('volume,show')
   if hidein > 0:
      if _volume_hide_timer: _volume_hide_timer.delete()
      _volume_hide_timer = ecore.Timer(hidein, volume_hide)

def volume_hide():
   global _volume_hide_timer
   signal_emit('volume,hide')
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
      backdrop_im = Image(win)
      backdrop_im.fill_outside_set(True)
      swallow_set('bg.swallow.backdrop1', backdrop_im)

   backdrop_im.file_set(image)

def mouse_hide():
   global _last_mouse_pos, _mouse_visible, _mouse_skip_next
   
   if not _mouse_visible: return

   if xwin is not None:
      xwin.cursor_hide()
      _last_mouse_pos = xwin.pointer_xy_get()
      xwin.pointer_warp(2, 2)

   _mouse_visible = False
   _mouse_skip_next = True

def mouse_show():
   global _last_mouse_pos, _mouse_visible, _mouse_skip_next

   renew_screensaver()

   if _mouse_visible:
      return
   
   if _mouse_skip_next:
      _mouse_skip_next = False
      return

   if xwin is not None:
      xwin.pointer_warp(*_last_mouse_pos)
      xwin.cursor_show()

   _mouse_visible = True

def renew_screensaver():
   global _screensaver_ts, _screensaver_status

   _screensaver_ts = time.time()
   if _screensaver_status != 0:
      _screensaver_status = 0
      _screensaver_timer_cb()

def fps_set(fps):
   ecore.animator_frametime_set(1.0 / float(fps))

### audio info/controls notify
_audio_notify = None

def audio_controls_show(text = None, icon = None):
   global _audio_notify
   
   if _audio_notify is None:
      _audio_notify = EmcNotify('', hidein = 0)

   if text or icon:
       audio_controls_set(text, icon)

def audio_controls_hide():
   global _audio_notify
   
   if _audio_notify:
      _audio_notify.close()
      _audio_notify = None

def audio_controls_set(text = None, icon = None):
   if _audio_notify is None:
      return
   if text: _audio_notify.text_set(text)
   if icon: _audio_notify.icon_set(icon)


### Simple edje abstraction ###
def part_get(name):
   return layout.edje_get().part_external_object_get(name)

def signal_emit(sig, src = 'emc'):
   layout.edje_get().signal_emit(sig, src)

def signal_cb_add(emission, source, cb):
   layout.edje_get().signal_callback_add(emission, source, cb)

def text_set(part, text):
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
def _screensaver_timer_cb():
   global _screensaver_status # 0=inactive 1=active 2=monitor_off

   # not when windowed
   if not win.fullscreen and ini.get('screensaver', 'only_in_fs') == 'True':
      return True # renew the timer
   
   # get someting like "5 minutes" from config
   try:
      ss_on_after = ini.get('screensaver', 'on_after')
      ss_on_after = int(re.sub('[^0-9]', '', ss_on_after)) * 60
   except:
      ss_on_after = 0

   # get someting like "10 minutes" from config
   try:
      monitor_off_after = ini.get('screensaver', 'monitor_off_after')
      monitor_off_after = int(re.sub('[^0-9]', '', monitor_off_after)) * 60
   except:
      monitor_off_after = 0

   # got nothing to do
   if ss_on_after == monitor_off_after == 0:
      return True # renew the timer

   # calc elapsed time since last user input
   now = time.time()
   elapsed = now - _screensaver_ts
   LOG('dbg', "ScreenSaver: Timer! status: %d  elapsed: %f  ss_on_in: %.0f  mon_off_in: %.0f" % \
        (_screensaver_status, elapsed,
         _screensaver_ts + ss_on_after - now if ss_on_after > 0 else -1,
         _screensaver_ts + monitor_off_after - now if monitor_off_after > 0 else -1))

   def exe_run(cmd):
      try:
         ecore.exe_run(cmd)
         return True
      except:
         return False

   if _screensaver_status == 0:
      # Status 0: the screensaver is off - user active
      if ss_on_after > 0 and elapsed > ss_on_after:
         # turn on the screensaver
         LOG('dbg', 'ScreenSaver: activate screensaver')
         _screensaver_status = 1
         exe_run(ini.get('screensaver', 'activate_cmd'))
      elif monitor_off_after > 0 and elapsed > monitor_off_after:
         # turn off the monitor
         LOG('dbg', 'ScreenSaver: monitor off')
         _screensaver_status = 2
         exe_run(ini.get('screensaver', 'monitor_off_cmd'))
      else:
         # or keep the screensaver alive
         LOG('dbg', 'ScreenSaver: keep alive')
         exe_run(ini.get('screensaver', 'keepalive_cmd'))

   elif _screensaver_status == 1:
      # Status 1: the screensaver is on - user away
      if monitor_off_after > 0 and elapsed > monitor_off_after:
         # turn off the monitor
         LOG('dbg', 'ScreenSaver: monitor off')
         _screensaver_status = 2
         exe_run(ini.get('screensaver', 'monitor_off_cmd'))

   elif _screensaver_status == 2:
      # Status 2: the monitor is off - user probably sleeping :)
      pass

   return True # renew the timer

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




credits = """







programming
DAVIDE ANDREOLI


graphics
DAVIDE ANDREOLI


edc design
DAVIDE ANDREOLI


python efl
BORIS FAURE
BRUNO DILLY
DAVE ANDREOLI
FABIANO FIDÊNCIO
GUSTAVO SVERZUT BARBIERI
JOOST ALBERS
KAI HUUHKO
SIMON BUSCH
TIAGO FALCÃO


efl team
ADAM SIMPKINS
AHARON HILLEL
ALBIN TONNERRE
ALEXANDRE BECOULET
ALEXEY YAKOVENKO
ANDRE DIEB
ANDREW ELCOCK
ARNAUD DE TURCKHEIM
BERNHARD NEMEC
BORIS FAURE
BLUEZERY
BORIS FAURE
BRETT NASH
BRIAN MATTERN
BRUNO DILLY
CARSTEN HAITZLER
CEDRIC BAIL
CHIDAMBAR ZINNOURY
CHRIS ROSS
CHRISTOPHE DUMEZ
CHRISTOPHER MICHAEL
CHRISTOPHE SADOINE
CHUNEON PARK
COREY DONOHOE
DAN SINCLAIR
DANIEL JUYUNG SEO
DANIEL STENBERG
DANIEL WILLMANN
DANIEL ZAOUI
DAN SINCLAIR
DAVIDE ANDREOLI
DAVID GOODLAD
DAVID SEIKEL
DOYOUN KANG
EDUARDO LIMA
FABIANO FIDÊNCIO
FLAVIO CEOLIN
GOVINDARAJU SM
GUILHERME SILVEIRA
GUILLAUME FRILOUX
GUSTAVO CHAVES
GUSTAVO LIMA CHAVES
GUSTAVO SVERZUT BARBIERI
GWANGLIM LEE
HAIFENG DENG
HISHAM MARDAM BEY
HOWELL TAM
HUGO CAMBOULIVE
HYOYOUNG CHANG
IBUKUN OLUMUYIWA
IGOR MURZOV
IVÁN BRIANO
JAEHWAN KIM
JÉRÉMY ZURCHER
JÉRÔME PINOT
JIHOON KIM
JIM KUKUNAS
JIYOUN PARK
JONAS M. GASTAL
JORGE LUIS ZAPATA
JOSE O GONZALEZ
JOSÉ ROBERTO DE SOUZA
KEITH MARSHALL
KIM SHINWOO
KIM WOELDERS
KIM YUNHAN
LANCE FETTERS
LARS MUNCH
LEANDRO DORILEO
LEANDRO PEREIRA
LEANDRO SANTIAGO
LEIF MIDDELSCHULTE
LIONEL ORRY
LUCAS DE MARCHI
LUIS FELIPE STRANO MORAES
MATHIEU TAILLEFUMIER
MATT BARCLAY
MICHAEL BOUCHAUD
MICHAEL LAUER
MICHAL PAKULA VEL RUTKA
MIKAEL SANS
MIKE BLUMENKRANTZ
MIKE MCCORMACK
MYOUNGWOON ROY KIM
MYUNGJAE LEE
NATHAN INGERSOLL
NATHAN INGERSOLL
NICHOLAS CURRAN
NICHOLAS HUGHART
NICOLAS AGUIRRE
PATRYK KACZMAREK
PAUL VIXIE
PETER WEHRFRITZ
PIERRE LE MAGOUROU
PRINCE KUMAR DUBEY
RAFAEL ANTOGNOLLI
RAFAL KRYPA
RAJEEV RANJAN
RAPHAEL KUBO DA COSTA
RICARDO DE ALMEIDA GONZAGA
ROBERT DAVID
RUI MIGUEL SILVA SEABRA
SANGHO PARK
SEBASTIAN DRANSFELD
SEONG-HO CHO
SEUNGSOO WOO
SHILPA SINGH
SIMON POOLE
SOHYUN KIM
STEFAN SCHMIDT
STEPHEN HOUSTON
STEVE IRELAND
SUNG W. PARK
THIERRY EL BORGI
TIAGO FALCÃO
TILL ADAM
TILMAN SAUERBECK
TIM HORTON
TOM GILBERT
TOM HACOHEN
TOR LILLQVIST
VIKRAM NARAYANAN
VINCENT TORRI
VINCENT RICHOMME
WILLEM MONSUWE
WOOHYUN JUNG
YAKOV GOLDBERG
YOUNESS ALAOUI
YURI HUDOBIN
ZBIGNIEW KOSINSKI
ZIGSMCKENZIE


author special thanks
SARA
TEODORO
MONOPOLIO DI STATO


license
Copyright © 2010-2013 Davide Andreoli <dave@gurumeditation.it>

EpyMC is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

EpyMC is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with EpyMC. If not, see http://www.gnu.org/licenses/







"""

################################################################################
class EmcButton(Button):
   """ TODO documentation """

   def __init__(self, label = None, icon = None):
      Button.__init__(self, layout)
      self.style_set('emc')
      self.focus_allow_set(False)
      if label: self.text_set(label)
      if icon: self.content_set(load_icon(icon))
      self.show()

################################################################################
class EmcMenu(Menu):
   """ TODO doc this """

   def __init__(self, relto = None):
      Menu.__init__(self, layout)
      self.style_set('emc')
      if relto:
         # TODO better pos calc
         x, y, w, h = relto.geometry
         self.move(x, y + h)

      input_events.listener_add("EmcMenu", self._input_event_cb)
      self.callback_clicked_add(self._dismiss_cb)
      self.show()

   def item_add(self, parent = None, label = None, icon = None, callback = None, *args, **kwargs):
      item = Menu.item_add(self, parent, label, icon, self._item_selected_cb, callback, *args, **kwargs)
      if self.selected_item_get() is None:
         item.selected_set(True)

   def close(self):
      input_events.listener_del("EmcMenu")
      Menu.close(self)

   def _item_selected_cb(self, menu, item, cb, *args, **kwargs):
      input_events.listener_del("EmcMenu")
      if callable(cb):
         cb(menu, item, *args, **kwargs)
      
   def _dismiss_cb(self, menu):
      input_events.listener_del("EmcMenu")

   def _input_event_cb(self, event):
      if event == 'UP':
         item = self.selected_item_get()
         if not item or not item.prev:
            return input_events.EVENT_BLOCK
         while item.prev and item.prev.is_separator():
            item = item.prev
         item.prev.selected_set(True)
         return input_events.EVENT_BLOCK

      elif event == 'DOWN':
         item = self.selected_item_get()
         if not item or not item.next:
            return input_events.EVENT_BLOCK
         while item.next and item.next.is_separator():
            item = item.next
         item.next.selected_set(True)
         return input_events.EVENT_BLOCK

      elif event == 'OK':
         item = self.selected_item_get()
         args, kwargs = self.selected_item_get().data_get()
         cb = args[0]
         if cb and callable(cb):
            cb(self, item, *args[1:], **kwargs)
         # self.close() # not sure I want this :/
         return input_events.EVENT_BLOCK

      elif event == 'BACK' or event == 'EXIT':
         self.close()
         return input_events.EVENT_BLOCK

      elif event in ('LEFT', 'RIGHT'):
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

################################################################################
class EmcRemoteImage2(Image):
   """ THIS ONE USE Image remote url feature that is 1.8 only !!
       not used atm, waiting to drop 1.7 support
       also waiting for a "dest" suppoort in Image
   """

   def __init__(self, url = None, dest = None):
      Image.__init__(self, layout)
      self.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      self.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      
      self.on_move_add(self._cb_move_resize)
      self.on_resize_add(self._cb_move_resize)
      self._spinner = Progressbar(self)
      self._spinner.style_set('wheel')
      self._spinner.pulse = True
      self.callback_download_start_add(lambda o: self.start_spin())
      self.callback_download_done_add(lambda o: self.stop_spin())
      self.callback_download_error_add(lambda o: self.stop_spin())# TODO show a dummy img
      if url: self.url_set(url, dest)

   def show(self):
      Image.show(self)

   def hide(self):
      self._spinner.hide()
      Image.hide(self)

   def url_set(self, url, dest = None):
      if dest and os.path.exists(dest):
         self.file_set(dest)
      else:
         self.file_set(url)

   def start_spin(self):
      self.show()
      self._spinner.show()
      self._spinner.pulse(True)

   def stop_spin(self):
      self._spinner.hide()
      self._spinner.pulse(False)

   def _cb_move_resize(self, obj):
      (x, y, w, h) = self.geometry_get()
      self._spinner.resize(w, h)
      self._spinner.move(x, y)
      if self._spinner.clip != self.clip:
         self._spinner.clip = self.clip



class EmcRemoteImage(Image):
   """ TODO documentation """
   """ TODO on image_set abort the download ? """

   def __init__(self, url = None, dest = None):
      Image.__init__(self, layout)
      self.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      self.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      self.on_move_add(self._cb_move_resize)
      self.on_resize_add(self._cb_move_resize)
      self._spinner = Progressbar(layout)
      self._spinner.style_set('wheel')
      if url: self.url_set(url, dest)

   def show(self):
      Image.show(self)

   def hide(self):
      self._spinner.hide()
      Image.hide(self)

   def url_set(self, url, dest = None):
      if dest and os.path.exists(dest):
         self.file_set(dest)
      else:
         self.file_set('')
         self.start_spin()
         utils.download_url_async(url, dest if dest else 'tmp',
                                  complete_cb = self._cb_download_complete)

   def start_spin(self):
      self.show()
      self._spinner.show()
      self._spinner.pulse(True)

   def stop_spin(self):
      self._spinner.hide()
      self._spinner.pulse(False)

   def _cb_move_resize(self, obj):
      (x, y, w, h) = self.geometry_get()
      self._spinner.resize(w, h)
      self._spinner.move(x, y)
      if self._spinner.clip != self.clip:
         self._spinner.clip = self.clip

   def _cb_download_complete(self, dest, status):
      self.stop_spin()
      if status == 200: # Successfull HTTP code
         self.file_set(dest)
      else:
         # TODO show a dummy image
         self.file_set('')

################################################################################
class EmcDialog(edje.Edje):
   """ TODO doc this
   style can be 'panel' or 'minimal'

   you can also apply special style that perform specific task:
      'info', 'error', 'warning', 'yesno', 'cancel', 'progress', 'list'
   """

   minimal_styles = ['info', 'error', 'warning', 'yesno', 'cancel', 'progress']
   dialogs_counter = 0
   fman = None
   
   def __init__(self, title = None, text = None, content = None,
                spinner = False, style = 'panel',
                done_cb = None, canc_cb = None, user_data = None):

      # load the right edje object
      if style in EmcDialog.minimal_styles or style == 'minimal':
         group = 'emc/dialog/minimal'
      else:
         group = 'emc/dialog/panel'
      edje.Edje.__init__(self, layout.evas, file = theme_file, group = group)
      self.signal_callback_add('emc,dialog,close', '', self._close_pressed)
      self.signal_callback_add('emc,dialog,hide,done', '',
                               (lambda a,s,d: self._delete_real()))
      self.signal_callback_add('emc,dialog,show,done', '',
                               (lambda a,s,d: None))

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
      self._user_data = user_data
      self._list = None
      self._scroller = None
      self._textentry = None
      self._buttons = []
      self.fman = EmcFocusManager2()

      # title
      if title is None:
         self.signal_emit('emc,dialog,title,hide', 'emc')
      else:
         self.part_text_set('emc.text.title', title)
         self.signal_emit('emc,dialog,title,show', 'emc')

      # vbox
      self._vbox = Box(win)
      self._vbox.horizontal_set(False)
      self._vbox.size_hint_align_set(evas.EVAS_HINT_FILL, 0.0)
      self._vbox.size_hint_weight_set(evas.EVAS_HINT_EXPAND, 0.0)
      self._vbox.show()
      self.part_swallow('emc.swallow.content', self._vbox)

      # if both text and content given then put them side by side
      if text and content:
         hbox = Box(win)
         hbox.horizontal_set(True)
         hbox.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
         hbox.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         hbox.show()
         self._vbox.pack_end(hbox)
      
      # text entry
      if text is not None:
         self._textentry = Entry(win)
         self._textentry.style_set('dialog')
         self._textentry.editable_set(False)
         self._textentry.context_menu_disabled_set(True)
         self._textentry.entry_set(text)
         self._textentry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         self._textentry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
         self._textentry.show()
         
         self._scroller = Scroller(win)
         self._scroller.style_set('dialog')
         self._scroller.focus_allow_set(False)
         self._scroller.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         self._scroller.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
         self._scroller.content_set(self._textentry)
         self._scroller.show()

         if content:
            hbox.pack_end(self._scroller)
         else:
            self._vbox.pack_end(self._scroller)

      # user content
      if content is not None:
         frame = Frame(win)
         frame.style_set('pad_small')
         frame.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         frame.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
         frame.content_set(content)
         frame.show()
         if text is not None:
            hbox.pack_start(frame)
         else:
            self._vbox.pack_end(frame)

      # automatic list
      if style == 'list':
         self._list = List(win)
         self._list.focus_allow_set(False)
         self._list.style_set('dialog')
         self._list.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         self._list.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
         self._list.callback_activated_add(self._list_item_activated_cb)
         self._list.show()
         self._vbox.pack_end(self._list)

      # spinner
      if spinner:
         self._spinner = Progressbar(win)
         self._spinner.style_set('wheel')
         self._spinner.pulse(True)
         self._spinner.show()
         self._vbox.pack_end(self._spinner)

      # set minimal styles + automatic title
      if style in EmcDialog.minimal_styles:
         self.signal_emit('emc,dialog,%s,set' % (style), 'emc')
         if title is None:
            self.part_text_set('emc.text.title', style)
            self.signal_emit('emc,dialog,title,show', 'emc')

      # buttons
      if style in ('info', 'error', 'warning'):
         self.button_add('Ok', (lambda btn: self.delete()))

      if style in ('yesno'):
         if self._canc_cb:
            self.button_add('No', (lambda btn: self._canc_cb(self)))
         else:
            self.button_add('No', (lambda btn: self.delete()))

         if self._done_cb:
            self.button_add('Yes', (lambda btn: self._done_cb(self)))
         else:
            self.button_add('Yes', (lambda btn: self.delete()))

      # Do we want the cancel button? we have the red-round-close...
      # if style in ('cancel'):
         # if canc_cb:
            # self.button_add('Cancel', (lambda btn: self._canc_cb(self)))
         # else:
            # self.button_add('Cancel', (lambda btn: self.delete()))

      # listen for input events
      input_events.listener_add(self._name, self._input_event_cb)

      # show
      self.show()
      self.signal_emit('emc,dialog,show', 'emc')

   def activate(self):
      print('DEPRECATED EmcDialog.activate()')

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

   def data_get(self):
      return self._user_data

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
      if self._textentry:
         self._textentry.entry_set(text)

   def text_get(self):
      return self._textentry.entry_get()

   def text_append(self, text):
      self._textentry.entry_set(self._textentry.entry_get() + text)

   def list_item_append(self, label, icon = None, end = None, *args, **kwargs):
      if self._list:
         if icon: icon = load_icon(icon)
         if end: end = load_icon(end)
         it = self._list.item_append(label, icon, end, None, *args, **kwargs)
         if not self._list.selected_item_get():
            it.selected = True
         return it

   def list_item_selected_get(self):
      if self._list:
         return self._list.selected_item_get()

   def _list_item_activated_cb(self, li, it):
      if self._done_cb:
         args, kwargs = it.data
         self._done_cb(self, *args, **kwargs)
      else:
         self.delete()
   
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

   def scroll_by(self, sx=0, sy=0, animated=True, restart=False):
      if self._scroller:
         x, y, w, h = old_region = self._scroller.region
         if animated:
            self._scroller.region_bring_in(x + sx, y + sy, w, h)
         else:
            self._scroller.region_show(x + sx, y + sy, w, h)

         if restart and old_region == self._scroller.region:
            self._scroller.region_show(0, 0, w, h)

   def autoscroll_enable(self):
      self._autoscroll_amount = 0.0
      ecore.Animator(self._autoscroll_animator_cb)

   def _autoscroll_animator_cb(self):
      if self.is_deleted():
         return ecore.ECORE_CALLBACK_CANCEL

      self._autoscroll_amount += ecore.animator_frametime_get() * 30.0
      if self._autoscroll_amount >= 1.0:
         self.scroll_by(0, int(self._autoscroll_amount), False, True)
         self._autoscroll_amount = 0.0

      return ecore.ECORE_CALLBACK_RENEW

   def _input_event_cb(self, event):

      if not self.visible:
         return input_events.EVENT_CONTINUE

      if event in ['BACK', 'EXIT']:
         if self._canc_cb:
            self._canc_cb(self)
         else:
            self.delete()
         return input_events.EVENT_BLOCK

      # if content is List or Genlist then automanage the events
      if self._list or (self._content and type(self._content) in (List, Genlist)):
         list = self._list or self._content
         item = list.selected_item_get()
         if not item:
            item = list.items_get()[0]

         horiz = False
         if type(self._content) is List:
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

      # try to scroll the text entry
      if self._scroller:
         if event == 'UP':
            self.scroll_by(0, -100)
         if event == 'DOWN':
            self.scroll_by(0, +100)

      # focus between buttons
      if self._buttons:
         if event == 'LEFT':
            self.fman.focus_move('l')
         if event == 'RIGHT':
            self.fman.focus_move('r')
   
      if event == 'OK':
         if self._buttons:
            self._cb_buttons(self.fman.focused_get())
         elif self._done_cb:
            if self._list:
               it = self._list.selected_item
               self._list_item_activated_cb(self._list, it)
            else:
               self._done_cb(self)
         else:
            self.delete()

      if event in ('LEFT', 'RIGHT', 'UP', 'DOWN', 'OK'):
         return input_events.EVENT_BLOCK
      else:
         return input_events.EVENT_CONTINUE

################################################################################
class EmcNotify(edje.Edje):
   """ TODO doc this"""

   def __init__(self, text, icon = 'icon/star', hidein = 5.0):
      group = 'emc/notify/default'
      edje.Edje.__init__(self, layout.evas, file = theme_file, group = group)
      self.part_text_set('emc.text.caption', text)
      self._icon = load_image(icon)
      self.part_swallow('emc.swallow.icon', self._icon)
      box_append('notify.box.stack', self)
      if hidein > 0.0:
         self.timer = ecore.Timer(hidein, self.hide_timer_cb)
      else:
         self.timer = None
      self.show()

   def hide_timer_cb(self):
      box_remove('notify.box.stack', self)
      self._icon.delete()
      self.delete()
      return ecore.ECORE_CALLBACK_CANCEL

   def close(self):
      if self.timer:
         self.timer.delete()
      self.hide_timer_cb()

   def text_set(self, text):
      self.part_text_set('emc.text.caption', text)
   
   def icon_set(self, icon):
      self.part_text_set('emc.text.caption', text)
      # TODO need to del the old image ??
      self._icon = load_image(icon)

###############################################################################
class EmcSourceSelector(EmcDialog):
   """ TODO doc this
   """

   def __init__(self, title = 'Source Selector', done_cb=None, cb_data=None):
      self._selected_cb = done_cb
      self._selected_cb_data = cb_data
      self._glist = Genlist(win)
      self._glist.style_set('dialog')
      self._glist.homogeneous_set(True)
      self._glist.select_mode_set(elementary.ELM_OBJECT_SELECT_MODE_ALWAYS)
      self._glist.focus_allow_set(False)
      self._glist.callback_clicked_double_add(self._cb_item_selected)
      self._glist_itc = GenlistItemClass(item_style = 'default',
                                 text_get_func = self._genlist_folder_label_get,
                                 content_get_func = self._genlist_folder_icon_get)
      self._glist_itc_back = GenlistItemClass(item_style = 'default',
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
         return load_icon('icon/folder')
      return None
   
   def _genlist_back_label_get(self, obj, part, item_data):
      return 'back'

   def _genlist_back_icon_get(self, obj, part, data):
      if part == 'elm.swallow.icon':
         return load_icon('icon/back')
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
                title = None, text = None, user_data = None):
      """ TODO doc this """

      self.accept_cb = accept_cb
      self.dismiss_cb = dismiss_cb
      self.user_data = user_data
      self.current_button = None

      # table
      tb = Table(win)
      tb.homogeneous_set(True)
      tb.show()

      # set dialog title
      self.part_text_set('emc.text.title', title or 'Insert text')

      # entry
      self.entry = Entry(win) # TODO use scrolled_entry instead
      self.entry.style_set('vkeyboard')
      self.entry.single_line_set(True)
      self.entry.context_menu_disabled_set(True)
      # self.entry.editable_set(False)
      # self.entry.focus_allow_set(True)
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
      for i, c in enumerate(['u', 'v', 'w', 'x', 'y', 'z', '.', ',', ':', ';']):
         self._pack_btn(tb, i, 4, 1, 1, c, cb = self._default_btn_cb)

      self._pack_btn(tb, 0, 5, 3, 1, 'UPPERCASE', cb = self._uppercase_cb)
      self._pack_btn(tb, 3, 5, 4, 1, 'SPACE', cb = self._space_cb)
      self._pack_btn(tb, 7, 5, 3, 1, 'ERASE', cb = self._erase_cb)

      self._pack_btn(tb, 0, 6, 4, 1, 'Dismiss', 'icon/cancel', self._dismiss_cb)
      self._pack_btn(tb, 4, 6, 1, 1, None, 'icon/arrowL',
                                     lambda b: self.entry.cursor_prev())
      self._pack_btn(tb, 5, 6, 1, 1, None, 'icon/arrowR',
                                     lambda b: self.entry.cursor_next())
      self._pack_btn(tb, 6, 6, 4, 1, 'Accept',  'icon/ok',     self._accept_cb)

      # init the parent EmcDialog class
      EmcDialog.__init__(self, title = title, style = 'minimal', content = tb)

       # catch input events
      input_events.listener_add('vkbd', self.input_event_cb)

      # give focus to the entry, to show the cursor
      self.entry.focus_set(True)

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
         if self.user_data is not None:
            self.accept_cb(self, self.entry.entry_get(), self.user_data)
         else:
            self.accept_cb(self, self.entry.entry_get())
      self.delete()

   def _default_btn_cb(self, button):
      self.entry.entry_insert(button.text)

   def _erase_cb(self, button):
      pos = self.entry.cursor_pos_get()
      if pos > 0:
         text = self.entry.text
         self.entry.text = text[:pos-1] + text[pos:]
         self.entry.cursor_pos_set(pos - 1)

   def _space_cb(self, button):
      self.entry.entry_insert(' ')

   def _uppercase_cb(self, button):
      for btn in self.efm.all_get():
         c = btn.text_get()
         if c and len(c) == 1 and c.isalpha():
            if c.islower():
               btn.text = c.upper()
               button.text = 'LOWERCASE'
            else:
               btn.text = c.lower()
               button.text = 'UPPERCASE'
         elif c and len(c) == 1:
            if   c == '.':  btn.text = '/'
            elif c == '/':  btn.text = '.'
            elif c == ',':  btn.text = '@'
            elif c == '@':  btn.text = ','
            elif c == ':':  btn.text = '-'
            elif c == '-':  btn.text = ':'
            elif c == ';':  btn.text = '_'
            elif c == '_':  btn.text = ';'

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
  
