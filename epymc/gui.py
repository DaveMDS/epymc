#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2015 Davide Andreoli <dave@gurumeditation.it>
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
from datetime import datetime

from efl import evas
from efl import ecore
from efl import ecore_input
from efl import edje
from efl import elementary as elm
from efl.elementary import Window, ELM_WIN_BASIC, Layout, Icon, Image, Button, \
   Menu, Progressbar, Box, Entry, Scroller, Scrollable, Frame, List, Table, \
   Genlist, GenlistItemClass, ELM_OBJECT_SELECT_MODE_ALWAYS, ELM_LIST_COMPRESS, \
   Gengrid, Slideshow, SlideshowItemClass
from efl.elementary.theme import theme_overlay_add, theme_extension_add
from efl.elementary.configuration import scale_set as elm_scale_set
from efl.elementary.configuration import scale_get as elm_scale_get
from efl.elementary.configuration import Configuration as ElmConfig

from epymc import utils, ini, events, input_events
from epymc.thumbnailer import emc_thumbnailer


win = None
layout = None
theme_file = None

_backdrop_im1 = None
_backdrop_im2 = None
_backdrop_curr = None

_volume_hide_timer = None
_clock_update_timer = None
_clock_time_str = ''
_clock_date_str = ''

_theme_generation = '6'

EXPAND_BOTH = evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND
EXPAND_HORIZ = evas.EVAS_HINT_EXPAND, 0.0
FILL_BOTH = evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL
FILL_HORIZ = evas.EVAS_HINT_FILL, 0.5

MESSAGE_CLOCK_TIME = 12
MESSAGE_CLOCK_DATE = 13


def LOG(msg):
   print('GUI: %s' % msg)

def DBG(msg):
   # print('GUI: %s' % msg)
   pass


def init():
   """ return: False=failed True=ok """
   global win, layout, theme_file
   global _backdrop_im1, _backdrop_im2, _backdrop_curr
   global _clock_update_timer

   # get config values, setting defaults if needed
   theme_name = ini.get('general', 'theme', default_value='default')
   # evas_engine = ini.get('general', 'evas_engine', default_value='software_x11')
   evas_accelerated = ini.get('general', 'evas_accelerated', default_value='True')
   fps = ini.get('general', 'fps', default_value=30)
   scale = ini.get('general', 'scale', default_value=1.0)
   fullscreen = ini.get('general', 'fullscreen', False)
   ini.get('general', 'time_format', '%H:%M')
   ini.get('general', 'date_format', '%A %d %B')

   # connect ecore_input key event
   ecore_input.on_key_down_add(_on_key_down)

   # elementary configuration
   conf = ElmConfig()
   conf.window_auto_focus_enable = False
   conf.window_auto_focus_animate = False
   conf.focus_highlight_enabled = True
   conf.focus_highlight_animate = False
   conf.focus_autoscroll_mode = elm.ELM_FOCUS_AUTOSCROLL_MODE_NONE #ELM_FOCUS_AUTOSCROLL_MODE_SHOW or ELM_FOCUS_AUTOSCROLL_MODE_BRING_IN
   conf.item_select_on_focus_disabled = False
   conf.focus_highlight_clip_disabled = False
   # conf.softcursor_mode = ELM_SOFTCURSOR_MODE_ON
   if evas_accelerated == 'True':
      conf.accel_preference = 'accel'
      LOG('Request an hardware accelerated evas engine')
   
   # search the theme file, or use the default one
   if os.path.isabs(theme_name) and os.path.exists(theme_name):
      theme_file = theme_name
   else:
      if not theme_name.endswith('.edj'):
         theme_name += '.edj'
      theme_file = utils.get_resource_file('themes', theme_name, 'default.edj')
      if theme_file is None:
         LOG('cannot find a working theme file, exiting...')
         return False

   # check the theme generation
   gen = edje.file_data_get(theme_file, 'theme.generation')
   if gen != _theme_generation:
      LOG('Theme "{}" not in sync with actual code base.\n'
          'Needed generation: {} - theme: {} .. aborting'.format(
            theme_file, _theme_generation, gen))
      return False

   # custom elementary theme
   set_theme_file(theme_file)

   # create the elm window
   win = Window('epymc', ELM_WIN_BASIC, title=_('Emotion Media Center'),
                focus_allow=False)
   win.callback_delete_request_add(lambda w: ask_to_exit())
   if fullscreen == 'True':
      win.fullscreen_set(1)

   # main layout (main theme)
   layout = Layout(win, file=(theme_file, 'emc/main/layout'), focus_allow=False,
                   size_hint_expand=EXPAND_BOTH)
   win.resize_object_add(layout)
   layout.show()

   # clock update timer
   _clock_update_timer = ecore.Timer(1.0, clock_update)

   # right click for BACK
   layout.edje.signal_callback_add("mouse,up,3", "*",
                              (lambda o,e,s: input_events.event_emit('BACK')))

   # two Image objects for the backdrop
   _backdrop_im1 = Image(win, fill_outside=True)
   _backdrop_im2 = Image(win, fill_outside=True)
   swallow_set('bg.swallow.backdrop1', _backdrop_im1)
   swallow_set('bg.swallow.backdrop2', _backdrop_im2)
   _backdrop_curr = _backdrop_im2

   win.show()
   win.scale_set(float(scale))

   # listen to events and input_events
   input_events.listener_add('gui', _input_event_cb)
   events.listener_add('gui', _event_cb)

   # set efl frames per second
   fps_set(fps)

   return True

def shutdown():
   events.listener_del('gui')
   input_events.listener_del('gui')
   _clock_update_timer.delete()


### Various externally accessible functions ###

def get_theme_info(theme):
   D = {}
   D['name'] = edje.file_data_get(theme, 'theme.name') or _('Unknown')
   D['version'] = edje.file_data_get(theme, 'theme.version') or ''
   D['author'] = edje.file_data_get(theme, 'theme.author') or _('Unknown')
   D['info'] = edje.file_data_get(theme, 'theme.info') or _('Unknown')
   return D

def set_theme_file(path):
   global theme_file

   LOG('Using theme: ' + path)
   theme_overlay_add(path) # TODO REMOVE ME!!! it's here for buttons, and others
   theme_extension_add(path)
   theme_file = path
   utils.in_use_theme_file_set(theme_file) # ... a bit hackish :(

def load_icon(icon):
   """
   @icon can be a full path (if start with a '/' or
         can be a theme icon (ex: icon/folder).
   see icons.edc for all the existing icon
   """
   if not icon:
      return None
   if type(icon) in (Icon, Image, EmcImage):
      return icon
   ic = Icon(win)
   if icon[0] == '/':
      try:
         ic.file_set(icon)
      except: pass
   else:
      try:
         ic.file_set(theme_file, icon)
      except: pass

   ic.size_hint_aspect_set(evas.EVAS_ASPECT_CONTROL_VERTICAL, 1, 1)
   return ic

