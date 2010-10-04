#!/usr/bin/env python

import sys
import os

import ini



class EmcModule(object):
   name = ''
   label = 'Films'



def load_all():
   print "Searching for modules:"

   if not "modules/" in sys.path:
      sys.path.insert(0, "modules/")

   for root, dirs, files in os.walk("modules/"):
      for name in dirs:
         if os.path.isfile("modules/" + name + "/__init__.py"):
            print " * found: " + name
            mod =  __import__(name)
   print ""


_instances = {}


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

