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

from efl import evas, ecore, edje, elementary, emotion

from epymc import utils, ini, gui, input_events, events
from epymc.gui import EmcDialog, EmcButton, EmcMenu, DownloadManager, EmcNotify
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
_emotion = None
_buttons = list()
_buffer_dialog = None
_video_visible = False
_controls_visible = False
_minipos_visible = False
_last_focused_obj = None # used to steal/restore the focus on show/hide
_update_timer = None # used to update the controls, minipos and buffer dialog
_minipos_timer = None # used to hide the minipos after some secs
_subs_timer = None # used to update the subtitles (always on)
_onair_url = None
_onair_title = None
_play_db = None # key: url  data: {'started': 14, 'finished': 0, 'stop_at': 0 }
_play_pause_btn = None
_subtitles = None # Subtitle class instance
_subs_notify = None # EmcNotify for subtitles delay changes


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


class Playlist(object):
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

   def clear(self):
      del self.items[:]

# Create the single instance of the Playlist class (everyone must use this one)
playlist = Playlist()


### API ###
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
def play_url(url, only_audio=False, start_from=None):
   global _onair_url, _onair_title

   # must be a string not unicode, otherwise it cannot be hashed
   url = str(url)
   
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
      _play_real()

def _resume_yes_cb(dia):
   dia.delete()
   _play_real(start_from=dia.data_get())

def _resume_no_cb(dia):
   dia.delete()
   _play_real()

def _play_real(start_from=None, only_audio=False):
   global _subtitles, _subs_timer

   # init emotion and the gui (if needed)
   if not _emotion and not _init_emotion():
      return

   if not _buttons:
      _init_mediaplayer_gui()

   url = _onair_url
   # Do not pass "file://" to emotion. Vlc has a bug somewhere that prevent
   # files with special chars in them to play (the bug don't appear if no
   # "file://" is given. The bug can be seen also using normal vlc from
   # the command line.
   _emotion.file_set(url[7:] if url.startswith('file://') else url)

   # setup the emotion object
   _emotion.position = start_from or 0
   if _emotion.play == False:
      volume_set(_volume)
      volume_mute_set(_volume_muted)
      _emotion.audio_mute = _volume_muted
      _emotion.play = True

   if not only_audio:
      # show the video player object
      video_player_show()

      # keep the counts of played/finished urls
      if _play_db.id_exists(url):
         counts = _play_db.get_data(url)
         counts['started'] += 1
         _play_db.set_data(url, counts)
      else:
         counts = { 'started': 0, 'finished': 0, 'stop_at': 0 }
         _play_db.set_data(url, counts)

      # try to load subtitles (only for local files)
      if url.startswith('file://'):
         _subtitles = Subtitles(url)
         _subs_timer = ecore.Timer(0.2, _update_subs_timer_cb)

def play_counts_get(url):
   try:
      return _play_db.get_data(url)
   except:
      return { 'started': 0,   # num times started
               'finished': 0,  # num times finished
               'stop_at': 0 }  # last play pos

def stop():
   global _emotion, _onair_url, _onair_title, _subtitles, _subs_timer, \
          _buffer_dialog

   DBG('Stop()')

   # clear the subtitles instance
   if _subtitles:
      _subtitles.delete()
      _subtitles = None
   if _subs_timer:
      _subs_timer.delete()
      _subs_timer = None

   if _emotion is not None:
      # update play counts
      counts = play_counts_get(_onair_url)
      if _emotion.position >= _emotion.play_length - 5 or _emotion.position == 0.0: # vlc set the pos at zero when finished :/
         counts['finished'] += 1
         counts['stop_at'] = 0
      else:
         counts['stop_at'] = _emotion.position
      _play_db.set_data(_onair_url, counts)

      # delete the emotion object
      _emotion.play = False
      _emotion.position = 0.0
   
      _emotion.delete()
      del _emotion
      _emotion = None

   # delete the buffering dialog if visible
   if _buffer_dialog is not None:
      _buffer_dialog.delete()
      _buffer_dialog = None

   events.event_emit('PLAYBACK_FINISHED')
   _onair_url = None
   _onair_title = None

