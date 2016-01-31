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

from efl import evas, ecore, edje, emotion, elementary as elm

from epymc import utils, ini, gui, input_events, events
from epymc.gui import EmcDialog, EmcButton, EmcMenu, DownloadManager, \
   EmcNotify, EmcImage
from epymc.sdb import EmcDatabase
from epymc.subtitles import Subtitles, Opensubtitles


def LOG(msg):
   print('MEDIAPLAYER: %s' % msg)

def DBG(msg):
   print('MEDIAPLAYER: %s' % msg)
   pass


video_extensions = ['.avi','.mpg','.mpeg','.mpe','.ogv','.mkv','.divx','.xvid',
                    '.mp4','.wmv','.flv','.f4v','.mov','.m4v','.m2v','.mp4v',
                    '.mpeg4','.dv','.rv','.webm','.vid','.h264','.rm']
audio_extensions = ['.mp3','.ogg','.oga','.flac','.m4a','.wav']

_volume = 0
_volume_muted = False
_player = None # EmcVideoPlayer or EmcAudioPlayer instance, or None
_onair_url = None
_onair_title = None
_onair_poster = None
_play_db = None # key: url  data: {'started': 14, 'finished': 0, 'stop_at': 0 }



class PlaylistItem(object):
   """ You can pass the metadata right now (using the metadata param),
       or provide a callback (metadata_cb) to be called when the metadata are
       really needed.
       Args:
         url: the url of the item (mandatory)
         only_audio: set to False if you want the video player to show up
         metadata: a dict with the metadata for this item. Supported names:
            audio: artist, album, tracknumber
            video: ??
            both : url, title, length (seconds), poster
         metadata_cb: metadata can be requested later, when really needed,
            using this callback. Signature:
               callback(PlaylistItem) -> metadata_dict
   """
   def __init__(self, url, only_audio=True, metadata=None, metadata_cb=None):
      self.url = url
      self.only_audio = only_audio
      self._metadata = metadata
      self._metadata_cb = metadata_cb

   @property
   def metadata(self):
      if self._metadata is None and callable(self._metadata_cb):
         self._metadata = self._metadata_cb(self)
      return self._metadata

   def __str__(self):
      return '<PlaylistItem: %s>' % self.url

   def play(self):
      playlist.play_item(self)


class Playlist(utils.Singleton):
   def __init__(self):
      self.items = []
      self.cur_idx = -1
      self.onair_item = None

   def __str__(self):
      return '<Playlist: %d items, current: %d>' % \
             (len(self.items), self.cur_idx)

   def __len__(self):
      return len(self.items)

   def append(self, *args, **kargs):
      item = PlaylistItem(*args, **kargs)
      self.items.append(item)
      if self.onair_item is None:
         self.play_next()
      events.event_emit('PLAYLIST_CHANGED')

   def play_next(self):
      self.play_move(+1)

   def play_prev(self):
      self.play_move(-1)

   def play_move(self, offset):
      self.cur_idx += offset

      # start reached
      if self.cur_idx < 0:
         self.cur_idx = 0

      # end reached
      if self.cur_idx >= len(self.items):
         self.cur_idx = 0

      # play the new item
      self.onair_item = self.items[self.cur_idx]
      play_url(self.onair_item.url, only_audio=self.onair_item.only_audio)

   def play_item(self, item):
      self.cur_idx = self.items.index(item)
      self.onair_item = item
      play_url(self.onair_item.url, only_audio=self.onair_item.only_audio)

   def clear(self):
      del self.items[:]
      self.cur_idx = -1
      self.onair_item = None
      events.event_emit('PLAYLIST_CHANGED')

# Create the single instance of the Playlist class (everyone must use this one)
playlist = Playlist()


