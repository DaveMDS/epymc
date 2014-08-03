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

import os, sys, re, glob
from operator import itemgetter

from efl import evas, ecore, edje, elementary, emotion

from epymc import utils, ini, gui, input_events, events
from epymc.gui import EmcFocusManager, EmcDialog, EmcButton, EmcMenu, DownloadManager
from epymc.sdb import EmcDatabase


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
_buttons = list()
_fman = None
_video_visible = False
_buffer_dialog = None
_update_timer = None
_onair_url = None
_onair_title = None
_play_db = None # key: url  data: {'started': 14, 'finished': 0, 'stop_at': 0 }
_play_pause_btn = None
_subtitles = None # Subtitle class instance

### API ###
def init():
   global _volume
   global _play_db

   # default config values
   ini.add_section('mediaplayer')
   ini.add_section('subtitles')
   if not ini.has_option('mediaplayer', 'volume'):
      ini.set('mediaplayer', 'volume', '75')
   if not ini.has_option('mediaplayer', 'backend'):
      ini.set('mediaplayer', 'backend', 'gstreamer1')
   if not ini.has_option('subtitles', 'langs'):
      ini.set('subtitles', 'langs', 'en')
   if not ini.has_option('subtitles', 'encoding'):
      ini.set('subtitles', 'encoding', 'latin_1')
   if not ini.has_option('subtitles', 'always_try_utf8'):
      ini.set('subtitles', 'always_try_utf8', 'True')
   if not ini.has_option('subtitles', 'opensubtitles_user'):
      ini.set('subtitles', 'opensubtitles_user', '')
   if not ini.has_option('subtitles', 'opensubtitles_pass'):
      ini.set('subtitles', 'opensubtitles_pass', '')
      
   _volume = ini.get_int('mediaplayer', 'volume')

   # simple db to store the count of played files
   _play_db = EmcDatabase('playcount')

   # input events
   input_events.listener_add("mediaplayer", input_event_cb)

def shutdown():
   global _play_db

   # TODO Shutdown all emotion stuff & the buttons list
   input_events.listener_del("mediaplayer")
   del _play_db

### mediaplyer API ###
def play_url(url, only_audio = False, start_from = 0):
   global _onair_url, _onair_title, _subtitles

   if not _emotion:
      if not _init_emotion():
         return False

   if not _fman:
      _init_mediaplayer_gui()

   url = str(url) # must be a string not unicode, otherwise it cannot be hashed
   if url.find('://', 2, 15) is -1:
      url = 'file://' + url

   _onair_url = url
   _onair_title = None

   LOG('dbg', 'play_url: %s' % url)

   if url.startswith('file://') and not os.path.exists(url[7:]):
      text = '<b>%s:</b><br>%s' % (_('File not found'), url)
      EmcDialog(text = text, style = 'error')
      return

   # Do not pass "file://" to emotion. Vlc has a bug somewhere that prevent
   # files with special chars in them to play (the bug don't appear if no
   # "file://" is given. The bug can be seen also using normal vlc from
   # the command line.
   _emotion.file_set(url[7:] if url.startswith('file://') else url)

   _emotion.position = start_from
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
      counts = { 'started': 0, 'finished': 0, 'stop_at': 0 }
      _play_db.set_data(url, counts)
   LOG('dbg', 'url started: %d finished: %d' %
              (counts['started'], counts['finished']))

   # Try to load subs for this url
   _subtitles = Subtitles(url)

   ## TEST VARIOUS INFO
   # LOG('dbg', 'TITLE: ' + str(_emotion.title_get()))
   # LOG('dbg', 'CHAPTER COUNT: ' + str(_emotion.chapter_count()))
   # LOG('dbg', 'VIDEO CHNS COUNT: ' + str(_emotion.video_channel_count()))
   # LOG('dbg', 'AUDIO CHNS COUNT: ' + str(_emotion.audio_channel_count()))
   # LOG('dbg', 'SPU CHNS COUNT: ' + str(_emotion.spu_channel_count()))
   # LOG('dbg', 'VIDEO CHAN GET: ' + str(_emotion.video_channel_get()))
   # LOG('dbg', 'AUDIO CHAN GET: ' + str(_emotion.audio_channel_get()))
   # LOG('dbg', 'SPU CHAN GET: ' + str(_emotion.spu_channel_get()))
   # LOG('dbg', 'INFO DICT: ' + str(_emotion.meta_info_dict_get()))
   # LOG('dbg', 'SIZE: ' + str(_emotion.size))
   # LOG('dbg', 'IMAGE_SIZE: ' + str(_emotion.image_size))
   # LOG('dbg', 'RATIO: ' + str(_emotion.ratio_get()))
   ##

   return True