def pause():
   if _emotion is None: return
   _emotion.play = False
   _play_pause_btn.icon_set('icon/play')
   gui.signal_emit('minipos,pause,set')
   minipos_show() # TODO move this inside minipos (listening to PLAYBACK_PAUSED)
   events.event_emit('PLAYBACK_PAUSED')

def unpause():
   if _emotion is None: return
   _emotion.play = True
   _play_pause_btn.icon_set('icon/pause')
   gui.signal_emit('minipos,play,set')
   minipos_show() # TODO move this inside minipos (listening to PLAYBACK_UNPAUSED)
   events.event_emit('PLAYBACK_UNPAUSED')

def pause_toggle():
   if _emotion is None: return
   pause() if _emotion.play is True else unpause()

def play_state_get():
   """ 'Stopped', 'Paused' or 'Playing' (as per mpris spec, do not change!) """
   if _emotion is None:
      return 'Stopped'
   if _emotion.play:
      return 'Playing'
   return 'Paused'

def forward():
   seek(+10)

def backward():
   seek(-10)

def fforward():
   seek(+60)

def fbackward():
   seek(-60)

def seek(offset):
   """ offset in seconds (float) """
   if _emotion is None: return
   newpos = _emotion.position + offset
   position_set(newpos if newpos > 0 else 0)

def seekable_get():
   return _emotion.seekable if _emotion is not None else False

def position_set(pos):
   """ pos in seconds (float) """
   if _emotion is None: return
   _emotion.position = pos
   events.event_emit('PLAYBACK_SEEKED')
   # emotion need some loop to update the position, as minipos_show() call
   # slider_update(), we need a bit delay to show the updated position.
   if _video_visible: ecore.Timer(0.05, lambda: minipos_show())

def position_get():
   """ get position in seconds (float) from the start """
   if _emotion is None: return
   return _emotion.position

def volume_set(vol):
   """ between 0 and 100 """
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

def volume_mute_get():
   return _volume_muted

def volume_mute_toggle():
   volume_mute_set(not _volume_muted)

def subs_delay_more():
   subs_delay_apply(+100)

def subs_delay_less():
   subs_delay_apply(-100)

def subs_delay_zero():
   subs_delay_apply(0)

def subs_delay_apply(diff):
   if _subtitles is not None:
      if diff == 0:
         _subtitles.delay = 0
      else:
         _subtitles.delay += diff
      LOG('Subs delay: %d ms' % _subtitles.delay)

### gui API ###
def video_player_show():
   global _video_visible, _update_timer, _last_focused_obj

   _last_focused_obj = gui.win.focused_object
   if _last_focused_obj:
      _last_focused_obj.focus = False
   _play_pause_btn.focus = True

   gui.signal_emit('videoplayer,show')
   _video_visible = True
   input_events.listener_promote('mediaplayer')
   if _update_timer is not None:
      update_timer.delete()
   _update_timer = ecore.Timer(1.0, _update_timer_cb)

def video_player_hide():
   global _video_visible, _update_timer, _last_focused_obj

   video_controls_hide()
   minipos_hide()
   _video_visible = False
   if _update_timer is not None:
      _update_timer.delete()
      _update_timer = None
   gui.signal_emit('videoplayer,hide')
   if _last_focused_obj:
      _last_focused_obj.focus = True

def video_controls_show():
   global _controls_visible

   minipos_hide()
   gui.signal_emit('videoplayer,controls,show')
   _controls_visible = True
   gui.volume_show()
   _update_slider()

   if gui.win.focused_object is None:
      _play_pause_btn.focus = True

def video_controls_hide():
   global _controls_visible

   gui.signal_emit('videoplayer,controls,hide')
   _controls_visible = False
   gui.volume_hide()

def video_controls_toggle():   
   video_controls_hide() if _controls_visible else video_controls_show()

def poster_set(poster=None):
   img = gui.load_image(poster or 'dvd_cover_blank.png')
   img.size_hint_align = (0.5, 0.0)
   gui.swallow_set("videoplayer.controls.poster", img)