def load_image(name, path = None):
   """
   @name include the ext but not the path (es 'my_image.png')
   @name can also be a full_path or a complete url
   @path is searched if the image is not found in the theme
   @return ElmImage
   @example: load_image('my_image.png', os.path.dirname(__file__))

   DEPRECATED: use EmcImage instead !!!

   """
   DBG('Requested image: ' + str(name))
   DBG('Extra path: ' + str(path))

   # remote urls
   if name.startswith(('http://', 'https://')):
      return EmcImage(name)

   im = Image(win)

   # if it's a full path just load it
   if os.path.exists(name):
      DBG('Found image:' + name)
      im.file_set(name)
      return im

   # try in main theme file (as group: image/$name)
   if edje.file_group_exists(theme_file, 'image/' + name):
      DBG('Found image in theme group: image/' + name)
      im.file_set(theme_file, 'image/' + name)
      return im

   # try in main theme file (as group: $name) (thus you can load 'icon/*')
   if edje.file_group_exists(theme_file, name):
      DBG('Found image in theme group: ' + name)
      im.file_set(theme_file, name)
      return im

   # TODO search in some system dirs
   
   # try in caller path
   if path:
      full = os.path.join(path, name)
      if os.path.exists(full):
         DBG('Found image in extra path: image/' + name)
         im.file_set(full)
         return im

   LOG('Cannot load image: ' + str(name))
   return im

def ask_to_exit():
   text = '<center>' + credits.replace('\n', '<br>') + '</center>'
   d = EmcDialog(title=_('credits'), style='minimal', text=text)
   d.button_add(_('Cancel'), selected_cb=lambda b: d.delete())
   # d.button_add(_('Suspend'), selected_cb=None) # TODO
   # d.button_add(_('Shutdown'), selected_cb=None) # TODO
   d.button_add(_('Exit'), selected_cb=lambda b: exit_now())
   d.autoscroll_enable(3.0, 0.0)

def exit_now():
   elm.exit()

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

def volume_set(value):
   slider_val_set('volume.slider:dragable1', value)

def scale_set(scale):
   elm_scale_set(scale)

def scale_get():
   return elm_scale_get()

def scale_bigger():
   scale_set(scale_get() + 0.1)

def scale_smaller():
   scale_set(scale_get() - 0.1)

def scale_reset():
   scale_set(1.0)

def background_set(image):
   global _backdrop_curr

   if image == _backdrop_curr.file[0]:
      return

   if _backdrop_curr == _backdrop_im1:
      _backdrop_curr = _backdrop_im2
      signal = 'backdrop,show,2'
   else:
      _backdrop_curr = _backdrop_im1
      signal = 'backdrop,show,1'

   try:
      _backdrop_curr.file_set(image)
      signal_emit(signal)
   except: pass

def fps_set(fps):
   ecore.animator_frametime_set(1.0 / float(fps))

def fullscreen_get():
   return win.fullscreen

def fullscreen_set(full):
   win.fullscreen = full

def fullscreen_toggle():
   win.fullscreen = not win.fullscreen

def win_raise():
   win.iconified = False
   win.raise_()
   win.activate()

def clock_update():
   global _clock_time_str, _clock_date_str

   dt = datetime.now()
   time_str = dt.strftime(ini.get('general', 'time_format'))
   date_str = dt.strftime(ini.get('general', 'date_format'))

   if time_str != _clock_time_str:
      layout.edje.message_send(MESSAGE_CLOCK_TIME, time_str)
      _clock_time_str = time_str

   if date_str != _clock_date_str:
      layout.edje.message_send(MESSAGE_CLOCK_DATE, date_str)
      _clock_date_str = date_str
   
   return ecore.ECORE_CALLBACK_RENEW

### audio info/controls notify
_audio_notify = None

def audio_controls_show(text=None, icon=None):
   global _audio_notify
   
   if _audio_notify is None:
      _audio_notify = EmcNotify('', hidein=0, icon='icon/music')

   if text or icon:
       audio_controls_set(text, icon)

def audio_controls_hide():
   global _audio_notify
   
   if _audio_notify:
      _audio_notify.close()
      _audio_notify = None

def audio_controls_set(text=None, icon=None):
   if _audio_notify is None:
      return
   if text: _audio_notify.text_set(text)
   if icon: _audio_notify.icon_set(icon)


### Simple edje abstraction ###
def part_get(name):
   return layout.edje_get().part_external_object_get(name)

def signal_emit(sig, src='emc'):
   layout.signal_emit(sig, src)

def signal_cb_add(emission, source, cb):
   layout.signal_callback_add(emission, source, cb)

def signal_cb_del(emission, source, cb):
   layout.signal_callback_del(emission, source, cb)

def text_set(part, text):
   layout.text_set(part, text)

def swallow_set(part, obj, delete_old=True):
   if delete_old is True:
      layout.content_set(part, obj)
      return None
   else:
      ret = layout.content_unset(part)
      layout.content_set(part, obj)
      return ret

def slider_val_set(part, value):
   layout.edje_get().part_drag_value_set(part, value, value)

def slider_val_get(part):
   return layout.edje_get().part_drag_value_get(part)

def box_append(part, obj):
   layout.box_append(part, obj)

def box_prepend(part, obj):
   layout.box_prepend(part, obj)

def box_remove(part, obj):
   layout.box_remove(part, obj)

def box_remove_all(part, clear=True):
   layout.box_remove_all(part, clear)


### Internal functions ###

# This is a bit hackish, will be used by the keyb module.
# The reason is that the ecore_input event must be connected BEFORE the
# win is created, and at that point the keyb module is not yet loaded.
# So we need to connect here and pass the event to the key_down_func (that
# is setted by the keyb module)
key_down_func = None

def _on_key_down(event):
   if isinstance(win.focused_object, elm.Entry):
      return ecore.ECORE_CALLBACK_PASS_ON
   if key_down_func:
      return key_down_func(event)
   return ecore.ECORE_CALLBACK_DONE
# hack end


focus_directions = {
   'UP':    elm.ELM_FOCUS_UP,
   'DOWN':  elm.ELM_FOCUS_DOWN,
   'LEFT':  elm.ELM_FOCUS_LEFT,
   'RIGHT': elm.ELM_FOCUS_RIGHT,
}

