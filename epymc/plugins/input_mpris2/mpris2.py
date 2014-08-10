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

from dbus_helper import DBusServiceObjectWithProps, dbus_property


def DBG(msg):
   print('MPRIS2: ' + msg)
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

   @dbus_property(ROOT_IFACE, signature='b')
   def CanQuit(self):
      DBG('CanQuit()')
      return False

   @dbus.service.method(ROOT_IFACE)
   def Quit(self):
      DBG('Quit()')


   ### The Player interface: org.mpris.MediaPlayer2.Player ####################

   @dbus.service.method(PLAYER_IFACE)
   def Play(self):
      input_events.event_emit('PLAY')

   @dbus.service.method(PLAYER_IFACE)
   def Pause(self):
      input_events.event_emit('PAUSE')

   @dbus.service.method(PLAYER_IFACE)
   def PlayPause(self):
      input_events.event_emit('TOGGLE_PAUSE')

   @dbus.service.method(PLAYER_IFACE)
   def Stop(self):
      input_events.event_emit('STOP')