def play_counts_get(url):
   try:
      return _play_db.get_data(url)
   except:
      return { 'started': 0,   # num times started
               'finished': 0,  # num times finished
               'stop_at': 0 }  # last play pos

def stop():
   global _emotion, _onair_url, _subtitles

   LOG('dbg', 'Stop()')

   if _emotion is None:
      return

   counts = _play_db.get_data(_onair_url)
   if _emotion.position >= _emotion.play_length - 5 or _emotion.position == 0.0: # vlc set the pos at zero when finished :/
      counts['finished'] += 1
      counts['stop_at'] = 0
   else:
      counts['stop_at'] = _emotion.position
   _play_db.set_data(_onair_url, counts)

   _onair_url = None

   # delete the emotion object
   _emotion.play = False
   _emotion.position = 0.0
   
   _emotion.delete()
   del _emotion
   _emotion = None

   # clear the subtitles instance
   if _subtitles:
      _subtitles.delete()
      _subtitles = None

   events.event_emit('PLAYBACK_FINISHED')

def pause():
   _emotion.play = False
   _play_pause_btn.icon_set('icon/play')

def unpause():
   _emotion.play = True
   _play_pause_btn.icon_set('icon/pause')

def pause_toggle():
   if _emotion.play is True:
      pause()
   else:
      unpause()

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
   gui.volume_set(_volume / 100.0)
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
   input_events.listener_promote('mediaplayer')
   if _update_timer is not None:
      update_timer.delete()
   _update_timer = ecore.Timer(1.0, _update_timer_cb)

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
   gui.volume_show()
   _update_slider()

def video_controls_hide():
   global _controls_visible

   gui.signal_emit('videoplayer,controls,hide')
   _controls_visible = False
   gui.volume_hide()

def video_controls_toggle():
   if _controls_visible:
      video_controls_hide()
   else:
      video_controls_show()

def poster_set(poster = None, extra_path = None):
   if poster:
      gui.swallow_set("videoplayer.controls.poster", gui.load_image(poster, extra_path))
   else:
      gui.swallow_set("videoplayer.controls.poster", gui.load_image('dvd_cover_blank.png'))

def title_set(title):
   global _onair_title

   _onair_title = title
   gui.text_set("videoplayer.controls.title", title)

### internals ###
def _update_timer_cb():
   global _buffer_dialog

   def _dialog_canc_cb(dia):
      _buffer_dialog = None

   if _buffer_dialog is not None:
      _buffer_dialog.progress_set(_emotion.buffer_size)
      if _emotion.buffer_size >= 1.0:
         _emotion.play = True
         _buffer_dialog.delete()
         _buffer_dialog = None

   elif _emotion.buffer_size < 1.0:
      _buffer_dialog = EmcDialog(title=_('buffering'), style = 'progress',
                                 canc_cb = _dialog_canc_cb)
      _emotion.play = False

   _update_slider()

   # keep the screensaver out while playing videos
   if _emotion.play == _video_visible == True:
      events.event_emit('KEEP_ALIVE')

   return True # timer renew

