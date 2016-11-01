# This Python file uses the following encoding: utf-8

import os
import shutil


def DBG(txt):
   print(txt)
   pass


def copy(source, destination):
   DBG("VFS copy({}, {})".format(source, destination))
   try:
      shutil.copy(source, destination)
   except:
      return False
   return True


def delete(path):
   DBG("VFS delete({})".format(path))
   try:
      os.remove(path)
   except:
      return False
   return True


def exists(path):
   DBG("VFS exists({})".format(path))
   return os.path.exists(path)


def listdir(path):
   DBG("VFS listdir({})".format(path))
   files, dirs = [], []
   for fname in os.listdir(path):
      if os.path.isdir(os.path.join(path, fname)):
         dirs.append(fname)
      else:
         files.append(fname)
   return (dirs, files)


def mkdir(path):
   DBG("VFS mkdir({})".format(path))
   try:
      os.makedir(path)
   except:
      return False
   return True


def mkdirs(path):
   DBG("VFS mkdirs({})".format(path))
   try:
      os.makedirs(path)
   except:
      return False
   return True


def rename(file, newFileName):
   DBG("VFS rename({}, {})".format(file, newFileName))
   try:
      os.rename(file, newFileName)
   except:
      return False
   return True


def rmdir(path):
   DBG("VFS rmdir({})".format(path))
   try:
      os.rmdir(path)
   except:
      return False
   return True


class File(object):

   @NOT_IMPLEMENTED
   def __init__(self, *args, **kargs):
      pass


class Stat(object):

   @NOT_IMPLEMENTED
   def __init__(self, *args, **kargs):
      pass
