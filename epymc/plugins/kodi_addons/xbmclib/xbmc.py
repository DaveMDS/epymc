# This Python file uses the following encoding: utf-8

import os
import sys


#  defines   ###################################################################
CAPTURE_FLAG_CONTINUOUS = 1
CAPTURE_FLAG_IMMEDIATELY = 2
CAPTURE_STATE_DONE = 3
CAPTURE_STATE_FAILED = 4
CAPTURE_STATE_WORKING = 0
DRIVE_NOT_READY = 1
ENGLISH_NAME = 2
ISO_639_1 = 0
ISO_639_2 = 1
LOGDEBUG = 0
LOGERROR = 4
LOGFATAL = 6
LOGINFO = 1
LOGNONE = 7
LOGNOTICE = 2
LOGSEVERE = 5
LOGWARNING = 3
PLAYER_CORE_AUTO = 0
PLAYER_CORE_DVDPLAYER = 1
PLAYER_CORE_MPLAYER = 2
PLAYER_CORE_PAPLAYER = 3
PLAYLIST_MUSIC = 0
PLAYLIST_VIDEO = 1
SERVER_AIRPLAYSERVER = 2
SERVER_EVENTSERVER = 6
SERVER_JSONRPCSERVER = 3
SERVER_UPNPRENDERER = 4
SERVER_UPNPSERVER = 5
SERVER_WEBSERVER = 1
SERVER_ZEROCONF = 7
TRAY_CLOSED_MEDIA_PRESENT = 96
TRAY_CLOSED_NO_MEDIA = 64
TRAY_OPEN = 16


#  module level functions  #####################################################

@NOT_IMPLEMENTED
def audioResume():
   pass


@NOT_IMPLEMENTED
def audioSuspend():
   pass


@NOT_IMPLEMENTED
def convertLanguage(language, format):
   pass


@NOT_IMPLEMENTED
def enableNavSounds(yesNo):
   pass


@emc_function_call
def executeJSONRPC(jsonrpccommand):
   return emc_wait_reply()


@emc_function_call
def executebuiltin(function):
   pass


@NOT_IMPLEMENTED
def executescript(script):
   pass


@NOT_IMPLEMENTED
def getCacheThumbName(path):
   pass


@NOT_IMPLEMENTED
def getCleanMovieTitle(path, usefoldername=False):
   pass


@NOT_IMPLEMENTED
def getCondVisibility(condition):
   return False


@NOT_IMPLEMENTED
def getDVDState():
   return DRIVE_NOT_READY


@NOT_IMPLEMENTED
def getFreeMem():
   return 100


@NOT_IMPLEMENTED
def getGlobalIdleTime():
   return 1


@NOT_IMPLEMENTED
def getIPAddress():
   return '127.0.0.1'


@NOT_IMPLEMENTED
def getInfoImage(infotag):
   pass


@emc_function_call
def getInfoLabel(infotag):
   return emc_wait_reply()


@NOT_IMPLEMENTED
def getLanguage(format, region):
   pass


@NOT_IMPLEMENTED
def getLocalizedString(id):
   pass


@NOT_IMPLEMENTED
def getRegion(id):
   pass


def getSkinDir():
   return 'skin.confluence'


@NOT_IMPLEMENTED
def getSupportedMedia(media):
   pass


def log(msg, level=LOGNOTICE):
   print(msg)


@NOT_IMPLEMENTED
def makeLegalFilename(filename, fatX=True):
   pass


@NOT_IMPLEMENTED
def playSFX(filename, useCached=True):
   pass


@NOT_IMPLEMENTED
def restart():
   pass


@NOT_IMPLEMENTED
def shutdown():
   pass


@NOT_IMPLEMENTED
def skinHasImage(image):
   pass


@NOT_IMPLEMENTED
def sleep(time):
   pass


@NOT_IMPLEMENTED
def startServer(typ, bStart, bWait):
   return False


@NOT_IMPLEMENTED
def stopSFX():
   pass


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


@NOT_IMPLEMENTED
def validatePath(path):
   pass