def _init_emotion():
   global _emotion

   backend = ini.get('mediaplayer', 'backend')
   try:
      try:
         _emotion = emotion.Emotion(gui.layout.evas, module_filename=backend)
      except:
         _emotion = emotion.Emotion(gui.layout.evas, module_name=backend)
   except:
      EmcDialog(style='error', text=_('Cannot init emotion engine:<br>%s') % backend)
      return False

   gui.swallow_set('videoplayer.video', _emotion)
   _emotion.smooth_scale = True

   # _emotion.on_key_down_add(_cb)
   # _emotion.on_audio_level_change_add(_cb_volume_change)
   _emotion.on_frame_resize_add(_cb_frame_resize)
   _emotion.on_playback_finished_add(_cb_playback_finished)

   # Progress doesn't work, use frame_decode instead...but it's TOOO often
   #  yes, too often and not firing while buffering...Used a timer instead
   # _emotion.on_progress_change_add((lambda v: _update_slider()))
   # _emotion.on_frame_decode_add((lambda v: _update_slider()))

   return True

def _init_mediaplayer_gui():
   global _fman

   # focus manager for play/stop/etc.. buttons
   _fman = EmcFocusManager()

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
   bt = EmcButton(icon='icon/pause')
   bt.callback_clicked_add(_cb_btn_play)
   bt.data['cb'] = _cb_btn_play
   _fman.obj_add(bt)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)
   # ARGH this does'n work
   # for some reason in fman mouse_in callback is called once (wrong) on
   # the creation of the obj ...dunno why
   _fman.focused_set(bt)
   # store a reference to the button so we can change the icon later
   global _play_pause_btn
   _play_pause_btn = bt

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
   bt = EmcButton(_('Audio'))
   bt.callback_clicked_add(_cb_btn_audio)
   bt.data['cb'] = _cb_btn_audio
   _fman.obj_add(bt)
   gui.box_append('videoplayer.controls.btn_box2', bt)
   _buttons.append(bt)

   #  submenu video
   bt = EmcButton(_('Video'))
   bt.callback_clicked_add(_cb_btn_video)
   bt.data['cb'] = _cb_btn_video
   _fman.obj_add(bt)
   gui.box_append('videoplayer.controls.btn_box2', bt)
   _buttons.append(bt)

   #  submenu subtitles
   bt = EmcButton(_('Subtitles'))
   bt.callback_clicked_add(_cb_btn_subtitles)
   bt.data['cb'] = _cb_btn_subtitles
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

   # click on video to show/hide the controls
   gui.layout.edje.signal_callback_add("mouse,down,1", "videoplayer.events",
                                       (lambda a,s,d: video_controls_toggle()))

def _cb_playback_finished(vid):

   stop()

   video_player_hide()
   gui.volume_hide()

def _cb_frame_resize(vid):
   (w, h) = vid.image_size
   edje.extern_object_aspect_set(vid, edje.EDJE_ASPECT_CONTROL_BOTH, w, h)

def _cb_btn_play(btn):
   pause_toggle()

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

def _cb_btn_audio(btn):
   trk_cnt = _emotion.audio_channel_count()
   menu = EmcMenu(relto = btn)
   for n in range(trk_cnt):
      name = _emotion.audio_channel_name_get(n)
      if name:
         name = _('Audio track: %s') % name
      else:
         name = _('Audio track #%d') % (n + 1)
      item = menu.item_add(None, name, None, _cb_menu_audio_track, n)

   menu.item_separator_add()
   item = menu.item_add(None, _('Mute'), 'clock', _cb_menu_mute)

def _cb_btn_video(btn):
   trk_cnt = _emotion.video_channel_count()
   menu = EmcMenu(relto = btn)
   for n in range(trk_cnt):
      name = _emotion.video_channel_name_get(n)
      if name:
         name = _('Video track: %s') % name
      else:
         name = _('Video track #%d') % (n + 1)
      item = menu.item_add(None, name, None, _cb_menu_video_track, n)

   menu.item_separator_add()
   it = menu.item_add(None, _('Download video'), None, _cb_menu_download)
   if _onair_url.startswith('file://'):
      it.disabled = True


