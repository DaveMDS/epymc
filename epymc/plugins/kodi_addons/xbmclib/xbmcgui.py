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

   def addContextMenuItems(self, items, replaceItems=False):
      print('NOT IMPLEMENTED: addContextMenuItems(items:{})'.format(len(items)))

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

   def __init__(self):
      self._class_id = str(random.randint(1, 2**32))
      print("NOT IMPLEMENTED: Dialog()")

   def browse(self, type, heading, shares, mask=None, useThumb=False,
              treatAsFolder=False, default=None, enableMultiple=False):
      print("NOT IMPLEMENTED: Dialog.browse()")
      return None

   def browseMultiple(self, type, heading, shares, mask=None, useThumb=False,
                      treatAsFolder=False, default=None):
      print("NOT IMPLEMENTED: Dialog.browseMultiple()")
      return None

   def browseSingle(self, type, heading, shares, mask=None, useThumb=False,
                    treatAsFolder=False, default=None):
      print("NOT IMPLEMENTED: Dialog.browseSingle()")
      return None

   def input(self, heading, default='', type=INPUT_ALPHANUM, option=None,
             autoclose=0):
      print("NOT IMPLEMENTED: Dialog.input()")
      return ''

   def multiselect(self, heading, list, autoclose=0):
      print("NOT IMPLEMENTED: Dialog.multiselect()")
      return None

   def notification(self, heading, message, icon=NOTIFICATION_INFO, time=5000,
                    sound=True):
      print("NOT IMPLEMENTED: Dialog.notification()")

   def numeric(self, type, heading, default=None):
      print("NOT IMPLEMENTED: Dialog.numeric()")
      return default

   def ok(self, heading, line1, line2=None, line3=None):
      print("NOT IMPLEMENTED: Dialog.ok()")
      return False

   def select(self, heading, list):
      print("NOT IMPLEMENTED: Dialog.select()")
      return 0

   def textviewer(self, heading, text):
      print("NOT IMPLEMENTED: Dialog.textviewer()")

   def yesno(self, heading, line1, line2=None, line3=None, nolabel=None,
             yeslabel=None, autoclose=0):
      print("NOT IMPLEMENTED: Dialog.yesno()")
      return False


class DialogProgress(object):

   def __init__(self):
      self._class_id = str(random.randint(1, 2**32))
      print("NOT IMPLEMENTED: DialogProgress()")

   def close(self):
      print("NOT IMPLEMENTED: DialogProgress.close()")

   def create(self, heading, line1=None, line2=None, line3=None):
      print("NOT IMPLEMENTED: DialogProgress.create()")

   def iscanceled(self):
      print("NOT IMPLEMENTED: DialogProgress.iscanceled()")
      return False

   def update(self, pecent, line1=None, line2=None, line3=None):
      print("NOT IMPLEMENTED: DialogProgress.update()")


class DialogProgressBG(object):

   def __init__(self):
      self._class_id = str(random.randint(1, 2**32))
      print("NOT IMPLEMENTED: DialogProgressBG()")

   def close(self):
      print("NOT IMPLEMENTED: DialogProgressBG.close()")

   def create(self, heading, message=None):
      print("NOT IMPLEMENTED: DialogProgressBG.create()")

   def isFinished(self):
      print("NOT IMPLEMENTED: DialogProgressBG.isFinished()")

   def update(self, percent=None, heading=None, message=None):
      print("NOT IMPLEMENTED: DialogProgressBG.update()")