def focus_move(direction, root_obj=None):
   """ TODOC """

   if root_obj is None:
      root_obj = win
   focused = root_obj.focused_object

   # move between List items...
   if isinstance(focused, List) and focused.focus_allow:
      item = focused.focused_item
      to_item = None
      horiz = focused.horizontal
      if (horiz and direction == 'RIGHT') or (not horiz and direction == 'DOWN'):
         to_item = item.next
      elif (horiz and direction == 'LEFT') or (not horiz and direction == 'UP'):
         to_item = item.prev
      if to_item:
         to_item.selected = True
         to_item.focus = True
         to_item.bring_in()
         return True

   # move between Genlist items...
   elif isinstance(focused, Genlist) and focused.focus_allow:
      item = focused.focused_item or focused.selected_item
      to_item = None
      if direction == 'DOWN':
         to_item = item.next
         while to_item and to_item.type == elm.ELM_GENLIST_ITEM_GROUP:
            to_item = to_item.next
      elif direction == 'UP':
         to_item = item.prev
         while to_item and to_item.type == elm.ELM_GENLIST_ITEM_GROUP:
            to_item = to_item.prev
      if to_item:
         to_item.selected = True
         to_item.focus = True
         to_item.bring_in(elm.ELM_GENLIST_ITEM_SCROLLTO_MIDDLE)
         return True

   # move between Gengrid items...
   elif isinstance(focused, Gengrid) and focused.focus_allow:
      item = focused.focused_item or focused.selected_item
      x1, y1 = item.pos
      to_item = None

      if direction in ('LEFT', 'RIGHT'):
         to_item = item.next if direction == 'RIGHT' else item.prev
         if to_item:
            x2, y2 = to_item.pos
            if y1 != y2:
               to_item = None

      elif direction == 'DOWN':
         to_item = item
         try:
            while True:
               to_item = to_item.next
               x2, y2 = to_item.pos
               # skip items on the same row of the start one
               if y2 == y1:
                  continue
               # skip group items
               if to_item.disabled:
                  continue
               # search the first item on the same col (or on the left)
               if x2 == x1 or to_item.next.pos[1] > y2:
                  break
         except:
            if to_item != focused.last_item:
               to_item = None
         
      else: # UP
         to_item = item
         try:
            while True:
               to_item = to_item.prev
               x2, y2 = to_item.pos
               # skip items on the same row of the start one
               if y2 == y1:
                  continue
               # skip group items
               if to_item.disabled:
                  continue
               # search the first item on the same col (or on the left)
               if x2 <= x1:
                  break
         except:
            to_item = None
         

      if to_item:
         to_item.selected = True
         to_item.focus = True
         to_item.bring_in(elm.ELM_GENLIST_ITEM_SCROLLTO_MIDDLE)
         return True

   # or just let elm move the focus between objects
   root_obj.focus_next(focus_directions[direction])

   # workaroud for a bug in gengrid that give focus to the grid but not to an item
   new_focused = win.focused_object
   if isinstance(new_focused, (Gengrid, Genlist)) and new_focused.focused_item is None:
      new_focused.selected_item.focus = True

   return False

def _input_event_cb(event):
   focused = win.focused_object

   if event in focus_directions:
      focus_move(event)

   elif event == 'OK' and isinstance(focused, EmcButton):
      focused.activate()

   elif event == 'TOGGLE_FULLSCREEN':
      fullscreen_toggle()
   elif event == 'SCALE_BIGGER':
      scale_bigger()
   elif event == 'SCALE_SMALLER':
      scale_smaller()
   elif event == 'SCALE_RESET':
      scale_reset()
   else:
      return input_events.EVENT_CONTINUE

   return input_events.EVENT_BLOCK

def _event_cb(event):
   if event == 'VOLUME_CHANGED':
      volume_show(hidein = 3)


credits = """







<info>code</>
DAVIDE ANDREOLI

<info>design</>
DAVIDE ANDREOLI

<info>python efl team</>
BORIS FAURE
BRUNO DILLY
DAVIDE ANDREOLI
FABIANO FIDÊNCIO
GUSTAVO SVERZUT BARBIERI
JOOST ALBERS
KAI HUUHKO
SIMON BUSCH
TIAGO FALCÃO

<info>online sources</>
themoviedb.org
opensubtitles.org
progettoemma.net
freeroms.com
youtube.com
vimeo.com
zapiks.com

<info>efl team</>
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


<info>author special thanks</>
SARA
TEODORO
MONOPOLIO DI STATO


<info>license</>
Copyright © 2010-2015 Davide Andreoli
dave@gurumeditation.it

EpyMC is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

EpyMC is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with EpyMC. If not, see http://www.gnu.org/licenses/
"""


################################################################################
class EmcButton(Button):
   """ A simple wrapper around the elm Button class """

   def __init__(self, label=None, icon=None, cb=None, cb_data=None, **kargs):
      self._cb = cb
      self._cb_data = cb_data
      Button.__init__(self, layout, style='emc', **kargs)
      self.callback_clicked_add(self.activate)
      if label: self.text_set(label)
      if icon: self.icon_set(icon)
      self.show()

   def icon_set(self, icon):
      self.content_set(load_icon(icon))

   def activate(self, obj=None):
      if obj is None:
         self.signal_emit("elm,anim,activate", "elm")
      if callable(self._cb):
         if self._cb_data is not None:
            self._cb(self, self._cb_data)
         else:
            self._cb(self)

################################################################################
class EmcMenu(Menu):
   """ TODO doc this """

   def __init__(self, relto=None, close_on=()):
      self.close_on = close_on
      Menu.__init__(self, layout, style='emc', focus_allow=False)
      if relto:
         # TODO better pos calc
         x, y, w, h = relto.geometry
         self.move(x, y + h)
      input_events.listener_add("EmcMenu", self._input_event_cb)
      self.callback_clicked_add(self._dismiss_cb)
      self.show()

   def item_add(self, parent=None, label=None, icon=None, callback=None, *args, **kwargs):
      item = Menu.item_add(self, parent, label, icon, self._item_selected_cb,
                           callback, *args, **kwargs)
      item.data['_user_cb_data_'] = (callback, args, kwargs)
      if self.selected_item is None:
         item.selected = True
      return item

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
      item = self.selected_item
      if event == 'UP':
         if event in self.close_on and item == self.first_item:
            self.close()
            return input_events.EVENT_BLOCK
         if not item or not item.prev:
            return input_events.EVENT_BLOCK
         while item.prev and (item.prev.is_separator or item.prev.disabled):
            item = item.prev
         if item and item.prev:
            item.prev.selected = True
         return input_events.EVENT_BLOCK

      elif event == 'DOWN':
         if event in self.close_on and item == self.last_item:
            self.close()
         if not item or not item.next:
            return input_events.EVENT_BLOCK
         while item.next and (item.next.is_separator or item.next.disabled):
            item = item.next
         if item and item.next:
            item.next.selected = True
         return input_events.EVENT_BLOCK

      elif event == 'OK':
         cb, args, kwargs = self.selected_item_get().data['_user_cb_data_']
         if callable(cb):
            cb(self, item, *args, **kwargs)
         self.close()
         return input_events.EVENT_BLOCK

      elif event == 'BACK' or event == 'EXIT':
         self.close()
         return input_events.EVENT_BLOCK

      elif event in ('LEFT', 'RIGHT'):
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

