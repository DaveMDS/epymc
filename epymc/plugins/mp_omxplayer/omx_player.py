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

import os
import dbus
from collections import OrderedDict
from dbus import Int32, Int64, String, ObjectPath
from dbus.connection import Connection as DBusConnection

from efl import ecore
from efl.dbus_mainloop import DBusEcoreMainLoop

from epymc import utils


def DBG(msg):
   print('OMX_PLAYER: %s' % msg)
   # pass


class LastUpdatedOrderedDict(OrderedDict):
   """ Store items in the order the keys were last added """
   def __setitem__(self, key, value):
      if key in self:
         del self[key]
      OrderedDict.__setitem__(self, key, value)


class OMXPlayer(object):
   """ Wrapper around the omxplayer binary

   Run an omxplayer instance in an external process and communicate using
   the MPRIS DBus interface on the SessionBus.

   HIGHLY inspired by github.com/willprice/python-omxplayer-wrapper

   """
   DBUS_NAME = 'org.mpris.MediaPlayer2.omxplayer'
   ROOT_IFACE = 'org.mpris.MediaPlayer2'
   PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
   PROPS_IFACE = 'org.freedesktop.DBus.Properties'

   def __init__(self, url, omx_args=[],
                playback_started_cb=None, playback_finished_cb=None):
      DBG('__init__')
      self._exe = None
      self._root_iface = None
      self._player_iface = None
      self._props_iface = None
      self._cached_commands = LastUpdatedOrderedDict()
      self._playback_started_cb = playback_started_cb
      self._playback_finished_cb = playback_finished_cb

      self._process_spawn(url, omx_args)

   def _process_spawn(self, url, omx_args):
      cmd = 'omxplayer.bin %s "%s"' % (' '.join(omx_args), url)
      DBG('cmd: %s' % cmd)

      def add_cb(exe, event):
         DBG("omx process started")
         ecore.Timer(0.2, self._dbus_connect_try)

      def del_cb(exe, event):
         DBG("omx process died")
         self._exe = None
         self._root_iface = self._player_iface = self._props_iface = None
         self._cached_commands.clear()
         self._playback_finished_cb(None)

      self._exe = ecore.Exe(cmd, ecore.ECORE_EXE_TERM_WITH_PARENT)
      self._exe.on_add_event_add(add_cb)
      self._exe.on_del_event_add(del_cb)

   def _dbus_connect_try(self):
      DBG("connect try")

      if self._exe is None:  # process already died ?
         return ecore.ECORE_CALLBACK_CANCEL

      """
      # conect the omxplayer private bus address from the file created in tmp
      fname = '/tmp/omxplayerdbus.%s' % utils.user_name()
      if not os.path.exists(fname) or not os.path.getsize(fname):
         return ecore.ECORE_CALLBACK_RENEW  # retry on next timer tick
      bus_address = open(fname).read().strip()
      DBG('dbus address: %s' % bus_address)
      try:
         bus = DBusConnection(bus_address, mainloop=DBusEcoreMainLoop())
         obj = bus.get_object(self.DBUS_NAME, '/org/mpris/MediaPlayer2',
                              introspect=False)
      except dbus.exceptions.DBusException as e:
         DBG("DBUS CONNECTION ERROR: %s" % e)
         return ecore.ECORE_CALLBACK_RENEW  # retry on next timer tick
      """

      # connect to the standard Session bus
      try:
         bus = dbus.SessionBus(mainloop=DBusEcoreMainLoop())
         obj = bus.get_object(self.DBUS_NAME, '/org/mpris/MediaPlayer2',
                              introspect=False)
      except dbus.exceptions.DBusException as e:
         DBG("DBUS CONNECTION ERROR: %s" % e)
         return ecore.ECORE_CALLBACK_RENEW  # retry on next timer tick

      # get the 3 usefull interfaces
      self._root_iface = dbus.Interface(obj, self.ROOT_IFACE)
      self._player_iface = dbus.Interface(obj, self.PLAYER_IFACE)
      self._props_iface = dbus.Interface(obj, self.PROPS_IFACE)
      DBG("connection ok")

      # execute all commands received while starting up (only valid for setters)
      while self._cached_commands:
         fn, (args, kargs) = self._cached_commands.popitem(last=False)
         DBG("running cached command: %s" % fn.__name__)
         fn(self, *args, **kargs)

      # notify epymc
      self._playback_started_cb(None)

      return ecore.ECORE_CALLBACK_CANCEL  # stop the timer

   def _check_player_is_active(fn):
      """ Decorator that execute the decorated function if the dbus connection
          is alive, otherwise the function call is cached to run when the
          connection will be available """
      def wrapper(self, *args, **kargs):
         if self._root_iface and self._exe and not self._exe.is_deleted():
            try:
               return fn(self, *args, **kargs)
            except dbus.exceptions.DBusException:
               pass  # can fail while omx_player is shutting down
         else:
            DBG('WARNING: player not active, caching command: %s' % fn.__name__)
            self._cached_commands[fn] = (args, kargs)
      return wrapper


   ######  Public API  #######

   def quit(self):
      if self._exe:
         self._exe.terminate()

   @_check_player_is_active
   def play(self):
      self._player_iface.Play()

   @_check_player_is_active
   def pause(self):
      self._player_iface.Pause()

   @_check_player_is_active
   def play_pause(self):
      self._player_iface.PlayPause()

   @_check_player_is_active
   def stop(self):
      self._player_iface.Stop()

   @_check_player_is_active
   def is_paused(self):
      """ Whether the player is paused (bool) """
      return str(self._props_iface.PlaybackStatus()) == "Paused"

   @_check_player_is_active
   def is_playing(self):
      """ Whether the player is playing (bool) """
      return str(self._props_iface.PlaybackStatus()) == "Playing"

   @_check_player_is_active
   def position(self):
      """ Get the position in seconds (float) """
      return self._props_iface.Position() / (1000 * 1000.0)

   @_check_player_is_active
   def set_position(self, pos):
      """ Set the position in seconds (float) """
      self._player_iface.SetPosition(ObjectPath("/not/used"),
                                     Int64(pos * 1000 * 1000))

   @_check_player_is_active
   def duration(self):
      """ Get the duration in seconds (float) """
      return self._props_iface.Duration() / (1000 * 1000.0)

   @_check_player_is_active
   def volume(self):
      """ Get volume in range 0.0 -> 1.0 (float) """
      return float(self._props_iface.Volume())

   @_check_player_is_active
   def set_volume(self, volume):
      """ Set volume in range 0.0 -> 1.0 (float) """
      DBG("VOLUME SET %.3f" % volume)
      self._props_iface.Volume(volume)

   @_check_player_is_active
   def mute(self):
      """ Turns mute on, if the audio is already muted nothing is done """
      self._props_iface.Mute()

   @_check_player_is_active
   def unmute(self):
      """ Turns mute off, if the audio is already unmuted, nothing is done """
      self._props_iface.Unmute()

   @_check_player_is_active
   def set_aspect_mode(self, mode):
      """ One of ("letterbox" | "fill" | "stretch") """
      self._player_iface.SetAspectMode(ObjectPath('/not/used'), String(mode))

   @_check_player_is_active
   def set_video_pos(self, x1, y1, x2, y2):
      """ Video image position """
      pos = '%s %s %s %s' % (str(x1),str(y1),str(x2),str(y2))
      self._player_iface.VideoPos(ObjectPath('/not/used'), String(pos))

   @_check_player_is_active
   def set_video_crop(self, x1, y1, x2, y2):
      """ Video image crop """
      crop = '%s %s %s %s' % (str(x1),str(y1),str(x2),str(y2))
      self._player_iface.SetVideoCropPos(ObjectPath('/not/used'), String(crop))

   @_check_player_is_active
   def list_video(self):
      """ A list of all known video streams (str)
            format: ``<index>:<language>:<name>:<codec>:<active>``
      """
      return map(str, self._player_iface.ListVideo())

   @_check_player_is_active
   def list_audio(self):
      """ A list of all known audio streams
            format: ``<index>:<language>:<name>:<codec>:<active>``
      """
      return map(str, self._player_iface.ListAudio())

   @_check_player_is_active
   def select_audio(self, index):
      """ The index of the audio stream to select """
      return bool(self._player_iface.SelectAudio(Int32(index)))

   @_check_player_is_active
   def list_subtitles(self):
      """ A list of all known subtitles
            format: ``<index>:<language>:<name>:<codec>:<active>``
      """
      return map(str, self._player_iface.ListSubtitles())

   @_check_player_is_active
   def select_subtitle(self, index):
      """ The index of the subtitle to select """
      return bool(self._player_iface.SelectSubtitle(Int32(index)))

