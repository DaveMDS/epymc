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

from .kodi_addon_base import KodiAddonBase


class KodiPythonModule(KodiAddonBase):

   extension_point = ".//extension[@point='xbmc.python.module']"

   def __init__(self, *args):
      KodiAddonBase.__init__(self, *args)

      ext = self._root.find(self.extension_point)
      self._main_import = ext.get('library')
      for elem in ext:
         if elem.tag == 'provides':
            self._provides = elem.text

   @property
   def main_import(self):
      """ main library to import """
      return os.path.join(self.path, self._main_import)

