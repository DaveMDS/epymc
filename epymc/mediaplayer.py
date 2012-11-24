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
import evas, ecore, edje, elementary, emotion
import utils, ini, gui, input_events, events
from gui import EmcFocusManager2, EmcDialog, EmcButton
from sdb import EmcDatabase


DEBUG = True
DEBUGN = 'MEDIAPLAYER'
def LOG(sev, msg):
   if   sev == 'err': print('%s ERROR: %s' % (DEBUGN, msg))
   elif sev == 'inf': print('%s: %s' % (DEBUGN, msg))
   elif sev == 'dbg' and DEBUG: print('%s: %s' % (DEBUGN, msg))


_volume = 0
_volume_muted = False
_emotion = None
_controls_visible = False
_volume_visible = False
_volume_hide_timer = None
_buttons = list()
_fman = None
_video_visible = False
_buffer_dialog = None
_update_timer = None
_url_queue = []
_onair_url = None
_play_db = None     # key: url  data: {'started': int, 'finished': int}

### API ###
def init():
   global _volume
   global _play_db

   # default config values
   ini.add_section('mediaplayer')
   if not ini.has_option('mediaplayer', 'volume'):
      ini.set('mediaplayer', 'volume', '75')
   if not ini.has_option('mediaplayer', 'backend'):
      ini.set('mediaplayer', 'backend', 'gstreamer')
   _volume = ini.get_int('mediaplayer', 'volume')

   # simple db to store the count of played files
   _play_db = EmcDatabase('playcount')

   # input events
   input_events.listener_add("videoplayer", input_event_cb)

def shutdown():
   global _play_db
   
   # TODO Shutdown all emotion stuff & the buttons list
   input_events.listener_del("videoplayer")
   del _play_db

### mediaplyer API ###
def play_url(url, only_audio=False):
   global _onair_url

   if not _emotion:
      _init_emotion()

   if url.find('://', 2, 15) is -1:
      url = 'file://' + url

   _onair_url = url

   LOG('dbg', 'play_url: ' + str(url))

   if url.startswith('file://') and not os.path.exists(url[7:]):
      text = '<b>File not found:</b><br>' + str(url)
      EmcDialog(text = text, style = 'error')
      return

   _emotion.file_set(url)
   if _emotion.play == False:
      volume_set(_volume)
      volume_mute_set(_volume_muted)
      _emotion.audio_mute = _volume_muted
      _emotion.play = True

   events.event_emit('PLAYBACK_STARTED')

   if not only_audio:
      video_player_show()

   # keep the counts of played/finished urls
   if _play_db.id_exists(url):
      counts = _play_db.get_data(url)
      counts['started'] += 1
      _play_db.set_data(url, counts)
   else:
      counts = dict()
      counts['started'] = 1
      counts['finished'] = 0
      _play_db.set_data(url, counts)
   LOG('dbg', 'url started: %d finished: %d' %
              (counts['started'], counts['finished']))
   
   ## TEST VARIOUS INFO
   LOG('dbg', 'TITLE: ' + str(_emotion.title_get()))
   LOG('dbg', 'VIDEO CHNS COUNT: ' + str(_emotion.video_channel_count()))
   LOG('dbg', 'AUDIO CHNS COUNT: ' + str(_emotion.audio_channel_count()))
   LOG('dbg', 'VIDEO CHANS GET: ' + str(_emotion.video_channel_get()))
   LOG('dbg', 'AUDIO CHANS GET: ' + str(_emotion.audio_channel_get()))
   LOG('dbg', 'INFO DICT: ' + str(_emotion.meta_info_dict_get()))
   LOG('dbg', 'SIZE: ' + str(_emotion.size))
   LOG('dbg', 'IMAGE_SIZE: ' + str(_emotion.image_size))
   LOG('dbg', 'RATIO: ' + str(_emotion.ratio_get()))
   ##

def queue_url(url, only_audio=False):
   _url_queue.append(url)
   if _emotion is None or _emotion.play == False:
      play_url(url, only_audio)

def play_counts_get(url):
   try:
      return _play_db.get_data(url)
   except:
      return {'started': 0, 'finished': 0}

