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

# Kodi references:
#  http://kodi.wiki/view/list_of_built-in_functions

import sys

from epymc import gui


thismodule = sys.modules[__name__]


def DBG(*args):
   print('KODI BUILTIN:', *args)
   pass


def execute_builtin(command):
   DBG('Executing: "{}"'.format(command))

   # split function name and arguments
   if '(' in command and command.endswith(')'):
      func_name, params_str = command[:-1].split('(')
      params = list(map(str.strip, params_str.split(',')))
   else:
      func_name = command
      params = []

   # search the function in this module
   try:
      func = getattr(thismodule, func_name.strip())
   except AttributeError:
      DBG('NOT IMPLEMENTED: ', func_name)
      return False

   # execute function (all params are passe as string)
   try:
      func(*params)
   except TypeError:
      DBG('Error calling function:', func_name)
      return False

   return True


def Notification(header, message, time=None, image=None):
   if time is not None:
      time = int(time) / 1000
   text = '<title>{0}</title><br>{1}'.format(header, message)
   gui.EmcNotify(text, image, time)