################################################################################
class EmcImage(Image):
   """ An image object with support for remote url, with optional
       saving of the downloaded image to a local destination and a simple
       cache-to-file mechanism to avoid re-downloading the image again.

      Params:
         url: The url to load the image from, can be one of:
               * a local file fullpath
               * a real remote url
               * a tuple containing (url, dest) (deprecated method ??)
               * 'icon/*' to load an icon (aspect 1:1) from the theme
               * 'image/*' to load an image from the theme
               * 'special/style/text' to create a "special" image, supported
                 styles are: 'folder', 'bd', 'icon'
                 The text will be inserted in the image.
               * 'special/vthumb/video_url' to create a thumb of a video file
               * None to "unset" the image
         dest: Local path to save the image to. If the dest path already exists
               the image will not be downloaded, but directly loaded from dest.
               If dest is None the downloaded file will be saved in cache.
         icon: For the special style 'icon', you can here specify the icon
               to swallow inside the special image.
         label2: For the special style 'icon', you can here specify the
                 secondary label text.
   """

   def __init__(self, url=None, dest=None, icon=None, label2=None,
                      aspect_fixed=True, fill_outside=False, thumb=False):
      self._icon_obj = None
      self._thumb_request_id = None
      Image.__init__(self, layout, aspect_fixed=aspect_fixed,
                     fill_outside=fill_outside, size_hint_expand=EXPAND_BOTH,
                     size_hint_fill=FILL_BOTH)
      self.on_del_add(self._del_cb)
      if url is not None:
         self.url_set(url, dest, icon, label2, thumb)

   def url_set(self, url, dest=None, icon=None, label2=None, thumb=False):
      # None to "unset" the image
      if url is None:
         self.file_set(theme_file, 'emc/image/null')
         return

      # url can also include dest
      if isinstance(url, tuple):
         url, dest = url

      # a remote url ?
      if url.startswith(('http://', 'https://')):
         if dest is None:
            dest = self.cache_path_get(url)
         if os.path.exists(dest):
            self.file_set(dest)
         else:
            try:
               utils.download_url_async(url, dest,
                                        complete_cb=self._download_complete_cb)
               self.file_set(theme_file, 'emc/image/downloading')
            except:
               self.file_set(theme_file, 'emc/image/error')
         return

      # do we want to use/generate a thumbnail?
      if emc_thumbnailer is not None: # TODO remove this for release 
         if thumb and not url.startswith(('special/', 'icon/', 'image/')):
            ret = emc_thumbnailer.generate(url, self._thumb_complete_cb)
            if isinstance(ret, str): # thumb already exists (ret is thumb path)
               self.file_set(ret)
            elif isinstance(ret, int): # generation started (ret is req_id)
               self._thumb_request_id = ret
               self.file_set(theme_file, 'emc/image/thumbnailing')
            else: # failed ... this cannot really happend atm
               self.file_set(theme_file, 'emc/image/error')
            return

      # a local path ?
      if os.path.exists(url):
         self.file_set(url)
         if self.animated_available:
            self.animated = True
            self.animated_play = True
         return
      
      # an icon from the theme ?
      if url.startswith(('icon/', 'image/')):
         self.file_set(theme_file, url)
         return

      # a video thumbnail ?
      if url.startswith('special/vthumb/'):
         if emc_thumbnailer is not None: # TODO remove this for release 
            ret = emc_thumbnailer.generate(url[15:], self._thumb_complete_cb,
                                           frame='vthumb')
            if isinstance(ret, str): # thumb already exists (ret is thumb path)
               self.file_set(ret)
            elif isinstance(ret, int): # generation started (ret is req_id)
               self._thumb_request_id = ret
               self.file_set(theme_file, 'emc/image/thumbnailing')
            else: # failed ... this cannot really happend atm
              self.file_set(theme_file, 'emc/image/error')
         return

      # a special image ?
      if url.startswith('special/'):
         _, style, text = url.split('/', maxsplit=2)
         self.file_set(theme_file,  'emc/image/' + style)
         obj = self.object
         obj.part_text_set('emc.text', text)
         if icon:
            self._icon_obj = EmcImage(icon)
            obj.part_swallow('emc.icon', self._icon_obj)
         if label2:
            obj.part_text_set('emc.text2', label2)
         return

   def cache_path_get(self, url):
      fname =  utils.md5(url) + '.jpg' # TODO fix extension !
      return os.path.join(utils.user_cache_dir, 'remotes', fname[:2], fname)

   def _thumb_complete_cb(self, status, file, thumb):
      if self.is_deleted(): return
      self._thumb_request_id = None
      if status is True:
         self.file_set(thumb)
      else:
         self.file_set(theme_file, 'emc/image/error')
   
   def _download_complete_cb(self, dest, status):
      if self.is_deleted(): return
      if status == 200:
         self.file_set(dest)
      else:
         self.file_set(theme_file, 'emc/image/error')

   def _del_cb(self, obj):
      if self._icon_obj:
         self._icon_obj.delete()
         self._icon_obj = None

      # TODO abort download  ??

      if self._thumb_request_id is not None:
         emc_thumbnailer.cancel_request(self._thumb_request_id)
         self._thumb_request_id = None