### module API ###
def init():
   global _volume
   global _play_db
   global video_extensions
   global audio_extensions

   # default config values
   ini.add_section('mediaplayer')
   ini.add_section('subtitles')
   if not ini.has_option('mediaplayer', 'volume'):
      ini.set('mediaplayer', 'volume', '75')
   if not ini.has_option('mediaplayer', 'backend'):
      ini.set('mediaplayer', 'backend', 'gstreamer1')
   if not ini.has_option('mediaplayer', 'resume_from_last_pos'):
      ini.set('mediaplayer', 'resume_from_last_pos', '0')
   if not ini.has_option('mediaplayer', 'video_extensions'):
      ini.set('mediaplayer', 'video_extensions', '')
   if not ini.has_option('mediaplayer', 'audio_extensions'):
      ini.set('mediaplayer', 'audio_extensions', '')

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

   audio_extensions += ini.get_string_list('mediaplayer', 'audio_extensions')
   video_extensions += ini.get_string_list('mediaplayer', 'video_extensions')

   # restore volume from previous session
   _volume = ini.get_int('mediaplayer', 'volume')
   gui.volume_set(_volume / 100.0)

   # simple db to store the count of played files
   _play_db = EmcDatabase('playcount')

   # input events
   input_events.listener_add("mediaplayer", input_event_cb)

   # update volume when mouse drag the volume slider
   def _drag_vol(obj, emission, source):
      (val,val2) = gui.slider_val_get('volume.slider:dragable1')
      volume_set(val * 100.0)
   gui.signal_cb_add('drag', 'volume.slider:dragable1', _drag_vol)

   # click the volume icon to toggle mute
   gui.signal_cb_add('emc,mute,toggle', '',
                     lambda a,s,d: volume_mute_toggle())

def shutdown():
   global _play_db

   input_events.listener_del("mediaplayer")
   del _play_db

### mediaplyer API ###
def play_url(url, only_audio=False, start_from=None):
   global _onair_url, _onair_title, _onair_poster

   # default to 'file://' if not given
   if url.find('://', 2, 15) is -1:
      url = 'file://' + url

   # check url
   if url.startswith('file://') and not os.path.exists(url[7:]):
      text = '<b>%s:</b><br>%s' % (_('File not found'), url)
      EmcDialog(text=text, style='error')
      return

   DBG('play_url: %s' % url)
   _onair_url = url
   _onair_title = None
   _onair_poster = None

   if only_audio:
      _play_real(start_from, only_audio)
      return

   # starting position forced by param
   if start_from != None:
      _play_real(start_from, only_audio)
      return

   # resume_opt: 0=ask, 1=always, 2=never
   resume_opt = ini.get_int('mediaplayer', 'resume_from_last_pos')

   if resume_opt == 2: # never resume
      _play_real(0)
      return

   # resume playback from last position ?
   counts = play_counts_get(url)
   if counts['stop_at'] > 10.0: # don't ask if less then 10 seconds
      pos = counts['stop_at']
      if resume_opt == 1: # always resume
         _play_real(pos)
         return
      # ask if resume or not
      time = '%d:%.2d:%.2d' % \
             (int(pos / 3600), int(pos / 60) % 60, int(pos % 60))
      EmcDialog(style='yesno', title=_('Resume playback'),
                text=_('Continue from %s ?') % (time),
                done_cb=_resume_yes_cb, canc_cb=_resume_no_cb, user_data=pos)
   else:
      _play_real(0)

def _resume_yes_cb(dia):
   dia.delete()
   _play_real(start_from=dia.data_get())

def _resume_no_cb(dia):
   dia.delete()
   _play_real(0)

def _play_real(start_from=None, only_audio=False):
   global _player

   url = _onair_url

   if only_audio:
      if _player is None:
         _player = EmcAudioPlayer(url)
      else:
         _player.url = url
   else:
      _player = EmcVideoPlayer(url)
      _player.position = start_from or 0

      # keep the counts of played/finished urls
      if _play_db.id_exists(url):
         counts = _play_db.get_data(url)
         counts['started'] += 1
         _play_db.set_data(url, counts)
      else:
         counts = { 'started': 0, 'finished': 0, 'stop_at': 0 }
         _play_db.set_data(url, counts)

def poster_set(poster):
   global _onair_poster

   _onair_poster = poster
   if _player: _player.poster_set(poster)

def title_set(title):
   global _onair_title

   _onair_title = title
   if _player: _player.title_set(title)

def play_counts_get(url):
   try:
      return _play_db.get_data(url)
   except:
      return { 'started': 0,   # num times started
               'finished': 0,  # num times finished
               'stop_at': 0 }  # last play pos

def stop():
   global _player, _onair_url, _onair_title

   DBG('Stop()')

   if isinstance(_player, EmcVideoPlayer):
      # update play counts
      counts = play_counts_get(_onair_url)
      if _player.position >= _player.play_length - 5 or _player.position == 0.0: # vlc set the pos at zero when finished :/
         counts['finished'] += 1
         counts['stop_at'] = 0
      else:
         counts['stop_at'] = _player.position
      _play_db.set_data(_onair_url, counts)

   # delete the player
   if _player:
      _player.delete()
      _player = None

   playlist.clear()
   _onair_url = None
   _onair_title = None

def pause():
   if _player: _player.pause()