def title_set(title):
   global _onair_title

   _onair_title = title
   gui.text_set("videoplayer.controls.title", title)

def minipos_show():
   global _minipos_visible, _minipos_timer

   if _controls_visible:
      return

   gui.signal_emit('minipos,show')
   _minipos_visible = True
   _update_slider()

   if _minipos_timer is None:
      _minipos_timer = ecore.Timer(3, _minipos_timer_cb)
   else:
      _minipos_timer.reset()

def minipos_hide():
   global _minipos_visible, _minipos_timer

   gui.signal_emit('minipos,hide')
   _minipos_visible = False
   if _minipos_timer:
      _minipos_timer.delete()
      _minipos_timer = None

def _minipos_timer_cb():
   minipos_hide()
   return ecore.ECORE_CALLBACK_RENEW # as it is yet deleted in minipos_hide()

### internals ###
def _init_emotion():
   global _emotion

   backend = ini.get('mediaplayer', 'backend')
   try:
      _emotion = emotion.Emotion(gui.layout.evas, module_name=backend)
   except:
      EmcDialog(style='error', text=_('Cannot init emotion engine:<br>%s') % backend)
      return False

   gui.swallow_set('videoplayer.video', _emotion)
   _emotion.smooth_scale = True

   # _emotion.on_key_down_add(_cb)
   _emotion.callback_add('frame_resize', _cb_frame_resize)
   _emotion.callback_add('playback_started', _cb_playback_started)
   _emotion.callback_add('playback_finished', _cb_playback_finished)

   # Progress doesn't work, use frame_decode instead...but it's TOOO often
   #  yes, too often and not firing while buffering...Used a timer instead
   # _emotion.on_progress_change_add((lambda v: _update_slider()))
   # _emotion.on_frame_decode_add((lambda v: _update_slider()))

   return True

def _init_mediaplayer_gui():

   #  <<  fast backward
   bt = EmcButton(icon='icon/fbwd', cb=_cb_btn_fbackward)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)

   #  <   backward
   bt = EmcButton(icon='icon/bwd', cb=_cb_btn_backward)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)

   #  stop
   bt = EmcButton(icon='icon/stop', cb=_cb_btn_stop)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)

   #  play/pause
   bt = EmcButton(icon='icon/pause', cb=_cb_btn_play)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)
   # store a reference to the button so we can change the icon later
   global _play_pause_btn
   _play_pause_btn = bt

   #  >   forward
   bt = EmcButton(icon='icon/fwd', cb=_cb_btn_forward)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)
   
   #  >>  fast forward
   bt = EmcButton(icon='icon/ffwd', cb=_cb_btn_fforward)
   gui.box_append('videoplayer.controls.btn_box', bt)
   _buttons.append(bt)

   #  submenu audio
   bt = EmcButton(_('Audio'), cb=_build_audio_menu)
   gui.box_append('videoplayer.controls.btn_box2', bt)
   _buttons.append(bt)

   #  submenu video
   bt = EmcButton(_('Video'), cb=_build_video_menu)
   gui.box_append('videoplayer.controls.btn_box2', bt)
   _buttons.append(bt)

   #  submenu subtitles
   bt = EmcButton(_('Subtitles'), cb=_build_subtitles_menu)
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
   gui.signal_cb_add('mouse,down,1', 'videoplayer.events',
                     lambda a,s,d: video_controls_toggle())
   gui.signal_cb_add('mouse,down,2', 'videoplayer.events',
                     lambda a,s,d: gui.fullscreen_toggle())

   # click the volume icon to toggle mute
   gui.signal_cb_add('emc,mute,toggle', '',
                     lambda a,s,d: volume_mute_toggle())

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
      _buffer_dialog = EmcDialog(title=_('Buffering'), style='buffering',
                                 canc_cb=_dialog_canc_cb)
      _emotion.play = False

   _update_slider()

   # keep the screensaver out while playing videos
   if _emotion.play == _video_visible == True:
      events.event_emit('KEEP_ALIVE')

   return ecore.ECORE_CALLBACK_RENEW