################################################################################
class EmcDialog(Layout):
   """ TODO doc this
   style can be 'panel' or 'minimal'

   you can also apply special style that perform specific task:
      'info', 'error', 'warning', 'yesno', 'cancel', 'progress',
      'list', 'image_list_horiz', 'image_list_vert',
      'buffering'
   """

   minimal_styles = ['info', 'error', 'warning', 'yesno', 'cancel', 'progress']
   dialogs_counter = 0

   def __init__(self, title=None, text=None, content=None, spinner=False,
                style='panel', done_cb=None, canc_cb=None, user_data=None):

      # load the right edje object
      if style in EmcDialog.minimal_styles or style == 'minimal':
         group = 'emc/dialog/minimal'
      elif style == 'buffering':
         group = 'emc/dialog/buffering'
      else:
         group = 'emc/dialog/panel'
      Layout.__init__(self, layout, file=(theme_file, group), focus_allow=False,
                      size_hint_align=FILL_BOTH, size_hint_weight=EXPAND_BOTH)
      self.signal_callback_add('emc,dialog,close', '', self._close_pressed)
      self.signal_callback_add('emc,dialog,hide,done', '',
                               (lambda a,s,d: self._delete_real()))
      self.signal_callback_add('emc,dialog,show,done', '',
                               (lambda a,s,d: None))

      # put the dialog in the dialogs box of the main edje obj,
      # this way we only manage one edje and don't have stacking problems.
      # otherwise dialogs will stole the mouse events.
      box_append('dialogs.box.stack', self)

      EmcDialog.dialogs_counter += 1
      self._name = 'Dialog-' + str(EmcDialog.dialogs_counter)
      self._content = content
      self._done_cb = done_cb
      self._canc_cb = canc_cb
      self._user_data = user_data
      self._list = None
      self._textentry = None
      self._buttons = []

      # remember last focused obj (under the dialog)
      self._last_focused = win.focused_object
      if self._last_focused:
         self._last_focused.focus = False

      # title
      if title is None:
         self.signal_emit('emc,dialog,title,hide', 'emc')
      else:
         self.part_text_set('emc.text.title', title)
         self.signal_emit('emc,dialog,title,show', 'emc')

      # vbox
      if style != 'buffering':
         self._vbox = Box(self, horizontal=False, size_hint_align=FILL_HORIZ,
                          size_hint_weight=EXPAND_HORIZ)
         self._vbox.show()
         self.content_set('emc.swallow.content', self._vbox)

      # if both text and content given then put them side by side
      if text and content:
         hbox = Box(self, horizontal=True, size_hint_align=FILL_BOTH,
                    size_hint_weight=EXPAND_BOTH)
         hbox.show()
         self._vbox.pack_end(hbox)

      # text entry
      if text is not None:
         self._textentry = EmcScrolledEntry(parent=self, text=text,
                                            size_hint_weight=EXPAND_BOTH,
                                            size_hint_align=FILL_BOTH)
         self._textentry.show()

         if content:
            hbox.pack_end(self._textentry)
         else:
            self._vbox.pack_end(self._textentry)

      # user content
      if content is not None:
         frame = Frame(self, style='pad_small', size_hint_align=FILL_BOTH,
                       size_hint_weight=EXPAND_BOTH, content=content)
         frame.show()
         if text is not None:
            hbox.pack_start(frame)
         else:
            self._vbox.pack_end(frame)

      # automatic list
      if style in ['list', 'image_list_horiz', 'image_list_vert']:
         self._list = List(self, focus_allow=False, size_hint_align=FILL_BOTH,
                           size_hint_weight=EXPAND_BOTH,
                           horizontal=True if style == 'image_list_horiz' else False,
                           style='dialog' if style == 'list' else 'image_list')
         self._list.callback_activated_add(self._list_item_activated_cb)
         self._list.show()
         self._vbox.pack_end(self._list)

      # spinner
      if spinner:
         self._spinner = Progressbar(self, style='wheel', pulse_mode=True)
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
         self.button_add(_('Ok'), lambda btn: self.delete())

      if style in ('yesno'):
         if self._canc_cb:
            self.button_add(_('No'), lambda btn: self._canc_cb(self))
         else:
            self.button_add(_('No'), lambda btn: self.delete())

         if self._done_cb:
            self.button_add(_('Yes'), lambda btn: self._done_cb(self))
         else:
            self.button_add(_('Yes'), lambda btn: self.delete())

      # Do we want the cancel button? we have the red-round-close...
      # if style in ('cancel'):
         # if canc_cb:
            # self.button_add('Cancel', lambda btn: self._canc_cb(self))
         # else:
            # self.button_add('Cancel', lambda btn: self.delete())

      # listen for input events (not for the buffering dialog)
      if style != 'buffering':
         input_events.listener_add(self._name, self._input_event_cb)

      # show
      self.show()
      self.signal_emit('emc,dialog,show', 'emc')

   def activate(self):
      print('DEPRECATED EmcDialog.activate()')

   def delete(self):
      input_events.listener_del(self._name)
      self.signal_emit('emc,dialog,hide', 'emc')
      if self._last_focused:
         self._last_focused.focus = True

   def _delete_real(self):
      if self._textentry:
         self._textentry.delete()
      for b in self._buttons:
         b.delete()
      content = self.content_unset('emc.swallow.content')
      if content:
         content.delete()
      box_remove('dialogs.box.stack', self)
      Layout.delete(self)
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

   def button_add(self, label, selected_cb=None, cb_data=None, icon=None):
      b = EmcButton(label, icon, selected_cb, cb_data)
      self.box_prepend('emc.box.buttons', b)
      self._buttons.append(b)
      if len(self._buttons) == 1:
         self.signal_emit('emc,dialog,buttons,show', 'emc')
         b.focus = True
      return b

   def buttons_clear(self):
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
         self._textentry.text_set(text)

   def text_get(self):
      return self._textentry.text_get()

   def text_append(self, text):
      self._textentry.text_set(self._textentry.text_get() + text)

   def list_item_append(self, label, icon=None, end=None, *args, **kwargs):
      if self._list:
         if icon: icon = load_icon(icon)
         if end: end = load_icon(end)
         it = self._list.item_append(label, icon, end, None)
         it.data['_user_item_data_'] = (args, kwargs)
         if not self._list.selected_item_get():
            it.selected = True
         return it

   def list_go(self):
      self._list.go()

   def list_clear(self):
      self._list.clear()

   def list_item_selected_get(self):
      if self._list:
         return self._list.selected_item_get()

   def _list_item_activated_cb(self, li, it):
      if self._done_cb:
         args, kwargs = it.data['_user_item_data_']
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
      self.edje.part_external_object_get('emc.dialog.progress').value_set(val)

   def autoscroll_enable(self, speed_scale=1.0, start_delay=3.0):
      self._textentry.autoscroll_start_delay = start_delay
      self._textentry.autoscroll_speed_scale = speed_scale
      self._textentry.autoscroll = True

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
         li = self._list or self._content
         item = li.selected_item
         if item:
            new_it = None
            horiz = li.horizontal if type(li) is List else False
            if (horiz and event == 'RIGHT') or (not horiz and event == 'DOWN'):
               new_it = item.next
            if (horiz and event == 'LEFT') or (not horiz and event == 'UP'):
               new_it = item.prev
            if new_it:
               new_it.selected = True
               new_it.bring_in()
               return input_events.EVENT_BLOCK

      # try to scroll the text entry
      if self._textentry:
         if event == 'UP':
            self._textentry.scroll_by(0, -100)
         if event == 'DOWN':
            self._textentry.scroll_by(0, +100)

      if event in focus_directions:
         focus_move(event, self)
         return input_events.EVENT_BLOCK

      if event == 'OK':
         if isinstance(self.focused_object, EmcButton):
            self.focused_object.activate()

         elif self._done_cb:
            if self._list:
               it = self._list.selected_item
               self._list_item_activated_cb(self._list, it)
            else:
               self._done_cb(self)

         else:
            self.delete()

         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

################################################################################
class EmcNotify(edje.Edje):
   """ TODO doc this"""

   def __init__(self, text, icon='icon/star', hidein=5.0, close_cb=None):
      self.timer = None
      self.close_cb = close_cb

      edje.Edje.__init__(self, layout.evas, file=theme_file,
                         group='emc/notify/default')
      self.part_text_set('emc.text.caption', text)
      self._icon = load_image(icon)
      self.part_swallow('emc.swallow.icon', self._icon)
      box_append('notify.box.stack', self)

      if hidein > 0.0:
         self.hidein(hidein)

      self.show()

   def hidein(self, hidein):
      if self.timer:
         self.timer.delete()
      self.timer = ecore.Timer(hidein, self._hide_timer_cb)

   def _hide_timer_cb(self):
      box_remove('notify.box.stack', self)
      self._icon.delete()
      self.delete()
      if callable(self.close_cb):
         self.close_cb()
      return ecore.ECORE_CALLBACK_CANCEL

   def close(self):
      if self.timer:
         self.timer.delete()
      self._hide_timer_cb()

   def text_set(self, text):
      self.part_text_set('emc.text.caption', text)