def stop():
   LOG('dbg', 'Stop()')
   _emotion.play = False
   _emotion.position = 0.0

   # this cause a random color to be shown for an instant, but it is
   # necessary to hide a bug somewhere else:
   # without this the video restart to play when I set position to 0.0 :/
   _emotion.file_set('')

   events.event_emit('PLAYBACK_FINISHED')

def forward():
   LOG('dbg', 'Forward cb' + str(_emotion.position))
   LOG('dbg', 'Seekable: ' + str(_emotion.seekable))
   _emotion.position += 10 #TODO make this configurable

def backward():
   LOG('dbg', 'Backward cb' + str(_emotion.position))
   LOG('dbg', 'Seekable: ' + str(_emotion.seekable))
   _emotion.position -= 10 #TODO make this configurable

def fforward():
   LOG('dbg', 'FastForward cb' + str(_emotion.position))
   LOG('dbg', 'Seekable: ' + str(_emotion.seekable))
   _emotion.position += 60 #TODO make this configurable

def fbackward():
   LOG('dbg', 'FastBackward cb' + str(_emotion.position))
   LOG('dbg', 'Seekable: ' + str(_emotion.seekable))
   _emotion.position -= 60 #TODO make this configurable

def volume_set(vol):
   global _volume

   _volume = max(0, min(int(vol), 100))
   ini.set('mediaplayer', 'volume', _volume)
   gui.slider_val_set('volume.slider:dragable1', _volume / 100.0)
   if _emotion:
      _emotion.audio_volume_set(_volume / 100.0)

def volume_get():
   return _volume

def volume_mute_set(mute):
   global _volume_muted

   _volume_muted = bool(mute)
   gui.signal_emit('volume,mute,' + ('on' if mute else 'off'))

   if _emotion:
      _emotion.audio_mute = _volume_muted

def volume_mute_toggle():
   volume_mute_set(not _volume_muted)

### gui API ###
def video_player_show():
   global _video_visible
   global _update_timer

   gui.signal_emit('videoplayer,show')
   _video_visible = True
   input_events.listener_promote('videoplayer')
   if _update_timer is not None:
      update_timer.delete()
   _update_timer = ecore.Timer(0.2, _update_timer_cb)

def video_player_hide():
   global _video_visible
   global _update_timer

   video_controls_hide()
   _video_visible = False
   if _update_timer is not None:
      _update_timer.delete()
      _update_timer = None
   gui.signal_emit('videoplayer,hide')

def video_controls_show():
   global _controls_visible

   gui.signal_emit('videoplayer,controls,show')
   _controls_visible = True
   volume_show()

def video_controls_hide():
   global _controls_visible

   gui.signal_emit('videoplayer,controls,hide')
   _controls_visible = False
   volume_hide()

def video_controls_toggle():
   if _controls_visible:
      video_controls_hide()
   else:
      video_controls_show()

def volume_show(hidein = 0):
   global _volume_visible
   global _volume_hide_timer

   gui.signal_emit('volume,show')
   _volume_visible = True
   if hidein > 0:
      if _volume_hide_timer: _volume_hide_timer.delete()
      _volume_hide_timer = ecore.Timer(hidein, volume_hide)

def volume_hide():
   global _volume_visible
   global _volume_hide_timer

   gui.signal_emit('volume,hide')
   _volume_visible = False
   _volume_hide_timer = None

def poster_set(poster, extra_path = None):
   gui.swallow_set("videoplayer.controls.poster", gui.load_image(poster, extra_path))

def title_set(title):
   gui.text_set("videoplayer.controls.title", title)

### internals ###
def _update_timer_cb():
   global _buffer_dialog

   def _dialog_canc_cb(dia):
      _buffer_dialog = None

   if _buffer_dialog is not None:
      _buffer_dialog.progress_set(_emotion.buffer_size)
      if _emotion.buffer_size >= 1.0:
         _emotion.play = _buffer_dialog.data['playing_state']
         _buffer_dialog.delete()
         _buffer_dialog = None

   elif _emotion.buffer_size < 1.0:
      _buffer_dialog = EmcDialog(title='buffering', style = 'progress',
                                 canc_cb = _dialog_canc_cb)
      _buffer_dialog.data['playing_state'] = _emotion.play
      _emotion.play = False

   _update_slider()
   return True # timer renew

