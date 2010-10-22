#!/usr/bin/env python

import sys
import os

import ini
import utils



class EmcModule(object):
   name = ''
   label = ''


_instances = {}


def load_all():
   print "Searching for modules:"

   # first check in ~/.config/epymc/modules ...
   path = os.path.join(utils.config_dir_get(), 'modules')
   if not path in sys.path:
      sys.path.insert(0, path)

   for root, dirs, files in os.walk(path):
      for name in dirs:
         f = os.path.join(root, name, '__init__.py')
         if os.path.isfile(f):
            print " * load: " + f
            mod =  __import__(name)
   
   # ... then in the modules/ dir relative to script position
   path = os.path.join(os.path.dirname(__file__), 'modules')
   if not path in sys.path:
      sys.path.insert(0, path)

   for root, dirs, files in os.walk(path):
      for name in dirs:
         f = os.path.join(root, name, '__init__.py')
         if os.path.isfile(f):
            print " * load: " + f
            mod =  __import__(name)
   print ""



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
      ini.set('general', 'modules', " ".join(_instances.keys()))

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
   print ""

