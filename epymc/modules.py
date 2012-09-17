#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2012 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of EpyMC.
#
# EpyMC is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# EpyMC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with EpyMC. If not, see <http://www.gnu.org/licenses/>.

import sys
import os

import ini
import utils



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


_instances = {}


def load_all():
   print ('Searching for modules:')

   # first check in ~/.config/epymc/modules ...
   path = os.path.join(utils.config_dir_get(), 'modules')
   if not path in sys.path:
      sys.path.insert(0, path)

   for root, dirs, files in os.walk(path):
      for name in dirs:
         f = os.path.join(root, name, '__init__.py')
         if os.path.isfile(f):
            print (' * load: ' + f)
            mod =  __import__(name)
   
   # ... then in the modules/ dir relative to script position
   path = os.path.join(utils.base_dir_get(), 'modules')
   if not path in sys.path:
      sys.path.insert(0, path)

   for root, dirs, files in os.walk(path):
      for name in dirs:
         f = os.path.join(root, name, '__init__.py')
         if os.path.isfile(f):
            print (' * load: ' + f)
            mod =  __import__(name)
   print ''

def get_module_by_name(name):
   for mod in EmcModule.__subclasses__():
      if mod.name == name:
         return mod
   return None

def list_get():
   return EmcModule.__subclasses__()

def is_enabled(name):
   return _instances.has_key(name)

def init_by_name(name):
   for mod in EmcModule.__subclasses__():
      if mod.name == name:
         if not name in _instances:
            _instances[name] = mod()

def init_all():
   for mod in EmcModule.__subclasses__():
      if not mod.name in _instances:
         _instances[mod.name] = mod()

def init_all_by_config():
   if ini.has_option('general', 'modules'):
      to_load = ini.get_string_list('general', 'modules')
      for modname in to_load:
         init_by_name(modname)
   else:
      init_all()
      ini.set('general', 'modules', ' '.join(_instances.keys()))

def save_enabled():
   ini.set('general', 'modules', ' '.join(_instances.keys()))

def shutdown_by_name(name):
   if _instances.has_key(name):
      _instances[name].__shutdown__()
      del _instances[name]

def shutdown_all():
   print 'Shutting down modules:'
   L = list()
   for mod in _instances:
      L.append(mod)
   for mod in L:
      shutdown_by_name(mod)
   print ''