def _init_emotion():
   global _emotion
   global _fman

   backend = ini.get('mediaplayer', 'backend')
   _emotion = emotion.Emotion(gui.layout.evas, module_filename=backend)
   gui.swallow_set('videoplayer.video', _emotion)
   _emotion.smooth_scale = True

   gui.layout.edje.signal_callback_add("mouse,down,1", "videoplayer.events",
                                 (lambda a,s,d: video_controls_toggle()))
   # _emotion.on_key_down_add(_cb)
   # _emotion.on_audio_level_change_add(_cb_volume_change)
   _emotion.on_frame_resize_add(_cb_frame_resize)
   _emotion.on_playback_finished_add(_cb_playback_finished)

   # Progress doesn't work, use frame_decode instead...but it's TOOO often
   #  yes, too often and not firing while buffering...Used a timer instead
   # _emotion.on_progress_change_add((lambda v: _update_slider()))
   # _emotion.on_frame_decode_add((lambda v: _update_slider()))

   # focus manager for play/stop/etc.. buttons
   _fman = EmcFocusManager2()

   #  <<  fast backward
   bt = EmcButton(icon='icon/fbwd')
   bt.callback_clicked_add(_cb_btn_fbackward)
   bt.data['cb'] = _cb_btn_fbackward
   _fman.obj_add(bt)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)

   #  <   backward
   bt = EmcButton(icon='icon/bwd')
   bt.callback_clicked_add(_cb_btn_backward)
   bt.data['cb'] = _cb_btn_backward
   _fman.obj_add(bt)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)

   #  stop
   bt = EmcButton(icon='icon/stop')
   bt.callback_clicked_add(_cb_btn_stop)
   bt.data['cb'] = _cb_btn_stop
   _fman.obj_add(bt)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)

   #  play/pause
   bt = EmcButton(icon='icon/play')
   bt.callback_clicked_add(_cb_btn_play)
   bt.data['cb'] = _cb_btn_play
   _fman.obj_add(bt)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)
   # ARGH this does'n work
   # for some reason in fman mouse_in callback is called once (wrong) on
   # the creation of the obj ...dunno why
   _fman.focused_set(bt)

   #  >   forward
   bt = EmcButton(icon='icon/fwd')
   bt.callback_clicked_add(_cb_btn_forward)
   bt.data['cb'] = _cb_btn_forward
   _fman.obj_add(bt)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)
   
   #  >>  fast forward
   bt = EmcButton(icon='icon/ffwd')
   bt.callback_clicked_add(_cb_btn_fforward)
   bt.data['cb'] = _cb_btn_fforward
   _fman.obj_add(bt)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)


   #  submenu audio
   bt = EmcButton('Audio')
   # bt.callback_clicked_add(_cb_btn_fforward)
   bt.data['cb'] = None
   _fman.obj_add(bt)
   gui.box_append('videoplayer.controls.btn_box2', bt)
   _buttons.append(bt)

   #  submenu video
   bt = EmcButton('Video')
   # bt.callback_clicked_add(_cb_btn_fforward)
   bt.data['cb'] = None
   _fman.obj_add(bt)
   gui.box_append('videoplayer.controls.btn_box2', bt)
   _buttons.append(bt)


   # update emotion position when mouse drag the progress slider
   def _drag_prog(obj, emission, source):
      (val,val2) = gui.slider_val_get('videoplayer.controls.slider:dragable1')
      _emotion.position_set(_emotion.play_length * val)
   gui.signal_cb_add('drag', 'videoplayer.controls.slider:dragable1', _drag_prog)

   # update volume when mouse drag the volume slider
   def _drag_vol(obj, emission, source):
      (val,val2) = gui.slider_val_get('volume.slider:dragable1')
      volume_set(val * 100.0)
   gui.signal_cb_add('drag', 'volume.slider:dragable1', _drag_vol)

def _cb_playback_finished(vid):

   counts = _play_db.get_data(_onair_url)
   counts['finished'] += 1
   _play_db.set_data(_onair_url, counts)

   stop()

   if len(_url_queue) > 0:
      _url_queue.pop(0)

   if len(_url_queue) > 0:
      play_url(_url_queue[0], only_audio=True)
   else:
      video_player_hide()
      volume_hide()

def _cb_frame_resize(vid):
   (w, h) = vid.image_size
   edje.extern_object_aspect_set(vid, edje.EDJE_ASPECT_CONTROL_BOTH, w, h)

