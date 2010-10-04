#!/usr/bin/env python

import os
import urllib


def config_dir_get():
   return os.path.expanduser('~/.config/epymc')

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