def _cb_menu_audio_track(menu, item, track_num):
   print("TODO: add support in emotion/gstreamer for this")
   print("Change to audio track #" + str(track_num))
   _emotion.audio_channel_set(track_num)

def _cb_menu_video_track(menu, item, track_num):
   print("TODO: add support in emotion/gstreamer for this")
   print("Change to video track #" + str(track_num))
   _emotion.video_channel_set(track_num)

def _cb_menu_mute(menu, item):
   volume_mute_toggle()

def _cb_menu_download(menu, item):
   DownloadManager().queue_download(_onair_url, _onair_title)

# subtitles menu
def _cb_btn_subtitles(btn):
   menu = EmcMenu(relto=btn)
   menu.item_add(None, _('No subtitles'),
                 None if _subtitles.current_file else 'arrow_right',
                 _cb_menu_sub_track, None)
   for sub in _subtitles.avail_files:
      if sub.startswith(utils.user_conf_dir):
         name = os.path.basename(sub)[33:]
      else:
         name = os.path.basename(sub)
      menu.item_add(None, name,
                    'arrow_right' if sub == _subtitles.current_file else None,
                    _cb_menu_sub_track, sub)

   menu.item_separator_add()
   menu.item_add(None, _('Download subtitles'), None, _cb_menu_sub_download)

def _cb_menu_sub_track(menu, item, sub_file):
   _subtitles.file_set(sub_file)

def _cb_menu_sub_download(menu, item):
   Opensubtitles(_onair_url)

def _update_slider():
   if _controls_visible:
      pos = _emotion.position
      len = _emotion.play_length

      lh = int(len / 3600)
      lm = int(len / 60) % 60
      ls = int(len % 60)

      ph = int(pos / 3600)
      pm = int(pos / 60) % 60
      ps = int(pos % 60)

      if len > 0:
         gui.slider_val_set('videoplayer.controls.slider:dragable1', pos / len)
      gui.text_set('videoplayer.controls.position', '%i:%02i:%02i' % (ph,pm,ps))
      gui.text_set('videoplayer.controls.length', '%i:%02i:%02i' % (lh,lm,ls))


### input events ###
def input_event_cb(event):

   if event == 'VOLUME_UP':
      volume_set(_volume + 5)
      events.event_emit('VOLUME_CHANGED')
      return input_events.EVENT_BLOCK

   elif event == 'VOLUME_DOWN':
      volume_set(_volume - 5)
      events.event_emit('VOLUME_CHANGED')
      return input_events.EVENT_BLOCK

   elif event == 'VOLUME_MUTE':
      volume_mute_toggle()
      events.event_emit('VOLUME_CHANGED')
      return input_events.EVENT_BLOCK

   elif event == 'TOGGLE_PAUSE':
      pause_toggle()
      return input_events.EVENT_BLOCK

   elif event == 'PLAY':
      unpause()
      return input_events.EVENT_BLOCK

   elif event == 'PAUSE':
      pause()
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


   if not _video_visible:
      return input_events.EVENT_CONTINUE


   if event == 'EXIT':
      stop()
      video_player_hide()
      gui.volume_hide()
      return input_events.EVENT_BLOCK

   if _controls_visible:
      if event == 'BACK':
         video_controls_hide()
         return input_events.EVENT_BLOCK
      elif event == 'OK':
         button = _fman.focused_get()
         cb = button.data['cb']
         if callable(cb):
            cb(button)
         # TODO TRY THIS INSTEAD:
         ## evas_object_smart_callback_call(obj, 'sig', NULL);
         return input_events.EVENT_BLOCK
      elif event == 'RIGHT':
         _fman.focus_move('r')
         return input_events.EVENT_BLOCK
      elif event == 'LEFT':
         _fman.focus_move('l')
         return input_events.EVENT_BLOCK
      elif event == 'UP':
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
         volume_set(_volume + 5)
         events.event_emit('VOLUME_CHANGED')
         return input_events.EVENT_BLOCK
      elif event == 'DOWN':
         volume_set(_volume - 5)
         events.event_emit('VOLUME_CHANGED')
         return input_events.EVENT_BLOCK

   return input_events.EVENT_CONTINUE