################################################################################
class EmcSlideshow(Slideshow):
   """ Fullscreen slideshow widget, with controls.

   Params:
      url: The folder to show. If it is a file than all the files in the
           parent folder will be show, starting from the given file.
   """

   def __init__(self, url, delay=4, show_controls=False):
      # private stuff
      self._itc = SlideshowItemClass(self._item_get_func, self._item_del_func)
      self._timeout = delay
      self._first_file = None
      self._controls_visible = False
      self._show_controls_on_start = show_controls
      self._num_images = 0
      self._folder = utils.url2path(url)
      if not os.path.isdir(self._folder):
         self._folder, self._first_file = os.path.split(self._folder)

      # swallow our layout in the main layout
      self._ly = Layout(layout, file=(theme_file, 'emc/slideshow/default'))
      swallow_set('slideshow.swallow', self._ly)

      # swallow the slideshow widget in our layout
      Slideshow.__init__(self, self._ly, loop=True, transition='fade',
                         focus_allow=False)
      self.callback_changed_add(self._photo_changed_cb)
      self._ly.content_set('slideshow.swallow', self)
      self._ly.signal_callback_add('emc,show,done', '', self._show_done_signal_cb)
      self._ly.signal_callback_add('emc,hide,done', '', self._hide_done_signal_cb)
      self._ly.signal_callback_add('mouse,down,1', 'slideshow.swallow', self._click_signal_cb)
      self._ly.signal_emit('show', 'emc')

      # fill the controls bar with buttons
      bt = EmcButton(icon='icon/prev', cb=lambda b: self.previous())
      self._ly.box_append('controls.btn_box', bt)

      bt = EmcButton(icon='icon/pause', cb=lambda b: self.pause_toggle())
      self._ly.box_append('controls.btn_box', bt)
      self._pause_btn = bt

      bt = EmcButton(icon='icon/next', cb=lambda b: self.next())
      self._ly.box_append('controls.btn_box', bt)

      # fill the slideshow widget
      self._populate()

      # listen to emc input events
      input_events.listener_add('EmcSlideShow', self._input_event_cb)

      # steal the focus
      self._pause_btn.focus = True

   def delete(self):
      self.pause()
      input_events.listener_del('EmcSlideShow')
      self._ly.signal_emit('hide', 'emc')
      self._ly.signal_emit('controls,hide', 'emc')

   def _delete_real(self):
      Slideshow.delete(self)
      self._ly.delete()

   def pause(self):
      self.timeout = 0
      self._pause_btn.icon_set('icon/play')

   def unpause(self):
      self.timeout = self._timeout
      self._pause_btn.icon_set('icon/pause')

   def pause_toggle(self):
      self.unpause() if self.timeout == 0 else self.pause()

   def controls_show(self):
      self._ly.signal_emit('controls,show', 'emc')
      self._controls_visible = True

   def controls_hide(self):
      self._ly.signal_emit('controls,hide', 'emc')
      self._controls_visible = False

   def controls_toggle(self):
      self.controls_hide() if self._controls_visible else self.controls_show()

   ## edje signal callbacks
   def _click_signal_cb(self, obj, signal, src):
      self.controls_toggle()

   def _show_done_signal_cb(self, obj, signal, src):
      self.unpause()
      if self._show_controls_on_start:
         self.controls_show()

   def _hide_done_signal_cb(self, obj, signal, src):
      self._delete_real()

   ## slideshow widget smart callbacks
   def _photo_changed_cb(self, obj, item):
      num, fname = item.data
      self._ly.text_set('controls.text',
                        _('Image {0} of {1}').format(num, self._num_images))

   ## internals
   def _populate(self):
      num = 1
      items = []
      for fname in utils.natural_sort(os.listdir(self._folder)):
         name, ext = os.path.splitext(fname)
         if fname[0] != '.' and ext.lower() in utils.supported_images:
            item_data = (num, fname)
            items.append(item_data)
            num += 1
      self._num_images = num

      for item_data in items:
         it = self.item_add(self._itc, item_data)
         if item_data[1] == self._first_file:
            it.show()

   ## slideshow items class
   def _item_get_func(self, obj, item_data):
      num, fname = item_data
      fullpath = os.path.join(self._folder, fname)
      img = Image(self, file=fullpath)
      return img

   def _item_del_func(self, obj, item_data):
      obj.delete()

   ## emc events
   def _input_event_cb(self, event):

      if self._controls_visible:
         if event in ('UP', 'DOWN', 'LEFT', 'RIGHT'):
            focus_move(event, self._ly)
            return input_events.EVENT_BLOCK

         elif event in ('EXIT', 'BACK'):
            self.controls_hide()
            return input_events.EVENT_BLOCK

      else:
         if event == 'RIGHT':
            self.next()
            return input_events.EVENT_BLOCK
         
         elif event == 'LEFT':
            self.previous()
            return input_events.EVENT_BLOCK

         elif event == 'OK':
            self.controls_show()
            return input_events.EVENT_BLOCK

         elif event in ('EXIT', 'BACK'):
            self.delete()
            return input_events.EVENT_BLOCK

      if event == 'TOGGLE_PAUSE':
         self.pause_toggle()
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

################################################################################
class EmcFolderSelector(EmcDialog):
   """
   Open a dialog that allow the user to choose a path on the filesystem.

   Args:
      title:
         The (optional) dialog title.
      done_cb:
         The function to call when the selection is over.
         Signature: cb(path, [cb_data])
      cb_data:
         Optional user-data to pass back in the done_cb function.
   """

   def __init__(self, title=_('Source Selector'), done_cb=None, cb_data=None):
      self._selected_cb = done_cb
      self._selected_cb_data = cb_data

      EmcDialog.__init__(self, title, style='list', done_cb=self._btn_browse_cb)
      b2 = self.button_add(_('Select'), self._btn_select_cb)
      b1 = self.button_add(_('Browse'), self._btn_browse_cb)
      b1.focus = True

      self.populate(os.getenv('HOME'))

   def populate(self, folder):
      parent_folder = os.path.normpath(os.path.join(folder, '..'))
      if folder != parent_folder:
         it = self.list_item_append(_('Parent folder'), 'icon/arrowU')
         it.data['fullpath'] = parent_folder
      for fname in utils.natural_sort(os.listdir(folder)):
         fullpath = os.path.join(folder, fname)
         if fname[0] != '.' and os.path.isdir(fullpath):
            it = self.list_item_append(fname, 'icon/folder')
            it.data['fullpath'] = fullpath
      self.list_go()

   def _btn_browse_cb(self, btn):
      path = self.list_item_selected_get().data['fullpath']
      self.list_clear()
      self.populate(path)

   def _btn_select_cb(self, btn):
      path = self.list_item_selected_get().data['fullpath']
      if path and callable(self._selected_cb):
         if self._selected_cb_data:
            self._selected_cb('file://' + path, self._selected_cb_data)
         else:
            self._selected_cb('file://' + path)

      self.delete()

