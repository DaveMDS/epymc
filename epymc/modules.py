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

import sys
import os
import traceback

from epymc import ini
from epymc import utils


def LOG(msg):
   print("MODULES: %s" % msg)

# modules enabled by default
DEFAULT_MODS = 'calibrator input_keyb onlinevideo movies music ' \
               'tvshows screensaver photos opticals'

class EmcModule(object):
   name = ''
   label = ''
   icon = ''
   info = ''

   def __init__(self):
      pass

   def __shutdown__(self):
      pass

   def __restart__(self):
      self.__shutdown__()
      self.__init__()


_instances = {} # key: module_name   val: EmcModule instance


def load_all():

   def _scan_folder(path):
      LOG('Searching for modules in: %s' % path)
      if not path in sys.path:
         sys.path.insert(0, path)
      for root, dirs, files in os.walk(path):
         for name in dirs:
            f = os.path.join(root, name, '__init__.py')
            if os.path.isfile(f):
               try:
                  LOG(' * loading: %s' % name)
                  mod =  __import__(name)
               except:
                  LOG(' * FAILED: %s' % f)
                  traceback.print_exc()
      LOG('')

   # load from the plugins/ dir relative to script position
   _scan_folder(os.path.join(utils.emc_base_dir, 'plugins'))

   # load from ~/.config/epymc/plugins ...
   _scan_folder(os.path.join(utils.user_conf_dir, 'plugins'))

"""
def load_all_SETUPTOOLS():
   print('Searching for modules:')

   for entrypoint in pkg_resources.iter_entry_points("epymc_modules"):
      try:
         print(' * loading: ' + entrypoint.name)
         entrypoint.load()
      except:
         print('    FAILED: ' + entrypoint.name)
         traceback.print_exc()
   print('')
"""

def get_module_by_name(name):
   for mod in EmcModule.__subclasses__():
      if mod.name == name:
         return mod
   return None

def list_get():
   return EmcModule.__subclasses__()

def is_enabled(name):
   return name in _instances

def init_by_name(name):
   for mod in EmcModule.__subclasses__():
      if mod.name == name:
         if not name in _instances:
            try:
               _instances[name] = mod()
            except:
               traceback.print_exc()

def init_all():
   for mod in EmcModule.__subclasses__():
      if not mod.name in _instances:
         _instances[mod.name] = mod()

def init_all_by_config():
   if not ini.has_option('general', 'modules'):
      ini.set('general', 'modules', DEFAULT_MODS)

   for modname in ini.get_string_list('general', 'modules'):
      init_by_name(modname)

def save_enabled():
   ini.set('general', 'modules', ' '.join(_instances.keys()))

def shutdown_by_name(name):
   if name in _instances:
      _instances[name].__shutdown__()
      del _instances[name]

def shutdown_all():
   LOG('Shutting down modules:')
   L = list()
   for mod in _instances:
      L.append(mod)
   for mod in L:
      shutdown_by_name(mod)
   LOG('')
