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

import os, time, re

try:
   from efl import evas, ecore, edje, elementary
   from efl.elementary.window import Window
   from efl.elementary.layout import Layout
   from efl.elementary.icon import Icon
   from efl.elementary.image import Image
except:
   import evas, ecore, edje, elementary
   import ecore.x #used only to show/hide the cursor
   from elementary import Window, Layout, Icon, Image

import utils, ini, gui, events, input_events
from widgets import EmcButton, EmcDialog, EmcNotify, EmcRemoteImage


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


DEBUG = True
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
   if type(icon) in (Icon, Image, EmcRemoteImage):
      return icon
   ic = Icon(gui.win)
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

   im = Image(gui.win)

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
      backdrop_im = Image(gui.win)
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