################################################################################
class EmcSourcesManager(EmcDialog):
   """ Open a dialog that allow the user to manage (add/remove) source
   folders. The manager automatically get the folders list from config file,
   using the group passed in the contructor and the 'folders' config item.
   The config item is also automatically updated when finished.

   Args:
      conf_group:
         The name of the config section to read the folders list from.
      title:
         Optional title for the dialog.
      done_cb:
         Function called when the user press the 'done' button.
         Signature: cb(new_folders_list)
   """
   def __init__(self, conf_group, title=_('Sources Manager'), done_cb=None):
      EmcDialog.__init__(self, title, style='list')
      self.button_add(_('Done'), icon='icon/ok',
                      selected_cb=self._cb_btn_done)
      self.button_add(_('Add'), icon='icon/plus',
                      selected_cb=self._cb_btn_add)
      self.button_add(_('Remove'), icon='icon/minus',
                      selected_cb=self._cb_btn_remove)
      self._sources = ini.get_string_list(conf_group, 'folders', ';')
      self._conf_group = conf_group
      self._done_cb = done_cb
      self._populate()

   def _populate(self):
      self.list_clear()
      for src in self._sources:
         self.list_item_append(src, 'icon/folder')
      self.list_go()

   def _cb_btn_add(self, btn):
      EmcFolderSelector(title=_('Choose a new source'), done_cb=self._cb_selected)

   def _cb_btn_remove(self, btn):
      it = self.list_item_selected_get()
      if it and it.text in self._sources:
         self._sources.remove(it.text)
         self._populate()

   def _cb_selected(self, path):
      if not path in self._sources:
         self._sources.append(path)
         self._populate()

   def _cb_btn_done(self, btn):
      ini.set_string_list(self._conf_group, 'folders', self._sources, ';')
      if callable(self._done_cb):
         self._done_cb(self._sources)
      self.delete()