### subtitles ###
def srt_time_to_seconds(time):
   split_time = time.split(',')
   major, minor = (split_time[0].split(':'), split_time[1])
   return int(major[0])*1440 + int(major[1])*60 + int(major[2]) + float(minor)/1000

def srt_read_encoding_py2(fname, encodings):
   with open(fname, 'r') as f:
      text = f.read()
      for enc in encodings:
         try:
            LOG('dbg', 'Trying encoding: %s' % enc)
            return text.decode(encoding=enc, errors='strict')
         except:
            pass
      return text

def srt_read_encoding_py3(fname, encodings):
   for enc in encodings:
      try:
         LOG('dbg', 'Trying encoding: %s' % enc)
         with open(fname, encoding=enc) as f:
            return f.read()
      except:
         pass

class SubtitleItem(object):
   def __init__(self, idx, start, end, text):
      self.idx = idx
      self.start = srt_time_to_seconds(start)
      self.end = srt_time_to_seconds(end)
      self.text = text

   def __str__(self):
      return '%f -> %f : %s' % (self.start, self.end, self.text)

class Subtitles(object):
   def __init__(self, url):
      self.avail_files = []
      self.current_file = None
      self.items = []
      self.current_item = None
      self.timer = None

      name = os.path.splitext(utils.url2path(url))[0]
      main_srt = name + '.srt'
      if os.path.exists(main_srt):
         self.avail_files.append(main_srt)

      for fname in glob.glob(name + '*.srt'):
         if not fname in self.avail_files:
            self.avail_files.append(fname)

      md5 = utils.md5(utils.url2path(url))
      p = os.path.join(utils.user_conf_dir, 'subtitles', md5 + '_*.srt')
      for fname in glob.glob(p):
         self.avail_files.append(fname)

      if len(self.avail_files) > 0:
         self.file_set(self.avail_files[0])

   def file_set(self, fname):
      if self.timer:
         self.timer.delete()
      self.clear()
      self.items = []
      self.current_item = None
      self.current_file = None

      if fname is not None:
         self.parse_srt(fname)
         if self.items:
            self.current_file = fname
            self.timer = ecore.Timer(0.2, self._timer_cb)

   def delete(self):
      self.file_set(None)
      self.clear()

   def parse_srt(self, fname):
      LOG('inf', 'Loading subs from file: %s' % fname)
      # read from file using the wanted encoding
      encodings = []
      if ini.get_bool('subtitles', 'always_try_utf8'):
         encodings.append('utf-8')
      encodings.append(ini.get('subtitles', 'encoding'))
      if sys.version_info[0] < 3:
         full_text = srt_read_encoding_py2(fname, encodings)
      else:
         full_text = srt_read_encoding_py3(fname, encodings)

      # parse the srt content
      idx = 0
      for s in re.sub('\r\n', '\n', full_text).split('\n\n'):
         st = [ x for x in s.split('\n') if x ] # spit and remove empty lines
         if len(st) >= 3:
            split = st[1].split(' --> ')
            item = SubtitleItem(idx, split[0], split[1], '<br>'.join(st[2:]))
            self.items.append(item)
            idx += 1

   def item_apply(self, item):
      if item != self.current_item:
         gui.text_set('videoplayer.subs', item.text)
         self.current_item = item

   def clear(self):
      gui.text_set('videoplayer.subs', '')

   def _timer_cb(self):
      if _emotion is None:
         self.timer = None
         return ecore.ECORE_CALLBACK_CANCEL
      pos = _emotion.position

      # current item is still valid ?
      item = self.current_item
      if item and item.start < pos < item.end:
         return ecore.ECORE_CALLBACK_RENEW

      # next item valid ?
      if item and (item.idx + 1) < len(self.items):
         next_item = self.items[item.idx + 1]
         if item.end < pos < next_item.start:
            # pause between current and the next
            self.clear()
            return ecore.ECORE_CALLBACK_RENEW
         elif next_item.start < pos < next_item.end:
            # apply the next
            self.item_apply(next_item)
            return ecore.ECORE_CALLBACK_RENEW

      # fallback: search all the items (TODO optimize using a binary search)
      for item in self.items:
         if item.start < pos < item.end:
            self.item_apply(item)
            return ecore.ECORE_CALLBACK_RENEW
         if item.end > pos:
            self.clear()
            return ecore.ECORE_CALLBACK_RENEW

      self.clear()
      return ecore.ECORE_CALLBACK_RENEW

