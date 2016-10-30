# This Python file uses the following encoding: utf-8



SORT_METHOD_ALBUM = 14
SORT_METHOD_ALBUM_IGNORE_THE = 15
SORT_METHOD_ARTIST = 11
SORT_METHOD_ARTIST_IGNORE_THE = 13
SORT_METHOD_BITRATE = 42
SORT_METHOD_CHANNEL = 40
SORT_METHOD_COUNTRY = 17
SORT_METHOD_DATE = 3
SORT_METHOD_DATEADDED = 21
SORT_METHOD_DATE_TAKEN = 43
SORT_METHOD_DRIVE_TYPE = 6
SORT_METHOD_DURATION = 8
SORT_METHOD_EPISODE = 24
SORT_METHOD_FILE = 5
SORT_METHOD_FULLPATH = 34
SORT_METHOD_GENRE = 16
SORT_METHOD_LABEL = 1
SORT_METHOD_LABEL_IGNORE_FOLDERS = 35
SORT_METHOD_LABEL_IGNORE_THE = 2
SORT_METHOD_LASTPLAYED = 36
SORT_METHOD_LISTENERS = 38
SORT_METHOD_MPAA_RATING = 30
SORT_METHOD_NONE = 0
SORT_METHOD_PLAYCOUNT = 37
SORT_METHOD_PLAYLIST_ORDER = 23
SORT_METHOD_PRODUCTIONCODE = 28
SORT_METHOD_PROGRAM_COUNT = 22
SORT_METHOD_SIZE = 4
SORT_METHOD_SONG_RATING = 29
SORT_METHOD_STUDIO = 32
SORT_METHOD_STUDIO_IGNORE_THE = 33
SORT_METHOD_TITLE = 9
SORT_METHOD_TITLE_IGNORE_THE = 10
SORT_METHOD_TRACKNUM = 7
SORT_METHOD_UNSORTED = 39
SORT_METHOD_VIDEO_RATING = 19
SORT_METHOD_VIDEO_RUNTIME = 31
SORT_METHOD_VIDEO_SORT_TITLE = 26
SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE = 27
SORT_METHOD_VIDEO_TITLE = 25
SORT_METHOD_VIDEO_USER_RATING = 20
SORT_METHOD_VIDEO_YEAR = 18

def addSortMethod(handle, sortMethod, label2Mask=None):
   print('NOT IMPLEMENTED: addSortMethod')


def addDirectoryItem(handle, url, listitem, isFolder=False, totalItems=1):
   kargs = {
      'handle': handle,
      'url': url,
      'listitem': listitem,
      'isFolder': isFolder,
      'totalItems': totalItems,
   }
   print('addDirectoryItem {}'.format(kargs))
   return True

def addDirectoryItems(handle, items, totalItems=1):
   for url, listitem, isFolder in items:
      addDirectoryItem(handle, url, listitem, isFolder, totalItems)
   return True

def setContent(handle, content):
   print('NOT IMPLEMENTED: setContent')
   # content: files, songs, artists, albums, movies, tvshows, episodes, musicvideos

def endOfDirectory(handle, succeeded=True, updateListing=False, cacheToDisc=True):
   kargs = {
      'succeeded': succeeded,
      'updateListing': updateListing,
      'cacheToDisc': cacheToDisc,
   }
   print('endOfDirectory {}'.format(kargs))


def setResolvedUrl(handle, succeeded, listitem):
   kargs = {
      'succeeded': succeeded,
      'listitem': listitem,
   }
   print('setResolvedUrl {}'.format(kargs))
   
   
