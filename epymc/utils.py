#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2014 Davide Andreoli <dave@gurumeditation.it>
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

import os, tempfile, glob, re

try:
   from urllib.parse import quote as urllib_quote
except:
   from urllib import quote as urllib_quote

from efl import ecore
from efl.ecore import FileDownload, Exe, ECORE_EXE_PIPE_READ, ECORE_EXE_PIPE_READ_LINE_BUFFERED


def DBG(msg):
   print('UTILS: ' + str(msg))
   pass


emc_version = '1.0.0-beta0'
emc_base_dir = os.path.dirname(__file__)
user_conf_dir = os.path.expanduser('~/.config/epymc') # TODO use xdg-stuff

DBG('emc_base_dir: %s' % emc_base_dir)
DBG('user_conf_dir: %s' % user_conf_dir)


def get_resource_file(res_type, res_name, default = None):
   """
   This will search the given reasource (the file name) first in user config
   directory (usually ~/.config/epymc) and then inside the package dir
   Example:
      full_path = get_resource_file('themes', 'mytheme.edj', 'default.edj')
   """
   for res in [res_name, default]:
      # search in user config dir
      f = os.path.join(user_conf_dir, res_type, res)
      if os.path.exists(f):
         return f

      # search in the package base dir
      f = os.path.join(emc_base_dir, res_type, res)
      if os.path.exists(f):
         return f

   # not found :(
   return None

def get_available_themes():
   # first search in user config dir
   L = glob.glob(os.path.join(user_conf_dir, 'themes', '*.edj'))

   # then search inside the package
   L += glob.glob(os.path.join(emc_base_dir, 'themes', '*.edj'))

   return L

def url2path(url):
   # TODO ... convert the url to a local path !!
   return url[7:]

def hum_size(bytes):
   bytes = float(bytes)
   if bytes >= 1099511627776:
      terabytes = bytes / 1099511627776
      size = '%.2fT' % terabytes
   elif bytes >= 1073741824:
      gigabytes = bytes / 1073741824
      size = '%.2fG' % gigabytes
   elif bytes >= 1048576:
      megabytes = bytes / 1048576
      size = '%.2fM' % megabytes
   elif bytes >= 1024:
      kilobytes = bytes / 1024
      size = '%.2fK' % kilobytes
   else:
      size = '%.2fb' % bytes
   return size

def splitpath(path):
   """ Convert a string path in a list of all the components """
   return [p for p in path.split(os.path.sep) if p != '']

def ensure_file_not_exists(fullpath):
   """ Add a number at the end of the file name to ensure it do not exists """
   if not os.path.exists(fullpath):
      return fullpath

   num = 1
   name, ext = os.path.splitext(fullpath)
   while True:
      new = name + '_%03d' % num + ext
      if not os.path.exists(new):
         return new
      num += 1

def natural_sort(l): 
   convert = lambda text: int(text) if text.isdigit() else text.lower() 
   alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)] 
   return sorted(l, key=alphanum_key)

def grab_files(folders, show_hidden=False, recursive=True):
   """
   This is a generator function, you give a list of directories to
   scan (recursively or not) and the generator will return all the files
   path, one file on each next() call.

   Usage:

   # in a for loop
   for filename in self.grab_files(['/path/1', '/path/2/other']):
      print(filename)

   # or asynchrony ;)
   generator = self.grab_files(['/path/1', '/path/2/other'])
      ...
   try:
      filename = generator.next()
      print(filename)
   except StopIteration:
      print('file list done')

   """
   for folder in folders:
      if folder.startswith('file://'): # mhhhh...
         folder = folder[7:]
      for name in os.listdir(folder):
         if show_hidden or name[0] != '.':
            full_path = os.path.join(folder, name)
            if os.access(full_path, os.R_OK):
               # not recursive version
               if not recursive:
                  yield full_path
               # the recursive one
               elif os.path.isdir(full_path):
                  for entry in grab_files([full_path]):
                     yield entry
               elif os.path.isfile(full_path):
                  yield full_path
               else:
                  print('Unidentified name %s. It could be a symbolic link' % full_path)

def download_url_async(url, dest='tmp', min_size=0,
                       complete_cb=None, progress_cb=None,
                       urlencode=True, *args, **kargs):
   """Download the given url in async way.

   TODO:
      If dest is set to None than the data will be passed as the dest param
      in the complete_cb.

   Args:
      url: must be a valid url to download.
      dest: If set to a local file name then the download data will be written
         to that file (created and overwritten if necessary, also the
         necessary parent directories are created).
         If dest is omitted (or is 'tmp') than the data will be written
         to a random new temp file.
      min_size: if min_size is set (and > 0) than downloaded files smaller that
         min_size will be discarted.
      complete_cb: if given, will be called when the download is done.
         signature: complete_cb(file, status, *args, **kargs)
      progress_cb: will be called while the download is in progress.
         signature: progress_cb(file, dltotal, dlnow, *args, **kargs)
      urlencode: encode the given url (default to True).
      *args: any other arguments will be passed back in the callbacks.
      **kargs: any other keyword arguments will be passed back in the callbacks.

   Returns:
      The Ecore FileDownload instance

   """

   def _cb_download_complete(dest, status, dwl_data, *args, **kargs):
      (complete_cb, progress_cb, min_size) = dwl_data

      # if file size < min_size: report as error
      if status == 200 and min_size > 0 and os.path.getsize(dest) < min_size:
         DBG('MIN_SIZE not reached, discard download')
         status = 404 # HTTP NotFound code

      # on errors delete the downloaded file
      if status != 200 and os.path.exists(dest):
         DBG('download error, HTTP code: ' + str(status))
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
   if urlencode:
      (_prot, _url) = url.split('://', 1)
      encoded = '://'.join((_prot, urllib_quote(_url)))
   else:
      encoded = url

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
   return FileDownload(encoded, dest, _cb_download_complete,
                  _cb_download_progress, dwl_data = dwl_data, *args, **kargs)

def download_abort(dwl_handler):
   ecore.file_download_abort(dwl_handler)


class Singleton(object):
   __single = None

   def __new__(classtype, *args, **kwargs):
      if classtype != type(classtype.__single):
         classtype.__single = object.__new__(classtype, *args, **kwargs)
      return classtype.__single


class EmcExec(object):
   """
   Just a tiny wrapper around ecore.Exe to execute shell command async
   cmd: the command to execute
   grab_output: whenever to collect the stdoutput
   done_cb: function to call when the program ends. Will receive one argument:
            the standard output of the command or an empty string if
            grab_input is False (the default)
            done_cb will also receive any other params you pass to the costructor
   """
   def __init__(self, cmd, grab_output = False, done_cb = None, *args, **kargs):
      self.done_cb = done_cb
      self.args = args
      self.kargs = kargs
      self.grab_output = grab_output
      self.outbuffer = ''
      if grab_output:
         self.exe = Exe(cmd, ECORE_EXE_PIPE_READ | ECORE_EXE_PIPE_READ_LINE_BUFFERED)
         self.exe.on_data_event_add(self.data_cb)
      else:
         self.exe = ecore.Exe(cmd)
      if done_cb:
         self.exe.on_del_event_add(self.del_cb)

   def data_cb(self, exe, event):
      for l in event.lines:
         self.outbuffer += (l + '\n')

   def del_cb(self, exe, event):
      if callable(self.done_cb):
         self.done_cb(self.outbuffer, *self.args, **self.kargs)

