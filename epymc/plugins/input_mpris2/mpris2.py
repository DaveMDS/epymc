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

import dbus
import dbus.service

from efl import ecore
from efl.dbus_mainloop import DBusEcoreMainLoop

from epymc.modules import EmcModule
import epymc.input_events as input_events
import epymc.mediaplayer as mediaplayer
import epymc.utils as utils
import epymc.gui as gui

from dbus_helper import DBusServiceObjectWithProps, dbus_property


def DBG(msg):
   print('MPRIS2: %s' % msg)
   pass


class MPRIS2Module(EmcModule):
   name = 'input_mpris2'
   label = _('Input - MPRIS2')
   icon = 'icon/dbus'
   info = _("""Long info for the <b>MPRIS2</b> module, explain what it does
and what it need to work well, can also use markup like <title>this</> or
<b>this</>""")

   BUS_NAME = "org.mpris.MediaPlayer2.epymc"

   def __init__(self):
      DBG('Init module')
      bus = dbus.SessionBus(mainloop=DBusEcoreMainLoop())
      name = dbus.service.BusName(self.BUS_NAME, bus)
      self.player = Mpris_MediaPlayer2(name)

   def __shutdown__(self):
      DBG('Shutdown module')
      self.player.remove_from_connection()



class Mpris_MediaPlayer2(DBusServiceObjectWithProps):
   PATH = "/org/mpris/MediaPlayer2"
   ROOT_IFACE = "org.mpris.MediaPlayer2"
   PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"

   def __init__(self, name):
      DBusServiceObjectWithProps.__init__(self, object_path=self.PATH,
                                                bus_name=name)


   ### The root interface: org.mpris.MediaPlayer2 #############################

   ## properties
   @dbus_property(ROOT_IFACE, signature='b')
   def CanQuit(self):
      return True

   @dbus_property(ROOT_IFACE, signature='b')
   def CanSetFullscreen(self):
      return True

   @dbus_property(ROOT_IFACE, signature='b', setter='FullscreenSet')
   def Fullscreen(self):
      return gui.fullscreen_get()

   def FullscreenSet(self, value):
      gui.fullscreen_set(bool(value))

   @dbus_property(ROOT_IFACE, signature='b')
   def CanRaise(self):
      return True

   @dbus_property(ROOT_IFACE, signature='b')
   def CanRaise(self):
      return True

   @dbus_property(ROOT_IFACE, signature='b')
   def HasTrackList(self):
      return False

   @dbus_property(ROOT_IFACE, signature='s')
   def Identity(self):
      return 'Emotion Media Center'

   @dbus_property(ROOT_IFACE, signature='s')
   def DesktopEntry(self):
      return 'epymc'

   @dbus_property(ROOT_IFACE, signature='as')
   def SupportedUriSchemes(self):
      return utils.supported_uris

   @dbus_property(ROOT_IFACE, signature='as')
   def SupportedMimeTypes(self):
      return utils.supported_mimes

   ## methods
   @dbus.service.method(ROOT_IFACE)
   def Quit(self):
      gui.exit_now()

   @dbus.service.method(ROOT_IFACE)
   def Raise(self):
      gui.win_raise()


   ### The Player interface: org.mpris.MediaPlayer2.Player ####################

   ## methods
   @dbus.service.method(PLAYER_IFACE)
   def Next(self):
      input_events.event_emit('PLAYLIST_NEXT')

   @dbus.service.method(PLAYER_IFACE)
   def Previous(self):
      input_events.event_emit('PLAYLIST_PREV')

   @dbus.service.method(PLAYER_IFACE)
   def Pause(self):
      input_events.event_emit('PAUSE')

   @dbus.service.method(PLAYER_IFACE)
   def PlayPause(self):
      input_events.event_emit('TOGGLE_PAUSE')

   @dbus.service.method(PLAYER_IFACE)
   def Stop(self):
      input_events.event_emit('STOP')

   @dbus.service.method(PLAYER_IFACE)
   def Play(self):
      input_events.event_emit('PLAY')

   @dbus.service.method(PLAYER_IFACE, in_signature='x')
   def Seek(self, Offset): #microseconds
      DBG("Seek %d microsecs" % Offset)
      secs = Offset / 1000000.0
      mediaplayer.seek(secs)

   @dbus.service.method(PLAYER_IFACE, in_signature='ox')
   def SetPosition(self, TrackId, Position):
      # TrackId ignored atm
      mediaplayer.position_set(Position / 1000000.0)

   @dbus.service.method(PLAYER_IFACE, in_signature='s')
   def OpenUri(self, Uri):
      raise NotImplementedError # TODO

   ## properties
   @dbus_property(PLAYER_IFACE, signature='s')
   def PlaybackStatus(self):
      return mediaplayer.play_state_get()
   
   @dbus_property(PLAYER_IFACE, signature='s', setter='LoopStatusSet')
   def LoopStatus(self):
      return 'Playlist'

   def LoopStatusSet(self, loop):
      DBG('TODO LoopStatusSet: %s' % loop)
      raise NotImplementedError # TODO

   @dbus_property(PLAYER_IFACE, signature='d', setter='RateSet')
   def Rate(self):
      return 1.0

   def RateSet(self, rate):
      DBG('TODO RateSet: %s' % rate)
      raise NotImplementedError # TODO

   @dbus_property(PLAYER_IFACE, signature='d', setter='ShuffleSet')
   def Shuffle(self):
      return False

   def ShuffleSet(self, shuffle):
      DBG('TODO ShuffleSet: %s' % shuffle)
      raise NotImplementedError # TODO

   @dbus_property(PLAYER_IFACE, signature='a{sv}')
   def Metadata(self):
      """ freedesktop.org/wiki/Specifications/mpris-spec/metadata/ """

      metadata = {}
      item = mediaplayer.playlist.onair_item
      if not item:
         return dbus.Dictionary(metadata, signature='sv', variant_level=1)

      metadata["mpris:trackid"] = dbus.ObjectPath('/org/epymc/pl/trk%d' % \
                                                  mediaplayer.playlist.cur_idx)

      if 'length' in item.metadata:
         metadata['mpris:length'] = dbus.Int64(item.metadata['length'] * 1000000)

      if 'poster' in item.metadata and item.metadata['poster']:
         metadata['mpris:artUrl'] = 'file://' + item.metadata['poster']

      if 'artist' in item.metadata:
         metadata['xesam:artist'] = [item.metadata['artist']]

      play_count = mediaplayer.play_counts_get(item.url)['finished']
      metadata['xesam:useCount'] = int(play_count)

      name_map = {'album': 'xesam:album', 'title': 'xesam:title',
                  'tracknumber': 'xesam:trackNumber', 'url': 'xesam:url'}
      for mine, xesam in name_map.items():
         if mine in item.metadata:
            metadata[xesam] = item.metadata[mine]

      DBG(metadata)
      return dbus.Dictionary(metadata, signature='sv', variant_level=1)

   @dbus_property(PLAYER_IFACE, signature='d', setter='VolumeSet')
   def Volume(self):
      return mediaplayer.volume_get() / 100.0

   def VolumeSet(self, volume):
      mediaplayer.volume_set(volume * 100)

   @dbus_property(PLAYER_IFACE, signature='x')
   def Position(self):
      return int(mediaplayer.position_get() * 1000000)

   @dbus_property(PLAYER_IFACE, signature='d')
   def MinimumRate(self):
      return 1.0

   @dbus_property(PLAYER_IFACE, signature='d')
   def MaximumRate(self):
      return 1.0

   @dbus_property(PLAYER_IFACE, signature='b')
   def CanGoNext(self): # TODO this can be improved
      if len(mediaplayer.playlist) > 0:
         return True
      return False

   @dbus_property(PLAYER_IFACE, signature='b')
   def CanGoPrevious(self): # TODO this can be improved
      if len(mediaplayer.playlist) > 0:
         return True
      return False

   @dbus_property(PLAYER_IFACE, signature='b')
   def CanPlay(self):
      if len(mediaplayer.playlist) > 0:
         return True
      return False

   @dbus_property(PLAYER_IFACE, signature='b')
   def CanPause(self):
      return True

   @dbus_property(PLAYER_IFACE, signature='b')
   def CanSeek(self):
      return mediaplayer.seekable_get()

   @dbus_property(PLAYER_IFACE, signature='b')
   def CanControl(self):
      return True

   # TODO implement the Seeked signal
