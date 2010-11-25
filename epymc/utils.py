#!/usr/bin/env python
#
# Copyright (C) 2010 Davide Andreoli <dave@gurumeditation.it>
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

import os
import urllib
import tempfile

import ecore.file


def DBG(msg):
   print('UTILS: ' + str(msg))
   pass


_base_dir = None
_config_dir = None

def base_dir_set(d):
   global _base_dir
   _base_dir = d

def base_dir_get():
   return _base_dir


def config_dir_get():
   global _config_dir
   if not _config_dir:
      _config_dir = os.path.expanduser('~/.config/epymc')
   return _config_dir


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

      # search relative to the script (epymc.py) dir
      f = os.path.join(base_dir_get(), "data", type, res)
      if os.path.exists(f):
         return f

   # not found :(
   return None

def download_url_sync(url, dest, min_size = 0):
   """
   Copy the contents of a file from a given URL to a local file, blocking
   the code while the download is in progress, you should use the async
   version instead.
   """
   dir = os.path.dirname(dest)
   if not os.path.exists(dir):
      os.makedirs(dir)

   (filename, headers) = urllib.urlretrieve(url, dest)
   DBG("Filename: " + filename)
   #~ print headers
   if os.path.getsize(filename) < min_size:
      DBG("TOO SHORT " + str(os.path.getsize(filename)))
      os.remove(filename)
      return None

   return headers

def download_url_async(url, dest = 'tmp', min_size = 0,
                       complete_cb = None, progress_cb = None,
                       *args, **kargs):
   """
   Download the given url in async way.
   url must be a valid url to download
   If dest is set to a local file name then the download data will
      be written to that file (created and overwritten if necessary, also
      the necessary parent directories are created)
   If dest is omitted (or is 'tmp') than the data will be written
      to a random new temp file

   if min_size is set (and > 0) than downloaded files smaller that min_size
      will be discarted

   complete_cb, if given, will be called when the download is done
         def complete_cb(file, status, *args, **kargs):

   progress_cb will be called while the download is in progress
         def progress_cb(file, dltotal, dlnow, *args, **kargs):

   TODO If dest is set to None than the data will be passed as the dest param
      in the complete_cb

   """

   def _cb_download_complete(dest, status, dwl_data, *args, **kargs):
      (complete_cb, progress_cb, min_size) = dwl_data

      # if file size < min_size: report as error
      if status == 0 and min_size > 0 and os.path.getsize(dest) < min_size:
         DBG("MIN_SIZE not reached, discard download")
         status = 1

      # on errors delete the downloaded file
      if status > 0 and os.path.exists(dest):
         DBG("download error")
         os.remove(dest)

      # call the user complete_cb if available
      if complete_cb and callable(complete_cb):
         complete_cb(dest, status, *args, **kargs)

   def _cb_download_progress(dest, dltotal, dlnow, uptotal, upnow, dwl_data, *args, **kargs):
      (complete_cb, progress_cb, min_size) = dwl_data
      #TODO filter out some call (maybe report only when dlnow change)
      if progress_cb and callable(progress_cb):
         progress_cb(dest, dltotal, dlnow, *args, **kargs)
      return 0 # always continue the download

   # urlencode the url (but not the http:// part, or ':' will be converted)
   (_prot, _url) = url.split('://', 1)
   encoded = '://'.join((_prot, urllib.quote(_url)))
   
   # use a random temp file
   if dest == 'tmp':
      dest = tempfile.mktemp()
   elif dest:
      # create dest path if necessary,
      dirname = os.path.dirname(dest)
      if not os.path.exists(dirname):
         os.makedirs(dirname)
      # remove destination file if exists (overwrite)
      if os.path.exists(dest):
         os.remove(dest)

   # store download data for later use
   dwl_data = (complete_cb, progress_cb, min_size)

   # start the download
   return ecore.file.download(encoded, dest, _cb_download_complete,
               _cb_download_progress, dwl_data = dwl_data, *args, **kargs)