def _cb_btn_play(btn):
   _emotion.play = not _emotion.play

def _cb_btn_stop(btn):
   stop()
   video_player_hide()

def _cb_btn_forward(btn):
   forward()

def _cb_btn_backward(btn):
   backward()

def _cb_btn_fforward(btn):
   fforward()

def _cb_btn_fbackward(btn):
   fbackward()

def _update_slider():
   if _controls_visible:
      pos = _emotion.position
      len = _emotion.play_length

      lh = int(len / 3600)
      lm = int((len / 60) - (lh * 60))
      ls = int(len - (lm * 60) - (lh * 3600))

      ph = int(pos / 3600)
      pm = int((pos / 60) - (ph * 60))
      ps = int(pos - (pm * 60) - (ph * 3600))

      if len > 0:
         gui.slider_val_set('videoplayer.controls.slider:dragable1', pos / len)
      gui.text_set('videoplayer.controls.position', '%i:%02i:%02i' % (ph,pm,ps))
      gui.text_set('videoplayer.controls.length', '%i:%02i:%02i' % (lh,lm,ls))


### input events ###
def input_event_cb(event):

   if event == 'VOLUME_UP':
      volume_set(_volume + 5)
      volume_show(hidein = 3)
      return input_events.EVENT_BLOCK
   elif event == 'VOLUME_DOWN':
      volume_set(_volume - 5)
      volume_show(hidein = 3)
      return input_events.EVENT_BLOCK
   elif event == 'VOLUME_MUTE':
      volume_mute_toggle()
      volume_show(hidein = 3)
      return input_events.EVENT_BLOCK

   if not _video_visible:
      return input_events.EVENT_CONTINUE

   if event == 'EXIT':
      stop()
      video_player_hide()
      volume_hide()
      return input_events.EVENT_BLOCK

   if _controls_visible:
      if event == 'BACK':
         video_controls_hide()
         return input_events.EVENT_BLOCK
      if event == 'OK':
         button = _fman.focused_get()
         cb = button.data['cb']
         if callable(cb):
            cb(button)
         # TODO TRY THIS INSTEAD:
         ## evas_object_smart_callback_call(obj, 'sig', NULL);
         return input_events.EVENT_BLOCK
      if event == 'RIGHT':
         _fman.focus_move('r')
         return input_events.EVENT_BLOCK
      elif event == 'LEFT':
         _fman.focus_move('l')
         return input_events.EVENT_BLOCK
      if event == 'UP':
         _fman.focus_move('u')
         return input_events.EVENT_BLOCK
      elif event == 'DOWN':
         _fman.focus_move('d')
         return input_events.EVENT_BLOCK
   else:
      if event == 'BACK':
         stop()
         video_player_hide()
         return input_events.EVENT_BLOCK
      elif event == 'OK':
         video_controls_show()
         return input_events.EVENT_BLOCK
      elif event == 'RIGHT':
         forward()
         return input_events.EVENT_BLOCK
      elif event == 'LEFT':
         backward()
         return input_events.EVENT_BLOCK
      elif event == 'UP':
         # fforward()
         volume_set(_volume + 5)
         volume_show(hidein = 3)
         
         return input_events.EVENT_BLOCK
      elif event == 'DOWN':
         # fbackward()
         volume_set(_volume - 5)
         volume_show(hidein = 3)
         return input_events.EVENT_BLOCK

   if event == 'TOGGLE_PAUSE':
      _emotion.play = not _emotion.play
      return input_events.EVENT_BLOCK
   elif event == 'PLAY':
      _emotion.play = True
      return input_events.EVENT_BLOCK
   elif event == 'PAUSE':
      _emotion.play = False
      return input_events.EVENT_BLOCK
   elif event == 'STOP':
      stop()
      video_player_hide()
      return input_events.EVENT_BLOCK
   elif event == 'FORWARD':
      forward()
      return input_events.EVENT_BLOCK
   elif event == 'BACKWARD':
      backward()
      return input_events.EVENT_BLOCK
   elif event == 'FAST_FORWARD':
      fforward()
      return input_events.EVENT_BLOCK
   elif event == 'FAST_BACKWARD':
      fbackward()
      return input_events.EVENT_BLOCK

   return input_events.EVENT_CONTINUE
