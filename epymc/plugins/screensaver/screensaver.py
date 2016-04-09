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

import time, re

from efl.ecore import Timer, Exe, ECORE_CALLBACK_RENEW

from epymc.modules import EmcModule
import epymc.ini as ini
import epymc.gui as gui
import epymc.config_gui as cgui
import epymc.events as events


def DBG(msg):
   # print('SSAVER: %s' % msg)
   pass


class ScreenSaver(EmcModule):
   name = 'screensaver'
   label = _('Screen saver')
   icon = 'icon/evas'
   info = _('This module manage the X screensaver. It will prevent the '
            'screensaver to activate while watching videos and can be '
            'configured to activate the screensaver and/or shutdown your '
            'monitor after a given amount of time.')

   def __init__(self):
      DBG('Init module')
      self.monitor_off_after = 0
      self.ssaver_on_after = 0
      self.only_in_fs = True
      self.status = 0  # 0=inactive 1=ss_active 2=monitor_off
      self.last_event_time = time.time()

      # create ini options if not exists (with defaults)
      ini.add_section('screensaver')
      ini.get('screensaver', 'screensaver_on_after', _('never'))
      ini.get('screensaver', 'screensaver_on_cmd', 'xset s activate')
      ini.get('screensaver', 'screensaver_off_cmd', 'xset s reset')
      ini.get('screensaver', 'monitor_off_after', _('never'))
      ini.get('screensaver', 'monitor_off_cmd', 'xset dpms force off')
      ini.get('screensaver', 'monitor_on_cmd', 'xset dpms force on')
      ini.get('screensaver', 'only_in_fs', 'True')

      # read config values
      self.parse_config()

      # register the config item
      cgui.root_item_add('ssaver', 40, _('Screen saver'), 'icon/evas', self.config_gui_cb)

      # start the timer
      self.timer = Timer(50.0, self.timer_cb)

      # listen to broadcasts events (we need the KEEP_ALIVE event)
      events.listener_add('screensaveer', self.event_cb)

   def __shutdown__(self):
      DBG('Shutdown module')
      events.listener_del('screensaveer')
      self.timer.delete()
      self.timer = None

   def parse_config(self):
      # get someting like "5 minutes" from config
      try:
         ssaver_on_after = ini.get('screensaver', 'screensaver_on_after')
         ssaver_on_after = int(re.sub('[^0-9]', '', ssaver_on_after))
         self.ssaver_on_after = ssaver_on_after * 60
      except:
         self.ssaver_on_after = 0

      # get someting like "10 minutes" from config
      try:
         monitor_off_after = ini.get('screensaver', 'monitor_off_after')
         monitor_off_after = int(re.sub('[^0-9]', '', monitor_off_after))
         self.monitor_off_after = monitor_off_after * 60
      except:
         self.monitor_off_after = 0

      # whenever to manage the ss only when in fullscreen 
      self.only_in_fs = ini.get_bool('screensaver', 'only_in_fs')

   def event_cb(self, event):
      if event == 'KEEP_ALIVE':
         self.last_event_time = time.time()
         if self.status != 0:
            self.status = 0
            self.timer_cb()
      
   def timer_cb(self):
      # nothing to do
      if self.ssaver_on_after == self.monitor_off_after == 0:
         return ECORE_CALLBACK_RENEW

      # not when windowed
      if self.only_in_fs is True and not gui.win.fullscreen:
         return ECORE_CALLBACK_RENEW

      # DBG("SS on after: %ds  MON off after: %ds (only fs: %s)" %
          # (self.ssaver_on_after, self.monitor_off_after, self.only_in_fs))

      # calc elapsed time since last STAY_ALIVE event
      now = time.time()
      elapsed = now - self.last_event_time
      DBG('ScreenSaver: Timer! status: %d  elapsed: %.0fs  ss_on_in: %.0fs  mon_off_in: %.0fs' % \
        (self.status, elapsed,
         self.last_event_time + self.ssaver_on_after - now if self.ssaver_on_after > 0 else -1,
         self.last_event_time + self.monitor_off_after - now if self.monitor_off_after > 0 else -1))

      def exe_run_safe(cmd):
         try:
            DBG("Executing: '%s'" % cmd)
            Exe(cmd)
         except:
            pass

      if self.status == 0:
         # Status 0: the screensaver is off - user is active
         if  elapsed > self.ssaver_on_after > 0:
            # turn on the screensaver
            DBG('ScreenSaver: activate screensaver')
            self.status = 1
            exe_run_safe(ini.get('screensaver', 'screensaver_on_cmd'))
         elif elapsed > self.monitor_off_after > 0:
            # turn off the monitor
            DBG('ScreenSaver: monitor off')
            self.status = 2
            exe_run_safe(ini.get('screensaver', 'monitor_off_cmd'))
         else:
            # or keep the screensaver alive and the monitor on
            DBG('ScreenSaver: keep alive')
            exe_run_safe(ini.get('screensaver', 'monitor_on_cmd'))
            exe_run_safe(ini.get('screensaver', 'screensaver_off_cmd'))

      elif self.status == 1:
         # Status 1: the screensaver is on - user is away
         if elapsed > self.monitor_off_after > 0:
            # turn off the monitor
            DBG('ScreenSaver: monitor off')
            self.status = 2
            exe_run_safe(ini.get('screensaver', 'monitor_off_cmd'))

         # the screensaver has been disabled outside epymc
         if elapsed < self.ssaver_on_after > 0:
            self.status = 0

      elif self.status == 2:
         # Status 2: the monitor is off - user probably sleeping :)

         # the monitor has been turned on outside epymc
         if elapsed < self.monitor_off_after > 0:
            self.status = 0

      return ECORE_CALLBACK_RENEW


   def config_gui_cb(self):
      bro = cgui.browser_get()
      bro.page_add('config://ssaver/', _('Screen saver'), None, self.config_gui_populate)
   
   def config_gui_populate(self, browser, url):
      L = _('never;1 minute;5 minutes;10 minutes;30 minutes;60 minutes').split(';')
      cgui.standard_item_string_from_list_add('screensaver', 'screensaver_on_after',
                                          _('Turn on screensaver after'), L,
                                          cb = self.parse_config)
      cgui.standard_item_string_from_list_add('screensaver', 'monitor_off_after',
                                          _('Turn off monitor after'), L,
                                          cb = self.parse_config)
      cgui.standard_item_bool_add('screensaver', 'only_in_fs',
                                  _('Manage screensaver only in fullscreen'),
                                  cb = self.parse_config)
