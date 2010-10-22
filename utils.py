#!/usr/bin/env python

import os
import urllib


def config_dir_get():
   # TODO 'cache' this
   return os.path.expanduser('~/.config/epymc')


def get_resource_file(type, resource, default = None):
   """
   This will search the given reasource (the file name) in user config dir and
   then in the script dir. ex:
      full_path = get_resource_file('themes', 'mytheme.edj', 'default.edj')
   """
   for res in [resource, default]:
      # search in user config dir
      f = os.path.join(config_dir_get(), type, res)
      if os.path.exists(f):
         return f

      # search relative to the script
      path = os.path.dirname(__file__)
      f = os.path.join(path, "data", type, res)
      if os.path.exists(f):
         return f

   # not found :(
   return None

def download_url_sync(url, dest, min_size = 0):
   """Copy the contents of a file from a given URL to a local file. """

   dir = os.path.dirname(dest)
   if not os.path.exists(dir):
      os.makedirs(dir)

   (filename, headers) = urllib.urlretrieve(url, dest)
   print "Filename: " + filename
   #~ print headers
   if os.path.getsize(filename) < min_size:
      print "TOO SHORT " + str(os.path.getsize(filename))
      os.remove(filename)
      return None

   return headers

