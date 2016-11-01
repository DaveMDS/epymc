# This Python file uses the following encoding: utf-8

import random


class LowerCaseDict(dict):
   """  A dict with always lowered keys """
   def __setitem__(self, key, val):
      dict.__setitem__(self, key.lower(), val)

   def __getitem__(self, key):
      dict.__getitem__(self, key.lower())

   def update(self, other):
      for key in other:
         self[key] = other[key]


class ListItem(object):

   def __init__(self, label='', label2=None, iconImage=None,
                thumbnailImage=None, path=None):
      self.path = path
      self.label = label
      self.label2 = label2
      self.infoLabels = LowerCaseDict()
      self.properties = LowerCaseDict()
      self.art = LowerCaseDict()
      self.streamInfo = LowerCaseDict()
      if iconImage:  # deprecated (use art instead)
         self.art['icon'] = iconImage
      if thumbnailImage:  # deprecated (use art instead)
         self.art['thumb'] = thumbnailImage

   def __repr__(self):
      return str(self.__dict__)

   def setLabel(self, label):
      self.label = label

   def getLabel(self):
      return self.label

   def setLabel2(self, label2):
      self.label2 = label2

   def getLabel2(self):
      return self.label2

   def setPath(self, path):
      self.path = path

   def getPath(self):
      return self.path

   def setArt(self, values):
      self.art.update(values)

   def setInfo(self, type=None, infoLabels={}):
      self.infoLabels.update(infoLabels)

   def addStreamInfo(self, type=None, values={}):
      self.streamInfo.update(values)

   def setProperty(self, key, value):
      self.properties[key] = value

   def getProperty(self, key):
      return self.properties.get(key)

   @NOT_IMPLEMENTED
   def addContextMenuItems(self, items, replaceItems=False):
      print('NOT IMPLEMENTED: addContextMenuItems(...)')

   def setThumbnailImage(self, thumb):
      """ deprecated  (use art instead) """
      self.art['thumb'] = thumb

   def setIconImage(self, icon):
      """ deprecated  (use art instead) """
      self.art['icon'] = icon


ALPHANUM_HIDE_INPUT = 2
INPUT_ALPHANUM = 0
INPUT_DATE = 2
INPUT_IPADDRESS = 4
INPUT_NUMERIC = 1
INPUT_PASSWORD = 5
INPUT_TIME = 3
NOTIFICATION_ERROR = 'error'
NOTIFICATION_INFO = 'info'
NOTIFICATION_WARNING = 'warning'
PASSWORD_VERIFY = 1


class Dialog(object):

   @NOT_IMPLEMENTED
   def __init__(self):
      self._class_id = str(random.randint(1, 2**32))

   @NOT_IMPLEMENTED
   def browse(self, type, heading, shares, mask=None, useThumb=False,
              treatAsFolder=False, default=None, enableMultiple=False):
      return None

   @NOT_IMPLEMENTED
   def browseMultiple(self, type, heading, shares, mask=None, useThumb=False,
                      treatAsFolder=False, default=None):
      return None

   @NOT_IMPLEMENTED
   def browseSingle(self, type, heading, shares, mask=None, useThumb=False,
                    treatAsFolder=False, default=None):
      return None

   @NOT_IMPLEMENTED
   def input(self, heading, default='', type=INPUT_ALPHANUM, option=None,
             autoclose=0):
      return ''

   @NOT_IMPLEMENTED
   def multiselect(self, heading, list, autoclose=0):
      return None

   @NOT_IMPLEMENTED
   def notification(self, heading, message, icon=NOTIFICATION_INFO, time=5000,
                    sound=True):
      pass

   @NOT_IMPLEMENTED
   def numeric(self, type, heading, default=None):
      return default

   @NOT_IMPLEMENTED
   def ok(self, heading, line1, line2=None, line3=None):
      return False

   @NOT_IMPLEMENTED
   def select(self, heading, list):
      return 0

   @NOT_IMPLEMENTED
   def textviewer(self, heading, text):
      pass

   @NOT_IMPLEMENTED
   def yesno(self, heading, line1, line2=None, line3=None, nolabel=None,
             yeslabel=None, autoclose=0):
      return False


class DialogProgress(object):

   @NOT_IMPLEMENTED
   def __init__(self):
      self._class_id = str(random.randint(1, 2**32))

   @NOT_IMPLEMENTED
   def close(self):
      pass

   @NOT_IMPLEMENTED
   def create(self, heading, line1=None, line2=None, line3=None):
      pass

   @NOT_IMPLEMENTED
   def iscanceled(self):
      return False

   @NOT_IMPLEMENTED
   def update(self, pecent, line1=None, line2=None, line3=None):
      pass


class DialogProgressBG(object):

   @NOT_IMPLEMENTED
   def __init__(self):
      self._class_id = str(random.randint(1, 2**32))

   @NOT_IMPLEMENTED
   def close(self):
      pass

   @NOT_IMPLEMENTED
   def create(self, heading, message=None):
      pass

   @NOT_IMPLEMENTED
   def isFinished(self):
      pass

   @NOT_IMPLEMENTED
   def update(self, percent=None, heading=None, message=None):
      pass

