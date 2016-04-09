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

from __future__ import absolute_import, print_function, division, unicode_literals

import os

import efl.ecore as ecore

from epymc.modules import EmcModule


def DBG(msg):
   print('WATCHDOG: %s' % msg)


class Watchdog(EmcModule):
   name = 'watchdog'
   label = _('Watchdog')
   icon = 'icon/watchdog'
   info = _('This module, if enabled, will respawn epymc in the rare cases '
            'of application crash/hang. So you dont have to leave your '
            'couch in case of problems...just wait 30 seconds and the module '
            'will restart epymc for you.')

   WD_FILE = '/tmp/epymc_watchdog'

   def __init__(self):
      DBG('Init module')

      # report we are alive every 5 seconds...
      self._timer = ecore.Timer(5.0, self.timer_cb)
      self.timer_cb() # ...and a first time now

      # run the watchdog daemon
      ecore.Exe('epymc_watchdog')

   def __shutdown__(self):
      DBG('Shutdown module')
      # kill the timer and the daemon
      self._timer.delete()
      ecore.Exe('killall epymc_watchdog')

   def timer_cb(self):
      # update file modification time of the watchdog file (WE ARE ALIVE!)
      with open(self.WD_FILE, 'a'):
         os.utime(self.WD_FILE)
      return ecore.ECORE_CALLBACK_RENEW

