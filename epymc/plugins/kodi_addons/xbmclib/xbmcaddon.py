# This Python file uses the following encoding: utf-8


class Addon(object):

   def __init__(self, id=None):
      self.id = id or addon_id  # addon_id comes from sitecustomize.py
      self._class_id = self.id  # this will be passed back in methods to emc

   @emc_method_call
   def getAddonInfo(self, id):
      return emc_wait_reply()

   @emc_method_call
   def getSetting(self, id):
      return emc_wait_reply()

   @emc_method_call
   def setSetting(self, id, value):
      pass

   @emc_method_call
   def openSettings(self):
      pass

   @emc_method_call
   def getLocalizedString(self, id):
      return emc_wait_reply()