#  The Player class  ###########################################################
class Player(object):

   def __init__(self):
      self._class_id = None  # this will be passed back in methods to emc

   @NOT_IMPLEMENTED
   def disableSubtitles(self):
      pass

   @NOT_IMPLEMENTED
   def getAvailableAudioStreams(self):
      pass

   @NOT_IMPLEMENTED
   def getAvailableSubtitleStreams(self):
      pass

   @NOT_IMPLEMENTED
   def getMusicInfoTag(self):
      pass

   @NOT_IMPLEMENTED
   def getPlayingFile(self):
      pass

   @NOT_IMPLEMENTED
   def getRadioRDSInfoTag(self):
      pass

   @NOT_IMPLEMENTED
   def getSubtitles(self):
      pass

   @NOT_IMPLEMENTED
   def getTime(self):
      pass

   @NOT_IMPLEMENTED
   def getTotalTime(self):
      pass

   @NOT_IMPLEMENTED
   def getVideoInfoTag(self):
      pass

   @NOT_IMPLEMENTED
   def isPlaying(self):
      pass

   @NOT_IMPLEMENTED
   def isPlayingAudio(self):
      pass

   @NOT_IMPLEMENTED
   def isPlayingRDS(self):
      pass

   @NOT_IMPLEMENTED
   def isPlayingVideo(self):
      pass

   @NOT_IMPLEMENTED
   def onPlayBackEnded(self):
      pass

   @NOT_IMPLEMENTED
   def onPlayBackPaused(self):
      pass

   @NOT_IMPLEMENTED
   def onPlayBackResumed(self):
      pass

   @NOT_IMPLEMENTED
   def onPlayBackSeek(self, time, seekOffset):
      pass

   @NOT_IMPLEMENTED
   def onPlayBackSeekChapter(self, chapter):
      pass

   @NOT_IMPLEMENTED
   def onPlayBackSpeedChanged(self, speed):
      pass

   @NOT_IMPLEMENTED
   def onPlayBackStarted(self):
      pass

   @NOT_IMPLEMENTED
   def onPlayBackStopped(self):
      pass

   @NOT_IMPLEMENTED
   def onQueueNextItem(self):
      pass

   @NOT_IMPLEMENTED
   def pause(self):
      pass

   @emc_method_call
   def play(self, item=None, listitem=None, windowed=False, startpos=-1):
      pass

   @NOT_IMPLEMENTED
   def playnext(self):
      pass

   @NOT_IMPLEMENTED
   def playprevious(self):
      pass

   @NOT_IMPLEMENTED
   def playselected(self):
      pass

   @NOT_IMPLEMENTED
   def seekTime(self):
      pass

   @NOT_IMPLEMENTED
   def setAudioStream(self, stream):
      pass

   @NOT_IMPLEMENTED
   def setSubtitleStream(self, stream):
      pass

   @NOT_IMPLEMENTED
   def setSubtitles(self, file):
      pass

   @NOT_IMPLEMENTED
   def showSubtitles(self, visible):
      pass

   @NOT_IMPLEMENTED
   def stop(self):
      pass


#  The Playlist class  #########################################################
class Playlist(object):

   def __init__(self):
      self._class_id = None  # this will be passed back in methods to emc

   @NOT_IMPLEMENTED
   def add(self, url, listitem=None, index=-1):
      pass

   @NOT_IMPLEMENTED
   def clear(self):
      pass

   @NOT_IMPLEMENTED
   def getPlayListId(self):
      pass

   @NOT_IMPLEMENTED
   def getposition(self):
      pass

   @NOT_IMPLEMENTED
   def load(self, filename):
      pass

   @NOT_IMPLEMENTED
   def remove(self, filename):
      pass

   @NOT_IMPLEMENTED
   def shuffle(self):
      pass

   @NOT_IMPLEMENTED
   def size(self):
      pass

   @NOT_IMPLEMENTED
   def unshuffle(self):
      pass


