#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2016 Davide Andreoli <dave@gurumeditation.it>
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

from collections import namedtuple

from efl import ecore
from efl import evas
from efl import elementary as elm

from epymc.modules import EmcModule
from epymc.mediaplayer import EmcPlayerBase
from epymc import mediaplayer
from epymc import events
from epymc import input_events
from epymc import gui

from .omx_player import OMXPlayer

def DBG(msg):
   print('OMX: %s' % msg)
   # pass


class OmxPlayerModule(EmcModule):
   name = 'mp_omxplayer'
   label = _('Media Player - OMX external player')
   icon = 'icon/remote'
   info = _('Use an external omx_player process to play videos. Only usable '
            'on RaspberryPI, make sure you have omxplayer installed.')

   def __init__(self):
      DBG('Init module')
      # monkey-patch the original EmcPlayer implementation
      self.EmcPlayerBase_ORIG = mediaplayer.EmcPlayerBase
      self.EmcVideoPlayer_ORIG = mediaplayer.EmcVideoPlayer
      self.EmcAudioPlayer_ORIG = mediaplayer.EmcAudioPlayer
      mediaplayer.EmcPlayerBase = EmcPlayerBase_OMX
      mediaplayer.EmcVideoPlayer = EmcVideoPlayer_OMX
      mediaplayer.EmcAudioPlayer = EmcAudioPlayer_OMX

   def __shutdown__(self):
      DBG('Shutdown module')
      # un-monkey-patch
      mediaplayer.EmcPlayerBase = self.EmcPlayerBase_ORIG
      mediaplayer.EmcVideoPlayer = self.EmcVideoPlayer_ORIG
      mediaplayer.EmcAudioPlayer = self.EmcAudioPlayer_ORIG


class EmcPlayerBase_OMX(EmcPlayerBase):
   def __init__(self):
      self._url = None
      self._OMP = None
      self._OMP_sizer_rect = None
      self._OMP_muted = False
      DBG("CUSTOM OMX PLAYER")

      # invisible rect to track the wanted position of the player and
      # mimic the position in the omx_player process
      def _sizer_cb(obj):
         x, y, w, h = obj.geometry
         self._OMP.set_video_pos(x, y, x + w, y + h)
      r = evas.Rectangle(gui.layout.evas, color=(0, 0, 0, 0))
      r.on_resize_add(_sizer_cb)
      self._OMP_sizer_rect = r

      # listen to input and generic events (cb implemented in the base class)
      input_events.listener_add(self.__class__.__name__ + 'Base_OMX',
                                self._base_input_events_cb)
      events.listener_add(self.__class__.__name__ + 'Base_OMX',
                                self._base_events_cb)

   def delete(self):
      DBG("DELETE")
      input_events.listener_del(self.__class__.__name__ + 'Base_OMX')
      events.listener_del(self.__class__.__name__ + 'Base_OMX')
      self._OMP.quit()
      self._OMP = None
      if self._OMP_sizer_rect is None:
         self._OMP_sizer_rect.delete()
         self._OMP_sizer_rect = None

   def video_object_get(self):
      DBG("VIDEO OBJECT GET")
      return self._OMP_sizer_rect

   @property
   def url(self):
      return self._url

   @url.setter
   def url(self, url):
      DBG("URL SET: %s" % url)
      self._url = url
      self._OMP = OMXPlayer(url, ['--no-osd', '--no-key'],
                            self._playback_started_cb,
                            self._playback_finished_cb)

      self.volume = mediaplayer.volume_get()
      self.muted = mediaplayer.volume_mute_get()
      self._OMP.set_aspect_mode("letterbox")
      # self._OMP.set_alpha(128)
      self._OMP.pause()
      self._OMP.play()

   @property
   def seekable(self):
      return self._OMP.can_seek()

   @property
   def position(self):
      return self._OMP.position() or 0

   @position.setter
   def position(self, pos):
      self._OMP.set_position(pos)
      events.event_emit('PLAYBACK_SEEKED')

   @property
   def play_length(self):
      # DBG("PLAY LEN %s" % self._OMP.duration())
      return self._OMP.duration() or 0

   @property
   def paused(self):
      return self._OMP.is_paused()

   def pause(self):
      self._OMP.pause()
      events.event_emit('PLAYBACK_PAUSED')

   def unpause(self):
      self._OMP.play()
      events.event_emit('PLAYBACK_UNPAUSED')

   @property
   def volume(self):
      return int(self._OMP.volume() * 100)

   @volume.setter
   def volume(self, value):
      self._OMP.set_volume(value / 100.0)

   @property
   def muted(self):
      return self._OMP_muted

   @muted.setter
   def muted(self, value):
      if value:
         self._OMP.mute()
         self._OMP_muted = True
      else:
         self._OMP.unmute()
         self._OMP_muted = False

   @property
   def buffer_size(self):
      # TODO ???
      # return self._emotion.buffer_size
      return 1.0

   @buffer_size.setter
   def buffer_size(self, value):
      # TODO ???
      # self._emotion.buffer_size = value
      pass

   @property
   def audio_tracks(self):
      """ line format  <index>:<language>:<name>:<codec>:<active> """
      Track = namedtuple('Track', 'idx lang name codec active')
      L = []
      for line in self._OMP.list_audio():
         idx, lang, name, codec, active = line.split(':')
         L.append(Track(int(idx), lang, name, codec, (active == 'active')))
      return L

   @property
   def selected_audio_track(self):
      """ index of the selected audio track """
      idx = 0
      for e in self._OMP.list_audio():
         if e.endswith(':active'):
            return idx
         idx += 1
      return 0

   @selected_audio_track.setter
   def selected_audio_track(self, index):
      self._OMP.select_audio(max(0, index))

   @property
   def video_tracks(self):
      """ line format  <index>:<language>:<name>:<codec>:<active> """
      Track = namedtuple('Track', 'idx lang name codec active')
      L = []
      for line in self._OMP.list_video():
         idx, lang, name, codec, active = line.split(':')
         L.append(Track(int(idx), lang, name, codec, (active == 'active')))
      return L

   @property
   def selected_video_track(self):
      """ index of the selected video track """
      idx = 0
      for e in self._OMP.list_video():
         if e.endswith(':active'):
            return idx
         idx += 1
      return 0

   @selected_video_track.setter
   def selected_video_track(self, index):
      print('Video track selection not implemented in omx_player')
      # self._OMP.select_video(max(0, index))


class EmcVideoPlayer_OMX(mediaplayer.EmcVideoPlayer, EmcPlayerBase_OMX):
   video_player_cannot_be_covered = True


class EmcAudioPlayer_OMX(mediaplayer.EmcAudioPlayer, EmcPlayerBase_OMX):
   pass