def unpause():
   if _player: _player.unpause()

def pause_toggle():
   if _player: _player.pause_toggle()

def play_state_get():
   """ 'Stopped', 'Paused' or 'Playing' (as per mpris spec, do not change!) """
   if _player is None:
      return 'Stopped'
   if _player.paused:
      return 'Paused'
   return 'Playing'

def seek(offset):
   """ offset in seconds (float) """
   if _player: _player.seek(offset)

def forward():
   if _player: _player.forward()

def backward():
   if _player: _player.backward()

def fforward():
   if _player: _player.fforward()

def fbackward():
   if _player: _player.fbackward()

def seekable_get():
   return _player.seekable if _player else False

def position_set(pos):
   """ pos in seconds (float) """
   if _player: _player.position = pos

def position_get():
   """ get position in seconds (float) from the start """
   if _player: return _player.position

def volume_set(vol):
   """ between 0 and 100 """
   global _volume

   _volume = max(0, min(int(vol), 100))
   ini.set('mediaplayer', 'volume', _volume)
   gui.volume_set(_volume / 100.0)
   events.event_emit('VOLUME_CHANGED')

def volume_get():
   return _volume

def volume_mute_set(mute):
   global _volume_muted

   _volume_muted = bool(mute)
   gui.signal_emit('volume,mute,' + ('on' if mute else 'off'))
   events.event_emit('VOLUME_CHANGED')

def volume_mute_get():
   return _volume_muted

def volume_mute_toggle():
   volume_mute_set(not _volume_muted)

### input events ###
def input_event_cb(event):
   if event == 'VOLUME_UP':
      volume_set(_volume + 5)
   elif event == 'VOLUME_DOWN':
      volume_set(_volume - 5)
   elif event == 'VOLUME_MUTE':
      volume_mute_toggle()
   else:
      return input_events.EVENT_CONTINUE
   return input_events.EVENT_BLOCK


###############################################################################
class EmcPlayerBase(object):
   def __init__(self):
      self._url = None

      ### init the emotion object
      backend = ini.get('mediaplayer', 'backend')
      # TODO fix better this 
      try:
         self._emotion = emotion.Emotion(gui.layout.evas, module_name=backend,
                                   keep_aspect=emotion.EMOTION_ASPECT_KEEP_BOTH)
      except:
         EmcDialog(style='error', text=_('Cannot init emotion engine:<br>%s') % backend)
         return

      self._emotion.smooth_scale = True
      self._emotion.callback_add('playback_started', self._playback_started_cb)
      self._emotion.callback_add('playback_finished', self._playback_finished_cb)

      ### listen to input and generic events
      input_events.listener_add('EmcPlayerBase', self._base_input_events_cb)
      events.listener_add('EmcPlayerBase', self._base_events_cb)

   def delete(self):
      input_events.listener_del('EmcPlayerBase')
      events.listener_del('EmcPlayerBase')
      self._emotion.delete()

   @property
   def url(self):
      return self._url

   @url.setter
   def url(self, url):
      # default to 'file://' if not given
      if url.find('://', 2, 15) == -1:
         url = 'file://' + url
      self._url = url

      # Do not pass "file://" to emotion. Vlc has a bug somewhere that prevent
      # files with special chars in them to play (the bug don't appear if no
      # "file://" is given. The bug can be seen also using normal vlc from
      # the command line.
      self._emotion.file_set(url[7:] if url.startswith('file://') else url)
      self._emotion.play = True
      self._emotion.audio_volume = volume_get() / 100.0
      self._emotion.audio_mute = volume_mute_get()

   @property
   def seekable(self):
      return self._emotion.seekable

   @property
   def play_length(self):
      return self._emotion.play_length

   @property
   def position(self):
      """ the playback position in seconds (float) from the start """
      return self._emotion.position

   @position.setter
   def position(self, pos):
      self._emotion.position = pos
      events.event_emit('PLAYBACK_SEEKED')

   @property
   def position_percent(self):
      """ the playback position in the range 0.0 -> 1.0 """
      pos, len = self._emotion.position, self._emotion.play_length
      return (pos / len) if len > 0 else 0.0

   @position_percent.setter
   def position_percent(self, val):
      self.position = self._emotion.play_length * val

   def seek(self, offset):
      """ offset in seconds (float) """
      newpos = self._emotion.position + offset
      self.position = max(0.0, newpos)

   def forward(self):
      self.seek(+10)

   def backward(self):
      self.seek(-10)

   def fforward(self):
      self.seek(+60)

   def fbackward(self):
      self.seek(-60)

   @property
   def paused(self):
      return not self._emotion.play

   def pause(self):
      self._emotion.play = False
      events.event_emit('PLAYBACK_PAUSED')

   def unpause(self):
      self._emotion.play = True
      events.event_emit('PLAYBACK_UNPAUSED')

   def pause_toggle(self):
      self.unpause() if self.paused else self.pause()

   # emotion obj callbacks
   def _playback_started_cb(self, vid):
      events.event_emit('PLAYBACK_STARTED')

   def _playback_finished_cb(self, vid):
      events.event_emit('PLAYBACK_FINISHED')

   ### events
   def _base_input_events_cb(self, event):
      if event == 'PLAY':
         self.unpause()
         return input_events.EVENT_BLOCK

      elif event == 'TOGGLE_PAUSE':
         self.pause_toggle()
         return input_events.EVENT_BLOCK

      elif event == 'PAUSE':
         self.pause()
         return input_events.EVENT_BLOCK

      elif event == 'STOP':
         stop()
         return input_events.EVENT_BLOCK

      elif event == 'FORWARD':
         self.forward()
         return input_events.EVENT_BLOCK

      elif event == 'BACKWARD':
         self.backward()
         return input_events.EVENT_BLOCK

      elif event == 'FAST_FORWARD':
         self.fforward()
         return input_events.EVENT_BLOCK

      elif event == 'FAST_BACKWARD':
         self.fbackward()
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

   def _base_events_cb(self, event):
      if event == 'VOLUME_CHANGED':
         self._emotion.audio_volume = volume_get() / 100.0
         self._emotion.audio_mute = volume_mute_get()