#  The Monitor class  ##########################################################
class Monitor(object):

   def __init__(self):
      self._class_id = None  # this will be passed back in methods to emc

   @NOT_IMPLEMENTED
   def abortRequested(self):
      pass

   @NOT_IMPLEMENTED
   def onAbortRequested(self):
      pass

   @NOT_IMPLEMENTED
   def onCleanFinished(self, library):
      pass

   @NOT_IMPLEMENTED
   def onCleanStarted(self, library):
      pass

   @NOT_IMPLEMENTED
   def onDPMSActivated(self):
      pass

   @NOT_IMPLEMENTED
   def onDatabaseScanStarted(self, database):
      pass

   @NOT_IMPLEMENTED
   def onDatabaseUpdated(self, database):
      pass

   @NOT_IMPLEMENTED
   def onNotification(self, sender, method, data):
      pass

   @NOT_IMPLEMENTED
   def onScanFinished(self, library):
      pass

   @NOT_IMPLEMENTED
   def onScanStarted(self, library):
      pass

   @NOT_IMPLEMENTED
   def onScreensaverActivated(self):
      pass

   @NOT_IMPLEMENTED
   def onScreensaverDeactivated(self):
      pass

   @NOT_IMPLEMENTED
   def onSettingsChanged(self):
      pass

   @NOT_IMPLEMENTED
   def waitForAbort(self, timeout=0.0):
      pass


#  The Keyboard class  #########################################################
class Keyboard(object):

   def __init__(self, default=None, heading=None, hidden=None):
      self._class_id = None  # this will be passed back in methods to emc

   @NOT_IMPLEMENTED
   def doModal(self, autoclose=-1):
      pass

   @NOT_IMPLEMENTED
   def getText(self):
      return ''

   @NOT_IMPLEMENTED
   def isConfirmed(self):
      return False

   @NOT_IMPLEMENTED
   def setDefault(self, default):
      pass

   @NOT_IMPLEMENTED
   def setHeading(self, heading):
      pass

   @NOT_IMPLEMENTED
   def setHiddenInput(self, hidden):
      pass


#  The InfoTagVideo class  #####################################################
class InfoTagVideo(object):

   def __init__(self):
      self._class_id = None  # this will be passed back in methods to emc

   @NOT_IMPLEMENTED
   def getCast(self):
      return ''

   @NOT_IMPLEMENTED
   def getDirector(self):
      return ''

   @NOT_IMPLEMENTED
   def getFile(self):
      return ''

   @NOT_IMPLEMENTED
   def getFirstAired(self):
      return ''

   @NOT_IMPLEMENTED
   def getGenre(self):
      return ''

   @NOT_IMPLEMENTED
   def getIMDBNumber(self):
      return ''

   @NOT_IMPLEMENTED
   def getLastPlayed(self):
      return ''

   @NOT_IMPLEMENTED
   def getOriginalTitle(self):
      return ''

   @NOT_IMPLEMENTED
   def getPath(self):
      return ''

   @NOT_IMPLEMENTED
   def getPictureURL(self):
      return ''

   @NOT_IMPLEMENTED
   def getPlayCount(self):
      return 0

   @NOT_IMPLEMENTED
   def getPlot(self):
      return ''

   @NOT_IMPLEMENTED
   def getPlotOutline(self):
      return ''

   @NOT_IMPLEMENTED
   def getPremiered(self):
      return ''

   @NOT_IMPLEMENTED
   def getRating(self):
      return 0.0

   @NOT_IMPLEMENTED
   def getTagLine(self):
      return ''

   @NOT_IMPLEMENTED
   def getTitle(self):
      return ''

   @NOT_IMPLEMENTED
   def getVotes(self):
      return ''

   @NOT_IMPLEMENTED
   def getWritingCredits(self):
      return ''

   @NOT_IMPLEMENTED
   def getYear(self):
      return 1970