def _update_subs_timer_cb():
   if _emotion and _subtitles:
      _subtitles.update(_emotion.position)
   return ecore.ECORE_CALLBACK_RENEW

def _update_slider():
   if _emotion is None:
      return

   pos = _emotion.position
   len = _emotion.play_length

   lh = int(len / 3600)
   lm = int(len / 60) % 60
   ls = int(len % 60)

   ph = int(pos / 3600)
   pm = int(pos / 60) % 60
   ps = int(pos % 60)

   if _controls_visible:
      if len > 0:
         gui.slider_val_set('videoplayer.controls.slider:dragable1', pos / len)
      gui.text_set('videoplayer.controls.position', '%i:%02i:%02i' % (ph,pm,ps))
      gui.text_set('videoplayer.controls.length', '%i:%02i:%02i' % (lh,lm,ls))

   if _minipos_visible:
      if len > 0:
         gui.slider_val_set('minipos.slider:dragable1', pos / len)
      gui.text_set('minipos.position', '%i:%02i:%02i' % (ph,pm,ps))
      gui.text_set('minipos.length', '%i:%02i:%02i' % (lh,lm,ls))

def _subtitles_delay_notify():
   global _subs_notify

   txt = '<title>%s</><br>%s' % ( _('Subtitles'),
         _('Delay: %d ms') % _subtitles.delay)
   if _subs_notify is None:
      _subs_notify = EmcNotify(text=txt, icon='icon/subs', hidein=2,
                              close_cb=_subtitles_delay_notify_cb)
   else:
      _subs_notify.text_set(txt)
      _subs_notify.hidein(2)

def _subtitles_delay_notify_cb():
   global _subs_notify
   _subs_notify = None

# emotion obj callbacks
def _cb_playback_started(vid):
   events.event_emit('PLAYBACK_STARTED')

def _cb_playback_finished(vid):
   video_player_hide()
   gui.volume_hide()
   stop()
   playlist.play_next()

def _cb_frame_resize(vid):
   (w, h) = vid.image_size
   edje.extern_object_aspect_set(vid, edje.EDJE_ASPECT_CONTROL_BOTH, w, h)

# mediaplayer buttons cb
def _cb_btn_play(btn):
   pause_toggle()

def _cb_btn_stop(btn):
   video_player_hide()
   stop()

def _cb_btn_forward(btn):
   forward()

def _cb_btn_backward(btn):
   backward()

def _cb_btn_fforward(btn):
   fforward()

def _cb_btn_fbackward(btn):
   fbackward()

# audio menu
def _build_audio_menu(btn):
   menu = EmcMenu(relto=btn, close_on=('UP',))

   # audio channels
   trk_cnt = _emotion.audio_channel_count()
   current = _emotion.audio_channel
   for n in range(trk_cnt):
      name = _emotion.audio_channel_name_get(n)
      if name:
         name = _('Audio track: %s') % name
      else:
         name = _('Audio track #%d') % (n + 1)
      icon = 'item_sel' if n == current else None
      item = menu.item_add(None, name, icon, _cb_menu_audio_track, n)

   # mute / unmute
   menu.item_separator_add()
   if volume_mute_get():
      menu.item_add(None, _('Unmute'), 'volume',
                    lambda m,i: volume_mute_set(False))
   else:
      menu.item_add(None, _('Mute'), 'mute',
                    lambda m,i: volume_mute_set(True))

def _cb_menu_audio_track(menu, item, track_num):
   print("TODO: add support in emotion/gstreamer for this")
   print("Change to audio track #" + str(track_num))
   _emotion.audio_channel_set(track_num)

# video menu
def _build_video_menu(btn):
   menu = EmcMenu(relto=btn, close_on=('UP',))

   # video channels
   trk_cnt = _emotion.video_channel_count()
   current = _emotion.video_channel
   for n in range(trk_cnt):
      name = _emotion.video_channel_name_get(n)
      if name:
         name = _('Video track: %s') % name
      else:
         name = _('Video track #%d') % (n + 1)
      icon = 'item_sel' if n == current else None
      item = menu.item_add(None, name, icon, _cb_menu_video_track, n)

   # download
   menu.item_separator_add()
   it = menu.item_add(None, _('Download video'), None, _cb_menu_download)
   if _onair_url.startswith('file://'):
      it.disabled = True