###############################################################################
class EmcAudioPlayer(elm.Layout, EmcPlayerBase):
   def __init__(self, url=None):

      ### init the layout
      elm.Layout.__init__(self, gui.layout, focus_allow=False,
                          file=(gui.theme_file, 'emc/audioplayer/default'))
      # self.callback_focused_add(self._focused_cb)
      # self.callback_unfocused_add(self._unfocused_cb)
      
      # update emotion position when mouse drag the progress slider
      self.signal_callback_add('drag', 'pos.slider:dragable1', self._pos_dragged_cb)

      ### init the base player class
      EmcPlayerBase.__init__(self)
      self.url = url

      ### control buttons
      buttons = [
         ('icon/prev', 'PLAYLIST_PREV'),
         ('icon/next', 'PLAYLIST_NEXT'),
         ('icon/pause', 'PAUSE'),
         ('icon/play', 'PLAY'),
         ('icon/stop', 'STOP'),
      ]
      def buttons_cb(b, event):
         input_events.event_emit(event)
      for icon, event in buttons:
         bt = EmcButton(icon=icon,cb=buttons_cb, cb_data=event)
         bt.callback_focused_add(self._focused_cb)
         bt.callback_unfocused_add(self._unfocused_cb)
         self.box_append('buttons.box', bt)

      ### playlist genlist
      self._itc = elm.GenlistItemClass(item_style='default',
                                       text_get_func=self._gl_text_get)
      self._gl = elm.Genlist(self, style='playlist', homogeneous=True,
                             mode=elm.ELM_LIST_COMPRESS)
      self._gl.callback_focused_add(self._focused_cb)
      self._gl.callback_unfocused_add(self._unfocused_cb)
      self._gl.callback_activated_add(self._genlist_item_activated_cb)
      self.content_set('playlist.swallow', self._gl)

      self._gl_populate()

      ### swallow ourself in the main layout and show
      gui.swallow_set('audioplayer.swallow', self)
      gui.signal_emit('audioplayer,show')

      ### listen to input and generic events
      input_events.listener_add('EmcAudioPlayer', self._input_events_cb)
      events.listener_add('EmcAudioPlayer', self._events_cb)

      ### timer to update the slider
      self._slider_timer = ecore.Timer(1.0, self._update_timer)

   def delete(self):
      self._slider_timer.delete()
      input_events.listener_del('EmcAudioPlayer')
      events.listener_del('EmcAudioPlayer')
      EmcPlayerBase.delete(self)
      elm.Layout.delete(self)

   def _focused_cb(self, obj):
      gui.signal_emit('audioplayer,expand')

   def _unfocused_cb(self, obj):
      if gui.win.focus == True: # do not contract when mouse goes out of win
         gui.signal_emit('audioplayer,contract')

   def _gl_populate(self):
      self._gl.clear()
      for item in playlist.items:
         # print(item.metadata)
         it = self._gl.item_append(self._itc, item)
         if item == playlist.onair_item:
            self._gl.focus_allow = False
            it.selected = True
            it.show()
            self._gl.focus_allow = True

   ## genlist item class
   def _gl_text_get(self, obj, part, pl_item):
      metadata = pl_item.metadata
      if part == 'elm.text.tracknum':
         return str(metadata.get('tracknumber'))
      if part == 'elm.text.title':
         return metadata.get('title')
      if part == 'elm.text.artist':
         return metadata.get('artist')
      if part == 'elm.text.len':
         seconds = metadata.get('length')
         if seconds is not None:
            return utils.seconds_to_duration(seconds)

   def _genlist_item_activated_cb(self, gl, it):
      playlist_item = it.data
      playlist_item.play()

   def _update_timer(self, single=False):
      pos = self.position_percent
      self.edje.part_drag_value_set('pos.slider:dragable1', pos, pos)
      return ecore.ECORE_CALLBACK_CANCEL if single else ecore.ECORE_CALLBACK_RENEW

   def _pos_dragged_cb(self, obj, emission, source):
      (val,val2) = self.edje.part_drag_value_get('pos.slider:dragable1')
      self.position_percent = val

   ### input events
   def _input_events_cb(self, event):
      if event == 'OK' and self._gl.focus == True:
         self._genlist_item_activated_cb(self._gl, self._gl.focused_item)
      elif event == 'PLAYLIST_NEXT':
         playlist.play_next()
      elif event == 'PLAYLIST_PREV':
         playlist.play_prev()
      else:
         return input_events.EVENT_CONTINUE
      return input_events.EVENT_BLOCK

   ### generic events
   def _events_cb(self, event):
      if event == 'PLAYBACK_STARTED':
         # update metadata infos
         metadata = playlist.onair_item.metadata
         self.part_text_set('artist.text', metadata.get('artist'))
         self.part_text_set('album.text', metadata.get('album'))
         poster = metadata.get('poster')
         img = EmcImage(poster or 'special/cd/' + metadata.get('album'))
         self.content_set('cover.swallow', img)

         # update selected playlist item
         it = self._gl.nth_item_get(playlist.cur_idx)
         if it:
            self._gl.focus_allow = False
            it.selected = True
            it.show()
            self._gl.focus_allow = True

         # update the slider
         self._update_timer(single=True)

      elif event == 'PLAYBACK_FINISHED':
         playlist.play_next()

      elif event == 'PLAYLIST_CHANGED':
         print("CHANGED")
         self._gl_populate()

      elif event == 'PLAYBACK_SEEKED':
         # emotion need some loop to update the position, so
         # we need a bit delay to show the updated position.
         ecore.Timer(0.05, lambda: self._update_timer(single=True))


