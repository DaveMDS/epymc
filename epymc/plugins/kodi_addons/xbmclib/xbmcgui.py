# This Python file uses the following encoding: utf-8


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

   def __init__(self, label='', label2=None, iconImage=None, thumbnailImage=None, path=None):
      self.path = path
      self.label = label
      self.label2 = label2
      self.infoLabels = LowerCaseDict()
      self.properties = LowerCaseDict()
      self.art = LowerCaseDict()
      if iconImage: # deprecated (use art instead)
         self.art['icon'] = iconImage
      if thumbnailImage: # deprecated (use art instead)
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

   def setInfo(self, type=None, infoLabels={}):
      self.infoLabels.update(infoLabels)
      
   def setProperty(self, key, value):
      self.properties[key] = value

   def getProperty(self, key):
      return self.properties.get(key)

   def setArt(self, values):
      self.art.update(values)

   def setThumbnailImage(self, thumb):
      """ deprecated  (use art instead) """
      self.art['thumb'] = thumb