def _cb_menu_video_track(menu, item, track_num):
   print("TODO: add support in emotion/gstreamer for this")
   print("Change to video track #" + str(track_num))
   _emotion.video_channel_set(track_num)

def _cb_menu_download(menu, item):
   DownloadManager().queue_download(_onair_url, _onair_title)

# subtitles menu
def _build_subtitles_menu(btn):
   menu = EmcMenu(relto=btn, close_on=('UP',))

   if not _onair_url.startswith('file://'):
      # no subs for online videos
      it = menu.item_add(None, _('No subtitles'))
      it.disabled = True
      return

   menu.item_add(None, _('Delay: %d ms') % _subtitles.delay,
                 None, _cb_menu_subs_delay)
   menu.item_separator_add()

   menu.item_add(None, _('No subtitles'),
                 None if _subtitles.current_file else 'item_sel',
                 _cb_menu_subs_track, None)
   for sub in _subtitles.search_subs():
      if sub.startswith(utils.user_conf_dir):
         name = os.path.basename(sub)[33:]
      else:
         name = os.path.basename(sub)
      menu.item_add(None, name,
                    'item_sel' if sub == _subtitles.current_file else None,
                    _cb_menu_subs_track, sub)

   menu.item_separator_add()
   menu.item_add(None, _('Download subtitles'), None, _cb_menu_subs_download)

def _cb_menu_subs_delay(menu, item):
   dia = EmcDialog(title=_('Subtitles delay'), style='minimal',
                   text=_('Delay: %d ms') % _subtitles.delay)
   dia.button_add(_('+100 ms'), _cb_dia_subs_delay, (dia, +100))
   dia.button_add(_('Reset'), _cb_dia_subs_delay, (dia, 0))
   dia.button_add(_('-100 ms'), _cb_dia_subs_delay, (dia, -100))

def _cb_dia_subs_delay(btn, data):
   dia, offset = data
   subs_delay_apply(offset)
   dia.text_set(_('Delay: %d ms') % _subtitles.delay)

def _cb_menu_subs_track(menu, item, sub_file):
   _subtitles.file_set(sub_file)

def _cb_menu_subs_download(menu, item):
   Opensubtitles(_onair_url, _cb_subs_download_done)

def _cb_subs_download_done(dest_file):
   _subtitles.file_set(dest_file)

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

   elif event == 'PLAYLIST_NEXT':
      playlist.play_next()
      return input_events.EVENT_BLOCK

   elif event == 'PLAYLIST_PREV':
      playlist.play_prev()
      return input_events.EVENT_BLOCK

   elif event == 'SUBS_DELAY_MORE':
      if _subtitles:
         subs_delay_more()
         _subtitles_delay_notify()
      return input_events.EVENT_BLOCK

   elif event == 'SUBS_DELAY_LESS':
      if _subtitles:
         subs_delay_less()
         _subtitles_delay_notify()
      return input_events.EVENT_BLOCK

   elif event == 'SUBS_DELAY_ZERO':
      if _subtitles:
         subs_delay_zero()
         _subtitles_delay_notify()
      return input_events.EVENT_BLOCK


   if not _video_visible:
      return input_events.EVENT_CONTINUE


   if event == 'EXIT':
      stop()
      video_player_hide()
      gui.volume_hide()
      return input_events.EVENT_BLOCK
   elif event == 'UP':
      volume_set(_volume + 5)
      events.event_emit('VOLUME_CHANGED')
      return input_events.EVENT_BLOCK
   elif event == 'DOWN':
      volume_set(_volume - 5)
      events.event_emit('VOLUME_CHANGED')
      return input_events.EVENT_BLOCK


   if _controls_visible:
      if event == 'BACK':
         video_controls_hide()
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

   return input_events.EVENT_CONTINUE

