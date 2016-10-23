# This Python file uses the following encoding: utf-8

import os

_home = os.path.expanduser('~/.config/epymc/kodi')
_temp = os.path.join(_home, 'temp')

def translatePath(path):
   """ http://kodi.wiki/view/Special_protocol """
   if path.startswith('special://home'):
      return path.replace('special://home', _home, 1)
   elif path.startswith('special://temp'):
      return path.replace('special://temp', _temp, 1)
   else:
      print("UNSUPPORTED PATH", path)
      
   return None # or path ?


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
   


class Player(object):
   def __init__(self):
      pass

   def play(self, item=None, listitem=None, windowed=False, startpos=-1):
      kargs = {
         'item': item,
         'listitem': listitem,
         'windowed': windowed,
         'startpos': startpos,
      }
      print('Player_play {}'.format(kargs))
