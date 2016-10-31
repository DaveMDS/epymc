# This Python file uses the following encoding: utf-8

import os
import sys



def translatePath(path):
   """ http://kodi.wiki/view/Special_protocol """

   if path.startswith('special://'):
      path = path.replace('special://', '', 1)
      base = os.path.expanduser('~/.config/epymc/kodi')

      if '/' in path:
         tag, path = path.split('/', 1)
      else:
         tag, path = path, ''

      if tag == 'home':
         return os.path.join(base, path)

      elif tag == 'temp':
         return os.path.join(base, 'temp', path)

      elif tag in ('masterprofile', 'profile', 'userdata'):
         return os.path.join(base, 'userdata', path)

      elif tag == 'database':
         return os.path.join(base, 'userdata', 'Database', path)

      elif tag == 'thumbnails':
         return os.path.join(base, 'userdata', 'Thumbnails', path)

      # TODO: subtitles, recordings, screenshots, musicplaylists,
      #       videoplaylists, cdrips, skin, logpath

   elif os.path.exists(path):
      return path

   print("UNSUPPORTED SPECIAL PATH:", path)
   return None


LOGDEBUG = 0
LOGINFO = 1
LOGNOTICE = 2
LOGWARNING = 3
LOGERROR = 4
LOGSEVERE = 5
LOGFATAL = 6
LOGNONE = 7

def log(msg, level=LOGNOTICE):
   print(msg)

def executebuiltin(function):
   print('NOT IMPLEMENTED: executebuiltin ("{}")'.format(function))


class Player(object):

   def __init__(self):
      self._class_id = None # this will be passed back in methods to emc

   @emc_method_call
   def play(self, item=None, listitem=None, windowed=False, startpos=-1):
      pass


@emc_function_call
def getInfoLabel(infotag):
   return emc_wait_replay()


def getSkinDir():
   return 'MediaCenter'