#  The InfoTagMusic class  #####################################################
class InfoTagMusic(object):

   def __init__(self):
      self._class_id = None  # this will be passed back in methods to emc

   @NOT_IMPLEMENTED
   def getAlbum(self):
      return ''

   @NOT_IMPLEMENTED
   def getAlbumArtist(self):
      return ''

   @NOT_IMPLEMENTED
   def getArtist(self):
      return ''

   @NOT_IMPLEMENTED
   def getComment(self):
      return ''

   @NOT_IMPLEMENTED
   def getDisc(self):
      return ''

   @NOT_IMPLEMENTED
   def getDuration(self):
      return 0

   @NOT_IMPLEMENTED
   def getGenre(self):
      return ''

   @NOT_IMPLEMENTED
   def getLastPlayed(self):
      return ''

   @NOT_IMPLEMENTED
   def getListeners(self):
      return 0

   @NOT_IMPLEMENTED
   def getLyrics(self):
      return ''

   @NOT_IMPLEMENTED
   def getPlayCount(self):
      return 0

   @NOT_IMPLEMENTED
   def getReleaseDate(self):
      return ''

   @NOT_IMPLEMENTED
   def getTitle(self):
      return ''

   @NOT_IMPLEMENTED
   def getTrack(self):
      return 0

   @NOT_IMPLEMENTED
   def getURL(self):
      return ''


#  The InfoTagRadioRDS class  ##################################################
class InfoTagRadioRDS(object):

   def __init__(self):
      self._class_id = None  # this will be passed back in methods to emc

   @NOT_IMPLEMENTED
   def getAlbum(self):
      return ''

   @NOT_IMPLEMENTED
   def getAlbumTrackNumber(self):
      return 0

   @NOT_IMPLEMENTED
   def getArtist(self):
      return ''

   @NOT_IMPLEMENTED
   def getBand(self):
      return ''

   @NOT_IMPLEMENTED
   def getComment(self):
      return ''

   @NOT_IMPLEMENTED
   def getComposer(self):
      return ''

   @NOT_IMPLEMENTED
   def getConductor(self):
      return ''

   @NOT_IMPLEMENTED
   def getEMailHotline(self):
      return ''

   @NOT_IMPLEMENTED
   def getEMailStudio(self):
      return ''

   @NOT_IMPLEMENTED
   def getEditorialStaff(self):
      return ''

   @NOT_IMPLEMENTED
   def getInfoCinema(self):
      return ''

   @NOT_IMPLEMENTED
   def getInfoHoroscope(self):
      return ''

   @NOT_IMPLEMENTED
   def getInfoLottery(self):
      return ''

   @NOT_IMPLEMENTED
   def getInfoNews(self):
      return ''

   @NOT_IMPLEMENTED
   def getInfoNewsLocal(self):
      return ''

   @NOT_IMPLEMENTED
   def getInfoOther(self):
      return ''

   @NOT_IMPLEMENTED
   def getInfoSport(self):
      return ''

   @NOT_IMPLEMENTED
   def getInfoStock(self):
      return ''

   @NOT_IMPLEMENTED
   def getInfoWeather(self):
      return ''

   @NOT_IMPLEMENTED
   def getPhoneHotline(self):
      return ''

   @NOT_IMPLEMENTED
   def getPhoneStudio(self):
      return ''

   @NOT_IMPLEMENTED
   def getProgHost(self):
      return ''

   @NOT_IMPLEMENTED
   def getProgNext(self):
      return ''

   @NOT_IMPLEMENTED
   def getProgNow(self):
      return ''

   @NOT_IMPLEMENTED
   def getProgStation(self):
      return ''

   @NOT_IMPLEMENTED
   def getProgStyle(self):
      return ''

   @NOT_IMPLEMENTED
   def getProgWebsite(self):
      return ''

   @NOT_IMPLEMENTED
   def getSMSStudio(self):
      return ''

   @NOT_IMPLEMENTED
   def getTitle(self):
      return ''


#  The RenderCapture class  ####################################################
class RenderCapture(object):

   def __init__(self):
      self._class_id = None  # this will be passed back in methods to emc

   @NOT_IMPLEMENTED
   def capture(self, width, height, flags=None):
      pass

   @NOT_IMPLEMENTED
   def getAspectRatio(self):
      return None

   @NOT_IMPLEMENTED
   def getCaptureState(self):
      return CAPTURE_STATE_FAILED

   @NOT_IMPLEMENTED
   def getHeight(self):
      return 0

   @NOT_IMPLEMENTED
   def getImage(self):
      return None

   @NOT_IMPLEMENTED
   def getImageFormat(self):
      return None

   @NOT_IMPLEMENTED
   def getWidth(self):
      return 0

   @NOT_IMPLEMENTED
   def waitForCaptureStateChangeEvent(self, msecs=0):
      return 0
