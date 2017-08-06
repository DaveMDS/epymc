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

from omxplayer import OMXPlayer

from efl import ecore
from efl import elementary as elm
# from efl.elementary.list import List

from epymc.modules import EmcModule
from epymc.mediaplayer import EmcPlayerBase
from epymc import events
# import epymc.input_events as input_events
# from epymc.gui import EmcVKeyboard, EmcDialog
# from epymc.browser import EmcItemClass
# import epymc.ini as ini
# import epymc.gui as gui
# import epymc.config_gui as config_gui


def DBG(msg):
   print('OMX: %s' % msg)
   # pass

class OmxPlayerModule(EmcModule):
   name = 'mp_omxplayer'
   label = _('Media Player - OMX external player')
   icon = 'icon/remote'
   info = _('Use an external omx_player instance to play videos.')

   def __init__(self):
      DBG('Init module')

   
      # get lirc socket from config
      # ini.add_section('lirc')
      # self.device = ini.get('lirc', 'device', self.DEFAULT_LIRC_SOCKET)
      
      # add an entry in the config section
      # config_gui.root_item_add('lirc', 51, _('Remote'), icon='icon/remote',
                               # callback=self.config_panel_cb)




   def __shutdown__(self):
      DBG('Shutdown module')
      # config_gui.root_item_del('lirc')




class EmcPlayerBase_OMX(EmcPlayerBase):
   def __init__(self):
      self._url = None
      self._OMP = None
      DBG("CUSTOM PLAYER")

   def delete(self):
      # input_events.listener_del(self.__class__.__name__ + 'Base')
      # events.listener_del(self.__class__.__name__ + 'Base')
      # self._emotion.delete()
      DBG("CUSTOM PLAYER  DELETE !!!")
      self._OMP.quit()
      self._OMP = None

   @property
   def url(self):
      return self._url

   @url.setter
   def url(self, url):
      DBG("CUSTOM PLAYER:  URL SET: %s" % url)
      # default to 'file://' if not given
      # if url.find('://', 2, 15) == -1:
         # url = 'file://' + url
      self._url = url

      if self._OMP is None:
         self._OMP = OMXPlayer(url)
         self._OMP.set_alpha(250)  # TODO REMOVE ME !!!!
      else:
         self._OMP.load(url)

      self._OMP.play()

      # Do not pass "file://" to emotion. Vlc has a bug somewhere that prevent
      # files with special chars in them to play (the bug don't appear if no
      # "file://" is given. The bug can be seen also using normal vlc from
      # the command line.
      # self._emotion.file_set(url[7:] if url.startswith('file://') else url)
      # self._emotion.play = True
      # self._emotion.audio_volume = volume_get() / 100.0
      # self._emotion.audio_mute = volume_mute_get()
      # if not url.startswith('dvd://'): # spu used in dvdnav
         # self._emotion.spu_mute = True
         # self._emotion.spu_channel = -1

   @property
   def seekable(self):
      return True

   @property
   def position(self):
      """ the playback position in seconds (float) from the start """
      DBG("CUSTOM PLAYER:  POS %s" % self._OMP.position())
      return self._OMP.position()

   @position.setter
   def position(self, pos):
      self._OMP.set_position(pos)
      events.event_emit('PLAYBACK_SEEKED')

   @property
   def play_length(self):
      DBG("CUSTOM PLAYER:  PLAY LEN %s" % self._OMP.duration())
      return self._OMP.duration()

   @property
   def paused(self):
      DBG("CUSTOM PLAYER:  PAUSED %s" % (not self._OMP.is_playing()))
      return not self._OMP.is_playing()

   def pause(self):
      DBG("CUSTOM PLAYER:  PAUSE")
      self._OMP.pause()
      events.event_emit('PLAYBACK_PAUSED')

   def unpause(self):
      DBG("CUSTOM PLAYER:  UNPAUSE")
      self._OMP.play()
      events.event_emit('PLAYBACK_UNPAUSED')

   @property
   def buffer_size(self):
      # return self._emotion.buffer_size
      return 1.0

   @buffer_size.setter
   def buffer_size(self, value):
      # self._emotion.buffer_size = value
      pass


###
### monkey patch the core Player classes with the OMX specific implementation
###
from epymc import mediaplayer

class EmcVideoPlayer_OMX(mediaplayer.EmcVideoPlayer, EmcPlayerBase_OMX):
   pass

class EmcAudioPlayer_OMX(mediaplayer.EmcAudioPlayer, EmcPlayerBase_OMX):
   pass

mediaplayer.EmcPlayerBase = EmcPlayerBase_OMX
mediaplayer.EmcVideoPlayer = EmcVideoPlayer_OMX
mediaplayer.EmcAudioPlayer = EmcAudioPlayer_OMX