try:
   from xmlrpclib import ServerProxy # py2
except:
   from xmlrpc.client import ServerProxy # py3
import struct
import threading
import zlib
import base64
import codecs
import hashlib


class Opensubtitles(object):
   """ OpenSubtitles API implementation.

   Check the official API documentation at:
   http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC

   """
   OPENSUBTITLES_SERVER = 'http://api.opensubtitles.org/xml-rpc'
   # USER_AGENT = 'Emotion Media Center' + version
   USER_AGENT = 'OS Test User Agent'

   def __init__ (self, url):
      self.dialog = None
      self.token = None
      self.results = []
      self.oso_user = ini.get('subtitles', 'opensubtitles_user')
      self.oso_pass = ini.get('subtitles', 'opensubtitles_pass')
      self.langs2 = ini.get_string_list('subtitles', 'langs')
      self.langs3 = [ utils.iso639_1_to_3(l) for l in self.langs2 ]
      self.path = utils.url2path(url)
      self.size = os.path.getsize(self.path)
      self.hash = self.calc_hash()
      self.xmlrpc = ServerProxy(self.OPENSUBTITLES_SERVER, allow_none=True)

      self.build_wait_dialog(_('Searching subtitles'))
      self.search_in_a_thread()

   def calc_hash(self):
      """'Original from: http://goo.gl/qqfM0 """
      longlongformat = 'q' # long long
      bytesize = struct.calcsize(longlongformat)

      try:
         f = open(self.path, "rb")
      except(IOError):
         return "IOError"

      hash = self.size

      if self.size < 65536 * 2:
         return "SizeError"

      for x in range(int(65536 / bytesize)):
         buffer = f.read(bytesize)
         (l_value, ) = struct.unpack(longlongformat, buffer)
         hash += l_value
         hash = hash & 0xFFFFFFFFFFFFFFFF # to remain as 64bit number

      f.seek(max(0, self.size - 65536), 0)
      for x in range(int(65536 / bytesize)):
         buffer = f.read(bytesize)
         (l_value, ) = struct.unpack(longlongformat, buffer)
         hash += l_value
         hash = hash & 0xFFFFFFFFFFFFFFFF

      f.close()
      return "%016x" % hash

   def get_from_data_or_none(self, data, key):
      if data:
         status = data.get('status').split()[0]
         return data.get(key) if status == '200' else None

   def search_in_a_thread(self):
      self._thread_finished = False
      self._thread_error = None
      ecore.Timer(0.1, self.check_search_done)
      threading.Thread(target=self.perform_search).start()

   def perform_login(self):
      try:
         data = self.xmlrpc.LogIn(self.oso_user, self.oso_pass,
                                  self.langs2[0], self.USER_AGENT)
         assert data.get('status').split()[0] == '200'
         self.token = self.get_from_data_or_none(data, 'token')
      except:
         self._thread_error = _('Login failed')

   def perform_search(self):
      if self.token is None:
         self.perform_login()

      if self.token is None or self.hash is None:
         self._thread_finished = True
         return

      try:
         data = self.xmlrpc.SearchSubtitles(self.token, [{
                                       'sublanguageid': ','.join(self.langs3),
                                       'moviehash': self.hash,
                                       'moviebytesize': self.size }])
      except:
         self._thread_error = _('Search failed')
      else:
         data = self.get_from_data_or_none(data, 'data')
         if data:
            for sub in data:
               if sub['SubFormat'] != 'srt': continue
               if 'SubBad' in sub and sub['SubBad'] != '0': continue
               for key in ('SubDownloadsCnt', 'SubRating'):
                  if key in sub and sub[key]:
                     sub[key] = float(sub[key])
               self.results.append(sub)

      self._thread_finished = True

   def check_search_done(self):
      if self._thread_finished == False:
         return ecore.ECORE_CALLBACK_RENEW

      self.dialog.delete()
      if self._thread_error:
         EmcDialog(style='error', title='Opensubtitles.org',
                   text=self._thread_error)
      elif not self.results:
         EmcDialog(style='info', title='Opensubtitles.org',
            text=_('No results found for languages: %s') % ' '.join(self.langs3))
      else:
         self.build_result_dialog()

      return ecore.ECORE_CALLBACK_CANCEL

   def build_wait_dialog(self, title):
      self.dialog = EmcDialog(style='minimal', spinner=True, title=title,
                              content=gui.load_image('osdo_logo.png'))

   def build_result_dialog(self):
      txt = '%s<br>Size: %s<br>Hash: %s' % (self.path, self.size, self.hash)
      self.dialog = EmcDialog(title='Opensubtitles.org', style='list',
                              done_cb=self.download_in_a_thread)
      self.dialog.button_add(_('Download'), self.download_in_a_thread,
                             icon='icon/download')

      for sub in sorted(self.results, reverse=True,
               key=itemgetter('LanguageName', 'SubRating', 'SubDownloadsCnt')):
         txt = '[%s] %s, from user: %s, rating: %.1f, downloads: %.0f' % \
               (sub['SubFormat'].upper(), sub['LanguageName'],
                sub['UserNickName'] or _('Unknown'), sub['SubRating'],
                sub['SubDownloadsCnt'])
         item = self.dialog.list_item_append(txt, 'icon/subs')
         item.data['sub'] = sub

   def download_in_a_thread(self, btn):
      item = self.dialog.list_item_selected_get()
      sub = item.data['sub']

      self.dialog.delete()
      self.build_wait_dialog(_('Downloading subtitles'))

      self._thread_finished = False
      self._thread_error = None
      ecore.Timer(0.1, self.check_download_done)
      threading.Thread(target=self.perform_download, args=(sub,)).start()

   def perform_download(self, sub):
      try:
         res = self.xmlrpc.DownloadSubtitles(self.token,
                                             [ sub['IDSubtitleFile'] ],
                                             { 'subencoding':'utf8' } )
         data = res['data'][0]['data']
      except:
         self._thread_error = _('Download failed')
         self._thread_finished = True
         return

      try:
         text = zlib.decompress(base64.b64decode(data), 47)
         md5 = utils.md5(self.path)
         fname = '%s_%s_001.%s' % (md5, sub['ISO639'], sub['SubFormat'])
         full_path = os.path.join(utils.user_conf_dir, 'subtitles', fname)
         full_path = utils.ensure_file_not_exists(full_path)

         with codecs.open(full_path, 'w', 'utf8') as f:
            f.write(text.decode('utf8'))

         self._downloaded_path = full_path
      except:
         self._thread_error = _('Decode failed')

      self._thread_finished = True

   def check_download_done(self):
      if self._thread_finished == False:
         return ecore.ECORE_CALLBACK_RENEW

      self.dialog.delete()
      if self._thread_error:
         EmcDialog(style='error', title='Opensubtitles.org',
                   text=self._thread_error)
      else:
         _subtitles.avail_files.append(self._downloaded_path)
         _subtitles.file_set(self._downloaded_path)
      
      return ecore.ECORE_CALLBACK_CANCEL