################################################################################
class EmcVKeyboard(EmcDialog):
   """ TODO doc this """
   def __init__(self, accept_cb=None, dismiss_cb=None,
                      title=None, text=None, user_data=None):
      """ TODO doc this """

      self.accept_cb = accept_cb
      self.dismiss_cb = dismiss_cb
      self.user_data = user_data
      self.current_button = None
      self.buttons = list()

      # table
      tb = Table(win, homogeneous=True)
      tb.show()

      # set dialog title
      self.part_text_set('emc.text.title', title or _('Insert text'))

      # entry (TODO use scrolled_entry instead)
      self.entry = Entry(win, style='vkeyboard',
                         single_line=True, editable=True,
                         context_menu_disabled=True, focus_allow=True,
                         size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
      self.entry.callback_activated_add(self._accept_cb)
      self.entry.callback_aborted_add(self._dismiss_cb)
      if text: self.text_set(text)
      tb.pack(self.entry, 0, 0, 10, 1)
      self.entry.show()

      # standard keyb
      for i, c in enumerate(['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']):
         self._pack_btn(tb, i, 1, 1, 1, c, cb=self._default_btn_cb)
      for i, c in enumerate(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']):
         self._pack_btn(tb, i, 2, 1, 1, c, cb=self._default_btn_cb)
      for i, c in enumerate(['k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't']):
         self._pack_btn(tb, i, 3, 1, 1, c, cb=self._default_btn_cb)
      for i, c in enumerate(['u', 'v', 'w', 'x', 'y', 'z', '.', ',', ':', ';']):
         self._pack_btn(tb, i, 4, 1, 1, c, cb=self._default_btn_cb)

      self._pack_btn(tb, 0, 5, 3, 1, _('UPPERCASE'), cb=self._uppercase_cb)
      self._pack_btn(tb, 3, 5, 4, 1, _('SPACE'), cb=self._space_cb)
      self._pack_btn(tb, 7, 5, 3, 1, _('ERASE'), cb=self._erase_cb)

      self._pack_btn(tb, 0, 6, 4, 1, _('Dismiss'), 'icon/cancel', self._dismiss_cb)
      self._pack_btn(tb, 4, 6, 1, 1, None, 'icon/arrowL',
                                     lambda b: self.entry.cursor_prev())
      self._pack_btn(tb, 5, 6, 1, 1, None, 'icon/arrowR',
                                     lambda b: self.entry.cursor_next())
      self._pack_btn(tb, 6, 6, 4, 1, _('Accept'),  'icon/ok', self._accept_cb)

      # init the parent EmcDialog class
      EmcDialog.__init__(self, title=title, style='minimal', content=tb)

      # catch input events
      input_events.listener_add('vkbd', self.input_event_cb)
      self.entry.focus = True

   def _pack_btn(self, tb, x, y, w, h, label, icon=None, cb=None):
      b = EmcButton(label=label, icon=icon, cb=cb, size_hint_align=FILL_HORIZ)
      tb.pack(b, x, y, w, h)
      self.buttons.append(b)
      return b

   def delete(self):
      input_events.listener_del('vkbd')
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
      for btn in self.buttons:
         c = btn.text_get()
         if c and len(c) == 1 and c.isalpha():
            if c.islower():
               btn.text = c.upper()
               button.text = _('LOWERCASE')
            else:
               btn.text = c.lower()
               button.text = _('UPPERCASE')
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
      if event == 'EXIT':
         self._dismiss_cb(None)
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE
  
################################################################################
class EmcScrolledEntry(Entry, Scrollable):
   """ A non editable, multiline text entry, with autoscroll ability. """
   def __init__(self, parent=None, autoscroll=False, **kargs):
      self._animator = None
      self._timer = None
      self._autoscroll_amount = 0.0
      self._autoscroll_speed_scale = 1.0
      self._autoscroll_start_delay = 3.0
      self._autoscroll = autoscroll
      Entry.__init__(self, parent or layout, style='scrolledentry',
                     editable=False, scrollable=True, focus_allow=False, **kargs)

   @property
   def autoscroll(self):
      return self._autoscroll

   @autoscroll.setter
   def autoscroll(self, value):
      if value != self._autoscroll:
         self._autoscroll = value
         if value is True:
            self._autoscroll_start()
         else:
            self._autoscroll_stop()

   @property
   def autoscroll_speed_scale(self):
      return self._autoscroll_speed_scale

   @autoscroll_speed_scale.setter
   def autoscroll_speed_scale(self, value):
      self._autoscroll_speed_scale = value

   @property
   def autoscroll_start_delay(self):
      return self._autoscroll_start_delay

   @autoscroll_start_delay.setter
   def autoscroll_start_delay(self, value):
      self._autoscroll_start_delay = value

   def text_set(self, text):
      Entry.text_set(self, text)
      if self._autoscroll:
         self._autoscroll_stop()
         self._autoscroll_start()

   def scroll_by(self, sx=0, sy=0, animated=True):
      x, y, w, h = self.region
      if animated:
         self.region_bring_in(x + sx, y + sy, w, h)
      else:
         self.region_show(x + sx, y + sy, w, h)

   def delete(self):
      self._autoscroll_stop()
      Entry.delete(self)

   def _autoscroll_start(self):
      if self._animator is None:
         self.region_show(0, 0, 10, 10)
         self._timer = ecore.Timer(self._autoscroll_start_delay,
                                   self._delayed_start)

   def _autoscroll_stop(self):
      if self._animator is not None:
         self._animator.delete()
         self._animator = None
      if self._timer is not None:
         self._timer.delete()
         self._timer = None

   def _delayed_start(self):
      self._animator = ecore.Animator(self._animator_cb)

   def _animator_cb(self):
      self._autoscroll_amount += ecore.animator_frametime_get() * 15 * \
                                 self._autoscroll_speed_scale

      # at least one pixel to scroll ?
      if self._autoscroll_amount >= 1.0:
         x, y, w, h = old_region = self.region
         # print("Animator  ", old_region, self._autoscroll_amount)

         self.region_show(0, y + int(self._autoscroll_amount), w, h)
         self._autoscroll_amount = 0.0

         # bottom reached ?
         if old_region == self.region:
            self._timer = ecore.Timer(3.0, self._autoscroll_start)
            self._animator = None
            return ecore.ECORE_CALLBACK_CANCEL

      return ecore.ECORE_CALLBACK_RENEW

################################################################################
class DownloadManager(utils.Singleton):
   """ Manage a queue of urls to download.

   The only function you need is queue_download, the class is a singleton so
   you must use as:
   DownloadManager().queue_download(url, ...)

   """
   def __init__(self):
      self.handlers = {} # in progress {key:url, data:FileDownload}
      self.queue = []    # in queue (url, dest)

   def queue_download(self, url, dest_name=None, dest_ext=None, dest_folder=None):
      """ Put a new url in the download queue.

      Asking the user to confirm the operation, and giving the ability to
      change destination folder and destination name.

      Args:
         url: a valid url to download.
         dest_name: suggested name for the file, without extension.
         dest_ext: extension for the file, if None it is extracted from the url.
         dest_folder: where to put the downloaded file.

      """
      # destination folder
      if dest_folder is None:
         dest_folder = ini.get('general', 'download_folder')

      # destination file extension
      if dest_ext is None:
         try:
            # try to get the file extension from the url
            if '?' in url:
               dest_ext = url.split('?')[0].split('.')[-1]
            else:
               dest_ext = url.split('.')[-1]
            assert 6 > len(dest_ext) > 1
         except:
            dest_ext = 'mp4' # :/

      # destination file name
      fname = '.'.join((dest_name or 'epymc_download', dest_ext))

      # confirm dialog
      dia = EmcDialog(_('Download Manager'), text='')
      dia.data['url'] = url
      dia.data['dst_folder'] = dest_folder
      dia.data['dst_name'] = fname
      dia.button_add(_('Start download'), self._start_cb, dia)
      dia.button_add(_('Rename'), self._change_name_cb, dia)
      dia.button_add(_('Change folder'), self._change_folder_cb, dia)
      self._update_dialog_text(dia)

   # confirmation dialog stuff
   def _update_dialog_text(self, dia):
      text = _('File will be downloaded in the folder:<br> <b>{}</b><br>' \
               '<br>File will be named as:<br> <b>{}</b><br>' \
               '<br>You can rename the file using the <i>Rename</i> button or ' \
               'change the destination folder from the main configuration.') \
             .format(dia.data['dst_folder'], dia.data['dst_name'])
      dia.text_set(text)

   def _change_name_cb(self, bt, dia):
      EmcVKeyboard(title=_('Rename download'), text=dia.data['dst_name'],
                   accept_cb=self._change_name_done_cb, user_data=dia)

   def _change_name_done_cb(self, vkeyb, text, dia):
      dia.data['dst_name'] = text
      self._update_dialog_text(dia)

   def _change_folder_cb(self, bt, dia):
      EmcFolderSelector(title=_('Change destination folder'),
                        done_cb=self._change_folder_done_cb, cb_data=dia)

   def _change_folder_done_cb(self, folder, dia):
      dia.data['dst_folder'] = folder.replace('file://', '')
      self._update_dialog_text(dia)

   def _start_cb(self, bt, dia):
      url = dia.data['url']
      fullpath = os.path.join(dia.data['dst_folder'], dia.data['dst_name'])
      fullpath = utils.ensure_file_not_exists(fullpath)

      # check if the given url is in queue or in progress yet
      if url in self.handlers or \
            len([u for u,d in self.queue if u == url]) > 0:
         text = _('The file %s is in the download queue yet') % dia.data['dst_name']
         EmcDialog(style='error', text=text)
         dia.delete()
         return

      # close the dialog
      dia.delete()

      # add the download to the queue
      self.queue.append((url, fullpath))
      self._process_queue()

   ###
   def _process_queue(self):
      # no items in queue, nothing to do
      if len(self.queue) < 1:
         return

      # respect the max_concurrent_download option
      if len(self.handlers) >= ini.get_int('general', 'max_concurrent_download'):
         return

      # pop an item from the queue and download it
      url, dest = self.queue.pop(0)
      DBG('************  DOWNLOAD START  ****************')
      DBG('URL: ' + url)
      DBG('PAT: ' + dest)
      handler = utils.download_url_async(url, dest=dest+'.part',
                                         complete_cb=self._complete_cb,
                                         # progress_cb=self._progress_cb,
                                         myurl=url)
      self.handlers[url] = handler

      # notify
      text = '<title>%s</title><br>%s' % (_('Download started'),
                                          os.path.basename(dest))
      EmcNotify(text, icon='icon/download')

   # def _progress_cb(self, dest, dltotal, dlnow, myurl):
      # print "PROG (%s) %.2f %.2f" % (dest, dltotal, dlnow)
      # pass

   def _complete_cb(self, dest, status, myurl):

      # remove the .part suffix
      real_dest = dest[:-5]

      # download failed ?
      if status != 200:
         text = '<b>%s:</b><br>%s<br><br><failure>%s: %d (%s)</failure>' % \
               (_('Cannot download file'), os.path.basename(real_dest),
               _('Failure code'), status, utils.http_error_code_to_str(status))
         EmcDialog(style='error', title=_('Download failed'), text=text)
         return

      # rename the downloaded file
      os.rename(dest, real_dest)

      # notify
      text = '<title>%s</title><br>%s' % (_('Download completed'),
                                          os.path.basename(real_dest))
      EmcNotify(text, icon='icon/download')

      # remove the handler from the dict
      handler = self.handlers.pop(myurl, None)

      # see if other (in queue) download should be started now
      self._process_queue()
