# This Python file uses the following encoding: utf-8

class ListItem(object):

   def __init__(self, label='', label2=None, iconImage=None, thumbnailImage=None, path=None):
      self.label = label
      self.label2 = label2
      self.iconImage = iconImage
      self.thumbnailImage = thumbnailImage
      self.path = path
      self.infoLabels = {}
      self.properties = {}
      self.art = {}

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

   def setInfo(self, type=None, infoLabels={}):
      self.infoLabels = infoLabels
      
   def setProperty(self, key, value):
      self.properties[key] = value

   def getProperty(self, key):
      return self.properties.get(key)

   def setArt(self, values):
      self.art.update(values)