###############################################################################
class EmcVideoPlayer(elm.Layout, EmcPlayerBase):
   def __init__(self, url=None):

      self._play_pause_btn = None
      self._update_timer = None
      self._buffer_dialog = None
      self._controls_visible = False
      self._title = None

      self._minipos_visible = False
      self._minipos_timer = None
      
      self._subtitles = None # Subtitle class instance
      self._subs_timer = None # Timer for subtitles update
      self._subs_notify = None # EmcNotify for subtitles delay changes

      ### init the layout
      elm.Layout.__init__(self, gui.layout,
                          file=(gui.theme_file, 'emc/videoplayer/default'))

      # left click on video to show/hide the controls
      self.signal_callback_add('mouse,down,1', 'events.rect',
                               lambda a,s,d: self.controls_toggle())

      # middle click on video to toggle fullscreen
      self.signal_callback_add('mouse,down,2', 'events.rect',
                               lambda a,s,d: gui.fullscreen_toggle())

      # update emotion position when mouse drag the progress slider
      def _drag_prog(obj, emission, source):
         (val,val2) = self.edje.part_drag_value_get('controls.slider:dragable1')
         self.position = self._emotion.play_length * val
      self.signal_callback_add('drag', 'controls.slider:dragable1', _drag_prog)

      ### init the base player class
      EmcPlayerBase.__init__(self)
      self.content_set('video.swallow', self._emotion)
      self.url = url

      ### control buttons
      bt = EmcButton(icon='icon/fbwd', cb=lambda b: self.fbackward())
      self.box_append('controls.btn_box', bt)

      bt = EmcButton(icon='icon/bwd', cb=lambda b: self.backward())
      self.box_append('controls.btn_box', bt)

      bt = EmcButton(icon='icon/stop', cb=lambda b: stop())
      self.box_append('controls.btn_box', bt)

      bt = EmcButton(icon='icon/pause', cb=lambda b: self.pause_toggle())
      self.box_append('controls.btn_box', bt)
      self._play_pause_btn = bt

      bt = EmcButton(icon='icon/fwd', cb=lambda b: self.forward())
      self.box_append('controls.btn_box', bt)
      
      bt = EmcButton(icon='icon/ffwd', cb=lambda b: self.fforward())
      self.box_append('controls.btn_box', bt)

      bt = EmcButton(_('Audio'), cb=self._audio_menu_build)
      self.box_append('controls.btn_box2', bt)

      bt = EmcButton(_('Video'), cb=self._video_menu_build)
      self.box_append('controls.btn_box2', bt)

      bt = EmcButton(_('Subtitles'), cb=self._subs_menu_build)
      self.box_append('controls.btn_box2', bt)
   
      ### swallow ourself in the main layout and show
      gui.swallow_set('videoplayer.swallow', self)
      gui.signal_emit('videoplayer,show')

      ### listen to input and generic events
      input_events.listener_add('EmcVideoPlayer', self._input_events_cb)
      events.listener_add('EmcVideoPlayer', self._events_cb)

      ### start the update timer
      self._update_timer = ecore.Timer(1.0, self._update_timer_cb)

      ### try to load subtitles (only for local files)
      if self.url.startswith('file://'):
         self._subtitles = Subtitles(self.url)
         self._subs_timer = ecore.Timer(0.2, self._update_subs_timer_cb)

      ### set title + poster
      if _onair_title: self.title_set(_onair_title)
      if _onair_poster: self.poster_set(_onair_poster)

   def delete(self):
      input_events.listener_del('EmcVideoPlayer')
      events.listener_del('EmcVideoPlayer')
      if self._update_timer:  self._update_timer.delete()
      if self._buffer_dialog: self._buffer_dialog.delete()
      if self._subtitles:     self._subtitles.delete()
      if self._subs_timer:    self._subs_timer.delete()
      if self._subs_notify:   self._subs_notify.delete()

      self.controls_hide()
      gui.signal_emit('videoplayer,hide')
      gui.signal_cb_add('videoplayer,hide,done', '', self._delete_real)

   def _delete_real(self, obj, sig, src):
      print("DELETE REAL")
      gui.signal_cb_del('videoplayer,hide,done', '', self._delete_real)
      EmcPlayerBase.delete(self)
      elm.Layout.delete(self)

   def title_set(self, title):
      self._title = title
      self.part_text_set("controls.title", title)

   def poster_set(self, poster):
      img = EmcImage(poster or 'image/dvd_cover_blank.png')
      img.size_hint_align = (0.5, 0.0)
      self.content_set("controls.poster", img)

   ### controls
   def controls_show(self):
      self.signal_emit('controls,show', 'emc')
      self._controls_visible = True
      self.minipos_hide()
      self._update_slider()
      gui.volume_show()
      if self.focused_object is None:
         self._play_pause_btn.focus = True

   def controls_hide(self):
      self.signal_emit('controls,hide', 'emc')
      self._controls_visible = False
      gui.volume_hide()

   def controls_toggle(self):
      if self._controls_visible:
         self.controls_hide()
      else:
         self.controls_show()

   ### minipos
   def minipos_show(self):
      if self._controls_visible:
         return

      self.signal_emit('minipos,show', 'emc')
      self._minipos_visible = True
      self._update_slider()

      if self._minipos_timer is None:
         self._minipos_timer = ecore.Timer(3, self._minipos_timer_cb)
      else:
         self._minipos_timer.reset()

   def minipos_hide(self):
      self.signal_emit('minipos,hide', 'emc')
      self._minipos_visible = False
      if self._minipos_timer:
         self._minipos_timer.delete()
         self._minipos_timer = None

   def _minipos_timer_cb(self):
      self.minipos_hide()
      return ecore.ECORE_CALLBACK_RENEW # as it is yet deleted in minipos_hide()

   ### subtitles
   def subs_delay_more(self):
      self.subs_delay_apply(+100)

   def subs_delay_less(self):
      self.subs_delay_apply(-100)

   def subs_delay_zero(self):
      self.subs_delay_apply(0)

   def subs_delay_apply(self, diff):
      if self._subtitles is not None:
         if diff == 0:
            self._subtitles.delay = 0
         else:
            self._subtitles.delay += diff
         LOG('Subs delay: %d ms' % self._subtitles.delay)
   
   def _subtitles_delay_notify(self):
      txt = '<title>%s</><br>%s' % ( _('Subtitles'),
            _('Delay: %d ms') % self._subtitles.delay)
      if self._subs_notify is None:
         self._subs_notify = EmcNotify(text=txt, icon='icon/subs', hidein=2,
                                       close_cb=self._subtitles_delay_notify_cb)
      else:
         self._subs_notify.text_set(txt)
         self._subs_notify.hidein(2)

   def _subtitles_delay_notify_cb(self):
      self._subs_notify = None

   def _update_subs_timer_cb(self):
      if self._subtitles:
         self._subtitles.update(self.position)
      return ecore.ECORE_CALLBACK_RENEW
   
   ### internals
   def _update_slider(self):
      pos = self._emotion.position
      len = self._emotion.play_length

      lh = int(len / 3600)
      lm = int(len / 60) % 60
      ls = int(len % 60)

      ph = int(pos / 3600)
      pm = int(pos / 60) % 60
      ps = int(pos % 60)

      pos_percent = (pos / len) if len > 0 else 0.0

      if self._controls_visible:
         self.edje.part_drag_value_set('controls.slider:dragable1',
                                       pos_percent, pos_percent)
         self.text_set('controls.position', '%i:%02i:%02i' % (ph,pm,ps))
         self.text_set('controls.length', '%i:%02i:%02i' % (lh,lm,ls))

         s = datetime.now().strftime('%H:%M')
         self.text_set('clock', s)

      if self._minipos_visible:
         self.edje.part_drag_value_set('minipos.slider:dragable1',
                                       pos_percent, pos_percent)
         self.text_set('minipos.position', '%i:%02i:%02i' % (ph,pm,ps))
         self.text_set('minipos.length', '%i:%02i:%02i' % (lh,lm,ls))

   def _update_timer_cb(self):
      if self._buffer_dialog is not None:
         self._buffer_dialog.progress_set(self._emotion.buffer_size)
         if self._emotion.buffer_size >= 1.0:
            self._emotion.play = True
            self._buffer_dialog.delete()
            self._buffer_dialog = None

      elif self._emotion.buffer_size < 1.0:
         self._buffer_dialog = EmcDialog(title=_('Buffering'), style='buffering')
         self._emotion.play = False

      self._update_slider()

      # keep the screensaver out while playing videos
      if self._emotion.play == True:
         events.event_emit('KEEP_ALIVE')

      return ecore.ECORE_CALLBACK_RENEW

   ### audio menu
   def _audio_menu_build(self, btn):
      menu = EmcMenu(relto=btn, close_on=('UP',))

      # audio channels
      trk_cnt = self._emotion.audio_channel_count()
      current = self._emotion.audio_channel
      for n in range(trk_cnt):
         name = self._emotion.audio_channel_name_get(n)
         if name:
            name = _('Audio track: %s') % name
         else:
            name = _('Audio track #%d') % (n + 1)
         icon = 'item_sel' if n == current else None
         item = menu.item_add(None, name, icon, self._audio_menu_track_cb, n)

      # mute / unmute
      menu.item_separator_add()
      if volume_mute_get():
         menu.item_add(None, _('Unmute'), 'volume',
                       lambda m,i: volume_mute_set(False))
      else:
         menu.item_add(None, _('Mute'), 'mute',
                       lambda m,i: volume_mute_set(True))

   def _audio_menu_track_cb(self, menu, item, track_num):
      self._emotion.audio_channel_set(track_num)

   ### video menu
   def _video_menu_build(self, btn):
      menu = EmcMenu(relto=btn, close_on=('UP',))

      # video channels
      trk_cnt = self._emotion.video_channel_count()
      current = self._emotion.video_channel
      for n in range(trk_cnt):
         name = self._emotion.video_channel_name_get(n)
         if name:
            name = _('Video track: %s') % name
         else:
            name = _('Video track #%d') % (n + 1)
         icon = 'item_sel' if n == current else None
         item = menu.item_add(None, name, icon, self._video_menu_track_cb, n)

      # download
      menu.item_separator_add()
      it = menu.item_add(None, _('Download video'), None,
                         self._video_menu_download_cb)
      if self.url.startswith('file://'):
         it.disabled = True

   def _video_menu_track_cb(self, menu, item, track_num):
      print("Change to video track #" + str(track_num))
      self._emotion.video_channel_set(track_num)

   def _video_menu_download_cb(self, menu, item):
      DownloadManager().queue_download(self.url, self._title)

   ### subtitles menu
   def _subs_menu_build(self, btn):
      menu = EmcMenu(relto=btn, close_on=('UP',))

      if not self.url.startswith('file://'):
         # no subs for online videos
         it = menu.item_add(None, _('No subtitles'))
         it.disabled = True
         return

      menu.item_add(None, _('Delay: %d ms') % self._subtitles.delay,
                    None, self._subs_menu_delay_cb)
      menu.item_separator_add()

      menu.item_add(None, _('No subtitles'),
                    None if self._subtitles.current_file else 'item_sel',
                    self._subs_menu_track_cb, None)
      for sub in self._subtitles.search_subs():
         if sub.startswith(utils.user_conf_dir):
            name = os.path.basename(sub)[33:]
         else:
            name = os.path.basename(sub)
         menu.item_add(None, name,
                       'item_sel' if sub == self._subtitles.current_file else None,
                       self._subs_menu_track_cb, sub)

      menu.item_separator_add()
      menu.item_add(None, _('Download subtitles'), None, self._subs_menu_download_cb)

   def _subs_menu_delay_cb(self, menu, item):
      dia = EmcDialog(title=_('Subtitles delay'), style='minimal',
                      text=_('Delay: %d ms') % self._subtitles.delay)
      dia.button_add(_('+100 ms'), self._subs_dia_delay_cb, (dia, +100))
      dia.button_add(_('Reset'), self._subs_dia_delay_cb, (dia, 0))
      dia.button_add(_('-100 ms'), self._subs_dia_delay_cb, (dia, -100))

   def _subs_dia_delay_cb(self, btn, data):
      dia, offset = data
      self.subs_delay_apply(offset)
      dia.text_set(_('Delay: %d ms') % self._subtitles.delay)

   def _subs_menu_track_cb(self, menu, item, sub_file):
      self._subtitles.file_set(sub_file)

   def _subs_menu_download_cb(self, menu, item):
      Opensubtitles(self.url, self._subs_download_done)

   def _subs_download_done(self, dest_file):
      self._subtitles.file_set(dest_file)

   ### input events
   def _input_events_cb(self, event):

      if event == 'SUBS_DELAY_MORE':
         if self._subtitles:
            self.subs_delay_more()
            self._subtitles_delay_notify()
         return input_events.EVENT_BLOCK

      elif event == 'SUBS_DELAY_LESS':
         if self._subtitles:
            self.subs_delay_less()
            self._subtitles_delay_notify()
         return input_events.EVENT_BLOCK

      elif event == 'SUBS_DELAY_ZERO':
         if self._subtitles:
            self.subs_delay_zero()
            self._subtitles_delay_notify()
         return input_events.EVENT_BLOCK
         
      if self._controls_visible:
         if event == 'OK':
            pass
         elif event == 'BACK':
            self.controls_hide()
            return input_events.EVENT_BLOCK
         elif event in gui.focus_directions:
            gui.focus_move(event, self)
            return input_events.EVENT_BLOCK

      else:
         if event == 'OK':
            self.controls_show()
            return input_events.EVENT_BLOCK
         elif event == 'BACK':
            stop()
            return input_events.EVENT_BLOCK
         elif event == 'RIGHT':
            self.forward()
            return input_events.EVENT_BLOCK
         elif event == 'LEFT':
            self.backward()
            return input_events.EVENT_BLOCK
         elif event == 'UP':
            input_events.event_emit('VOLUME_UP')
            return input_events.EVENT_BLOCK
         elif event == 'DOWN':
            input_events.event_emit('VOLUME_DOWN')
            return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

   ### generic events
   def _events_cb(self, event):
      if event == 'PLAYBACK_FINISHED':
         stop()
         return
      elif event == 'PLAYBACK_PAUSED':
         self._play_pause_btn.icon_set('icon/play')
         self.signal_emit('minipos,pause,set', 'emc')
      elif event == 'PLAYBACK_UNPAUSED':
         self._play_pause_btn.icon_set('icon/pause')
         self.signal_emit('minipos,play,set', 'emc')
      elif event == 'PLAYBACK_SEEKED':
         # emotion need some loop to update the position, so
         # we need a bit delay to show the updated position.
         ecore.Timer(0.05, lambda: self._update_slider())

      # show minipos on seek/pause/play
      if not self._controls_visible and self.position > 1:
         if event in ('PLAYBACK_PAUSED', 'PLAYBACK_UNPAUSED', 'PLAYBACK_SEEKED'):
            ecore.Timer(0.05, lambda: self.minipos_show())

