#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2016 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of EpyMC, an EFL based Media Center written in Python.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function

import sys, os, tempfile, glob, re, hashlib

try:
   from urllib.parse import quote as urllib_quote
except:
   from urllib import quote as urllib_quote

from efl import ecore
from efl import ecore_con
from efl.ecore import FileDownload, Exe, \
   ECORE_EXE_PIPE_READ, ECORE_EXE_PIPE_READ_LINE_BUFFERED


def DBG(msg):
   # print('UTILS: %s' % msg)
   pass


emc_base_dir = os.path.dirname(__file__)
user_conf_dir = os.path.expanduser('~/.config/epymc') # TODO use xdg-stuff
user_cache_dir = os.path.expanduser('~/.cache/epymc') # TODO use xdg-stuff
in_use_theme_file = None

supported_uris = ['file','http','https']
supported_mimes = ['application/mxf','application/ogg','application/ram', 
'application/sdp','application/smil','application/smil+xml','application/vnd.ms-wpl', 
'application/vnd.rn-realmedia','application/x-extension-m4a','application/x-extension-mp4', 
'application/x-flac','application/x-flash-video','application/x-matroska',
'application/x-netshow-channel','application/x-ogg','application/x-quicktime-media-link', 
'application/x-quicktimeplayer','application/x-shorten','application/x-smil', 
'application/xspf+xml','audio/3gpp','audio/ac3','audio/AMR','audio/AMR-WB', 
'audio/basic','audio/midi','audio/mp4','audio/mpeg','audio/mpegurl', 
'audio/ogg','audio/prs.sid','audio/vnd.rn-realaudio','audio/x-aiff','audio/x-ape', 
'audio/x-flac','audio/x-gsm','audio/x-it','audio/x-m4a','audio/x-matroska', 
'audio/x-mod','audio/x-mp3','audio/x-mpeg','audio/x-mpegurl','audio/x-ms-asf', 
'audio/x-ms-asx','audio/x-ms-wax','audio/x-ms-wma','audio/x-musepack', 
'audio/x-pn-aiff','audio/x-pn-au','audio/x-pn-realaudio','audio/x-pn-realaudio-plugin', 
'audio/x-pn-wav','audio/x-pn-windows-acm','audio/x-realaudio','audio/x-real-audio', 
'audio/x-sbc','audio/x-scpls','audio/x-speex','audio/x-tta','audio/x-wav','audio/x-wavpack', 
'audio/x-vorbis','audio/x-vorbis+ogg','audio/x-xm','image/vnd.rn-realpix','image/x-pict', 
'misc/ultravox','text/google-video-pointer','text/x-google-video-pointer','video/3gpp', 
'video/dv','video/fli','video/flv','video/mp2t','video/mp4','video/mp4v-es', 
'video/mpeg','video/msvideo','video/ogg','video/quicktime','video/vivo','video/vnd.divx', 
'video/vnd.rn-realvideo','video/vnd.vivo','video/webm','video/x-anim','video/x-avi', 
'video/x-flc','video/x-fli','video/x-flic','video/x-flv','video/x-m4v','video/x-matroska', 
'video/x-mpeg','video/x-ms-asf','video/x-ms-asx','video/x-msvideo','video/x-ms-wm', 
'video/x-ms-wmv','video/x-ms-wmx','video/x-ms-wvx','video/x-nsv','video/x-ogm+ogg', 
'video/x-theora+ogg','video/x-totem-stream','x-content/video-dvd','x-content/video-vcd', 
'x-content/video-svcd']

supported_images = ['.jpg', '.jpeg', '.png', '.gif']

iso639_table = {
#  'iso639-1': ('639-3', '639-5 / opensubtitles', 'Name')
# en.wikipedia.org/wiki/List_of_ISO_639-2_codes
# iso639-5 as for: www.opensubtitles.org/addons/export_languages.php
   'zu': ('zul', 'zul', 'Zulu'),
   'zh': ('zho', 'chi', 'Chinese'),#
   'za': ('zha', 'zha', 'Zhuang'),
   'yo': ('yor', 'yor', 'Yoruba'),
   'yi': ('yid', 'yid', 'Yiddish'),
   'xh': ('xho', 'xho', 'Xhosa'),
   'wo': ('wol', 'wol', 'Wolof'),
   'wa': ('wln', 'wln', 'Walloon'),
   'vo': ('vol', 'vol', 'Volapük'),
   'vi': ('vie', 'vie', 'Vietnamese'),
   've': ('ven', 'ven', 'Venda'),
   'uz': ('uzb', 'uzb', 'Uzbek'),
   'ur': ('urd', 'urd', 'Urdu'),
   'uk': ('ukr', 'ukr', 'Ukrainian'),
   'ug': ('uig', 'uig', 'Uighur'),
   'ty': ('tah', 'tah', 'Tahitian'),
   'tw': ('twi', 'twi', 'Twi'),
   'tt': ('tat', 'tat', 'Tatar'),
   'ts': ('tso', 'tso', 'Tsonga'),
   'tr': ('tur', 'tur', 'Turkish'),
   'to': ('ton', 'ton', 'Tonga (Tonga Islands)'),
   'tn': ('tsn', 'tsn', 'Tswana'),
   'tl': ('tgl', 'tgl', 'Tagalog'),
   'tk': ('tuk', 'tuk', 'Turkmen'),
   'ti': ('tir', 'tir', 'Tigrinya'),
   'th': ('tha', 'tha', 'Thai'),
   'tg': ('tgk', 'tgk', 'Tajik'),
   'te': ('tel', 'tel', 'Telugu'),
   'ta': ('tam', 'tam', 'Tamil'),
   'sw': ('swa', 'swa', 'Swahili (macrolanguage)'),
   'sv': ('swe', 'swe', 'Swedish'),
   'su': ('sun', 'sun', 'Sundanese'),
   'st': ('sot', 'sot', 'Southern Sotho'),
   'ss': ('ssw', 'ssw', 'Swati'),
   'sr': ('srp', 'scc', 'Serbian'),
   'sq': ('sqi', 'alb', 'Albanian'),
   'so': ('som', 'som', 'Somali'),
   'sn': ('sna', 'sna', 'Shona'),
   'sm': ('smo', 'smo', 'Samoan'),
   'sl': ('slv', 'slv', 'Slovenian'),
   'sk': ('slk', 'slo', 'Slovak'),
   'si': ('sin', 'sin', 'Sinhala'),
   'sg': ('sag', 'sag', 'Sango'),
   'se': ('sme', 'sme', 'Northern Sami'),
   'sd': ('snd', 'snd', 'Sindhi'),
   'sc': ('srd', 'srd', 'Sardinian'),
   'sa': ('san', 'san', 'Sanskrit'),
   'rw': ('kin', 'kin', 'Kinyarwanda'),
   'ru': ('rus', 'rus', 'Russian'),
   'ro': ('ron', 'rum', 'Romanian'),
   'rn': ('run', 'run', 'Rundi'),
   'rm': ('roh', 'roh', 'Romansh'),
   'qu': ('que', 'que', 'Quechua'),
   'pt': ('por', 'por', 'Portuguese'),
   'ps': ('pus', 'pus', 'Pushto'),
   'pl': ('pol', 'pol', 'Polish'),
   'pi': ('pli', 'pli', 'Pali'),
   'pa': ('pan', 'pan', 'Panjabi'),
   'os': ('oss', 'oss', 'Ossetian'),
   'or': ('ori', 'ori', 'Oriya (macrolanguage)'),
   'om': ('orm', 'orm', 'Oromo'),
   'oj': ('oji', 'oji', 'Ojibwa'),
   'oc': ('oci', 'oci', 'Occitan (post 1500)'),
   'ny': ('nya', 'nya', 'Nyanja'),
   'nv': ('nav', 'nav', 'Navajo'),
   'nr': ('nbl', 'nbl', 'South Ndebele'),
   'no': ('nor', 'nor', 'Norwegian'),
   'nn': ('nno', 'nno', 'Norwegian Nynorsk'),
   'nl': ('nld', 'dut', 'Dutch'),
   'ng': ('ndo', 'ndo', 'Ndonga'),
   'ne': ('nep', 'nep', 'Nepali (macrolanguage)'),
   'nd': ('nde', 'nde', 'North Ndebele'),
   'nb': ('nob', 'nob', 'Norwegian Bokmål'),
   'na': ('nau', 'nau', 'Nauru'),
   'my': ('mya', 'bur', 'Burmese'),
   'mt': ('mlt', 'mlt', 'Maltese'),
   'ms': ('msa', 'may', 'Malay (macrolanguage)'),
   'mr': ('mar', 'mar', 'Marathi'),
   'mn': ('mon', 'mon', 'Mongolian'),
   'ml': ('mal', 'mal', 'Malayalam'),
   'mk': ('mkd', 'mac', 'Macedonian'),
   'mi': ('mri', 'mao', 'Maori'),
   'mh': ('mah', 'mah', 'Marshallese'),
   'mg': ('mlg', 'mlg', 'Malagasy'),
   'lv': ('lav', 'lav', 'Latvian'),
   'lu': ('lub', 'lub', 'Luba-Katanga'),
   'lt': ('lit', 'lit', 'Lithuanian'),
   'lo': ('lao', 'lao', 'Lao'),
   'ln': ('lin', 'lin', 'Lingala'),
   'li': ('lim', 'lim', 'Limburgan'),
   'lg': ('lug', 'lug', 'Ganda'),
   'lb': ('ltz', 'ltz', 'Luxembourgish'),
   'la': ('lat', 'lat', 'Latin'),
   'ky': ('kir', 'kir', 'Kirghiz'),
   'kw': ('cor', 'cor', 'Cornish'),
   'kv': ('kom', 'kom', 'Komi'),
   'ku': ('kur', 'kur', 'Kurdish'),
   'ks': ('kas', 'kas', 'Kashmiri'),
   'kr': ('kau', 'kau', 'Kanuri'),
   'ko': ('kor', 'kor', 'Korean'),
   'kn': ('kan', 'kan', 'Kannada'),
   'km': ('khm', 'khm', 'Central Khmer'),
   'kl': ('kal', 'kal', 'Kalaallisut'),
   'kk': ('kaz', 'kaz', 'Kazakh'),
   'kj': ('kua', 'kua', 'Kuanyama'),
   'ki': ('kik', 'kik', 'Kikuyu'),
   'kg': ('kon', 'kon', 'Kongo'),
   'ka': ('kat', 'geo', 'Georgian'),
   'jv': ('jav', 'jav', 'Javanese'),
   'ja': ('jpn', 'jpn', 'Japanese'),
   'iu': ('iku', 'iku', 'Inuktitut'),
   'it': ('ita', 'ita', 'Italian'),
   'is': ('isl', 'ice', 'Icelandic'),
   'io': ('ido', 'ido', 'Ido'),
   'ik': ('ipk', 'ipk', 'Inupiaq'),
   'ii': ('iii', 'iii', 'Sichuan Yi'),
   'ig': ('ibo', 'ibo', 'Igbo'),
   'ie': ('ile', 'ile', 'Interlingue'),
   'id': ('ind', 'ind', 'Indonesian'),
   'ia': ('ina', 'ina', 'Interlingua'),
   'hz': ('her', 'her', 'Herero'),
   'hy': ('hye', 'arm', 'Armenian'),
   'hu': ('hun', 'hun', 'Hungarian'),
   'ht': ('hat', 'hat', 'Haitian'),
   'hr': ('hrv', 'hrv', 'Croatian'),
   'ho': ('hmo', 'hmo', 'Hiri Motu'),
   'hi': ('hin', 'hin', 'Hindi'),
   'he': ('heb', 'heb', 'Hebrew'),
   'ha': ('hau', 'hau', 'Hausa'),
   'gv': ('glv', 'glv', 'Manx'),
   'gu': ('guj', 'guj', 'Gujarati'),
   'gn': ('grn', 'grn', 'Guarani'),
   'gl': ('glg', 'glg', 'Galician'),
   'gd': ('gla', 'gla', 'Scottish Gaelic'),
   'ga': ('gle', 'gle', 'Irish'),
   'fy': ('fry', 'fry', 'Western Frisian'),
   'fr': ('fra', 'fre', 'French'),
   'fo': ('fao', 'fao', 'Faroese'),
   'fj': ('fij', 'fij', 'Fijian'),
   'fi': ('fin', 'fin', 'Finnish'),
   'ff': ('ful', 'ful', 'Fulah'),
   'fa': ('fas', 'per', 'Persian'),
   'eu': ('eus', 'baq', 'Basque'),
   'et': ('est', 'est', 'Estonian'),
   'es': ('spa', 'spa', 'Spanish'),
   'eo': ('epo', 'epo', 'Esperanto'),
   'en': ('eng', 'eng', 'English'),
   'el': ('ell', 'ell', 'Modern Greek'),
   'ee': ('ewe', 'ewe', 'Ewe'),
   'dz': ('dzo', 'dzo', 'Dzongkha'),
   'dv': ('div', 'div', 'Dhivehi'),
   'de': ('deu', 'ger', 'German'),
   'da': ('dan', 'dan', 'Danish'),
   'cy': ('cym', 'wel', 'Welsh'),
   'cv': ('chv', 'chv', 'Chuvash'),
   'cu': ('chu', 'chu', 'Church Slavic'),
   'cs': ('ces', 'cze', 'Czech'),
   'cr': ('cre', 'cre', 'Cree'),
   'co': ('cos', 'cos', 'Corsican'),
   'ch': ('cha', 'cha', 'Chamorro'),
   'ce': ('che', 'che', 'Chechen'),
   'ca': ('cat', 'cat', 'Catalan'),
   'bs': ('bos', 'bos', 'Bosnian'),
   'br': ('bre', 'bre', 'Breton'),
   'bn': ('ben', 'ben', 'Bengali'),
   'bm': ('bam', 'bam', 'Bambara'),
   'bi': ('bis', 'bis', 'Bislama'),
   'bg': ('bul', 'bul', 'Bulgarian'),
   'be': ('bel', 'bel', 'Belarusian'),
   'ba': ('bak', 'bak', 'Bashkir'),
   'az': ('aze', 'aze', 'Azerbaijani'),
   'ay': ('aym', 'aym', 'Aymara'),
   'av': ('ava', 'ava', 'Avaric'),
   'as': ('asm', 'asm', 'Assamese'),
   'ar': ('ara', 'ara', 'Arabic'),
   'an': ('arg', 'arg', 'Aragonese'),
   'am': ('amh', 'amh', 'Amharic'),
   'ak': ('aka', 'aka', 'Akan'),
   'af': ('afr', 'afr', 'Afrikaans'),
   'ae': ('ave', 'ave', 'Avestan'),
   'ab': ('abk', 'abk', 'Abkhazian'),
   'aa': ('aar', 'aar', 'Afar'),
}

def iso639_1_to_3(iso1):
   """ Convert ISO 639-1 lanuage code to ISO 639-3 (ex: "it" to "ita") """
   return iso639_table[iso1][0] if iso1 in iso639_table else None

def iso639_1_to_5(iso1):
   """ Convert ISO 639-1 lanuage code to ISO 639-5 (ex: "it" to "ita") """
   return iso639_table[iso1][1] if iso1 in iso639_table else None

def is_py3():
   return sys.version_info.major > 2

def is_py2():
   return sys.version_info.major == 2

def get_resource_file(res_type, res_name, default = None):
   """
   This will search the given reasource (the file name) first in user config
   directory (usually ~/.config/epymc) and then inside the package dir
   Example:
      full_path = get_resource_file('themes', 'mytheme.edj', 'default.edj')
   """
   for res in [res_name, default]:
      # search in user config dir
      f = os.path.join(user_conf_dir, res_type, res)
      if os.path.exists(f):
         return f

      # search in the package base dir
      f = os.path.join(emc_base_dir, res_type, res)
      if os.path.exists(f):
         return f

   # not found :(
   return None

def get_available_themes():
   # first search in user config dir
   L = glob.glob(os.path.join(user_conf_dir, 'themes', '*.edj'))

   # then search inside the package
   L += glob.glob(os.path.join(emc_base_dir, 'themes', '*.edj'))

   return L

def in_use_theme_file_set(theme_file):
   # this is a bit hackish, but I cannot find another way to use
   # it in thumbnailer.py (without recursive imports)
   global in_use_theme_file
   in_use_theme_file = theme_file

def url2path(url):
   # TODO ... convert the url to a local path !!
   return url[7:]

def hum_size(bytes):
   bytes = float(bytes)
   if bytes >= 1099511627776:
      terabytes = bytes / 1099511627776
      size = '%.3fT' % terabytes
   elif bytes >= 1073741824:
      gigabytes = bytes / 1073741824
      size = '%.2fG' % gigabytes
   elif bytes >= 1048576:
      megabytes = bytes / 1048576
      size = '%.1fM' % megabytes
   elif bytes >= 1024:
      kilobytes = bytes / 1024
      size = '%.0fK' % kilobytes
   else:
      size = '%.0fb' % bytes
   return size

def seconds_to_duration(seconds, hours=False):
   """Convert the number of seconds in a readable duration
      hours: If True then hours will be visible also when < 1
   """
   seconds = int(seconds)
   h = seconds // 3600
   m = (seconds // 60) % 60
   s = seconds % 60
   if h > 0 or hours:
      return '%d:%02d:%02d' % (h,m,s)
   else:
      return '%d:%02d' % (m,s)

def splitpath(path):
   """ Convert a string path in a list of all the components """
   return [p for p in path.split(os.path.sep) if p != '']

def ensure_file_not_exists(fullpath):
   """ Add a number at the end of the file name to ensure it do not exists """
   if not os.path.exists(fullpath):
      return fullpath

   num = 1
   name, ext = os.path.splitext(fullpath)
   while True:
      new = name + '_%03d' % num + ext
      if not os.path.exists(new):
         return new
      num += 1

def md5(txt):
   """ calc the md5 of the given str """
   if is_py3():
      txt = bytes(txt,'utf-8')
   return hashlib.md5(txt).hexdigest()

def natural_sort(l): 
   convert = lambda text: int(text) if text.isdigit() else text.lower() 
   alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)] 
   return sorted(l, key=alphanum_key)

def natural_cmp(a, b):
   convert = lambda text: int(text) if text.isdigit() else text.lower() 
   x = [ convert(c) for c in re.split('([0-9]+)', a) ]
   y = [ convert(c) for c in re.split('([0-9]+)', b) ]
   if x == y:  return 0
   elif x > y: return 1
   else:       return -1

def grab_files(folders, show_hidden=False, recursive=True):
   """
   This is a generator function, you give a list of directories to
   scan (recursively or not) and the generator will return all the files
   path, one file on each next() call.

   Usage:

   # in a for loop
   for filename in self.grab_files(['/path/1', '/path/2/other']):
      print(filename)

   # or asynchrony ;)
   generator = self.grab_files(['/path/1', '/path/2/other'])
      ...
   try:
      filename = next(generator)
      print(filename)
   except StopIteration:
      print('file list done')

   """
   if not isinstance(folders, (list, tuple)):
      folders = (folders,)
   for folder in folders:
      if folder.startswith('file://'): # mhhhh...
         folder = folder[7:]
      for name in os.listdir(folder):
         if show_hidden or name[0] != '.':
            full_path = os.path.join(folder, name)
            if os.access(full_path, os.R_OK):
               # not recursive version
               if not recursive:
                  yield full_path
               # the recursive one
               elif os.path.isdir(full_path):
                  for entry in grab_files([full_path]):
                     yield entry
               elif os.path.isfile(full_path):
                  yield full_path
               else:
                  print('Unidentified name %s. It could be a symbolic link' % full_path)

def download_url_async(url, dest='tmp', min_size=0,
                       complete_cb=None, progress_cb=None,
                       urlencode=True, *args, **kargs):
   """Download the given url in async way.

   TODO:
      If dest is set to None than the data will be passed as the dest param
      in the complete_cb.

   Args:
      url: must be a valid url to download.
      dest: If set to a local file name then the download data will be written
         to that file (created and overwritten if necessary, also the
         necessary parent directories are created).
         If dest is omitted (or is 'tmp') than the data will be written
         to a random new temp file.
      min_size: if min_size is set (and > 0) than downloaded files smaller that
         min_size will be discarted.
      complete_cb: if given, will be called when the download is done.
         signature: complete_cb(file, status, *args, **kargs)
      progress_cb: will be called while the download is in progress.
         signature: progress_cb(file, dltotal, dlnow, *args, **kargs)
      urlencode: encode the given url (default to True).
      *args: any other arguments will be passed back in the callbacks.
      **kargs: any other keyword arguments will be passed back in the callbacks.

   Returns:
      The Ecore FileDownload instance

   """

   def _cb_download_complete(dest, status, dwl_data, *args, **kargs):
      (complete_cb, progress_cb, min_size) = dwl_data

      # if file size < min_size: report as error
      if status == 200 and min_size > 0 and os.path.getsize(dest) < min_size:
         DBG('MIN_SIZE not reached, discard download')
         status = 404 # HTTP NotFound code

      # on errors delete the downloaded file
      if status != 200 and os.path.exists(dest):
         DBG('download error, HTTP code: ' + str(status))
         os.remove(dest)

      # call the user complete_cb if available
      if complete_cb and callable(complete_cb):
         complete_cb(dest, status, *args, **kargs)

   def _cb_download_progress(dest, dltotal, dlnow, uptotal, upnow, dwl_data, *args, **kargs):
      (complete_cb, progress_cb, min_size) = dwl_data
      #TODO filter out some call (maybe report only when dlnow change)
      if progress_cb and callable(progress_cb):
         progress_cb(dest, dltotal, dlnow, *args, **kargs)
      return 0 # always continue the download

   # urlencode the url (but not the http:// part, or ':' will be converted)
   if urlencode:
      (_prot, _url) = url.split('://', 1)
      encoded = '://'.join((_prot, urllib_quote(_url)))
   else:
      encoded = url

   # use a random temp file
   if dest == 'tmp':
      dest = tempfile.mktemp()
   elif dest:
      # create dest path if necessary,
      dirname = os.path.dirname(dest)
      if not os.path.exists(dirname):
         os.makedirs(dirname)
      # remove destination file if exists (overwrite)
      if os.path.exists(dest):
         os.remove(dest)

   # store download data for later use
   dwl_data = (complete_cb, progress_cb, min_size)

   # start the download
   return FileDownload(encoded, dest, _cb_download_complete,
                  _cb_download_progress, dwl_data=dwl_data, *args, **kargs)

def download_abort(dwl_handler):
   ecore.file_download_abort(dwl_handler)

def http_error_code_to_str(code):
   try:
      import BaseHTTPServer # py2
   except:
      import http.server as BaseHTTPServer # py3
   try:
      return BaseHTTPServer.BaseHTTPRequestHandler.responses[code][0]
   except:
      return _('Unknown')

class Singleton(object):
   __single = None

   def __new__(classtype, *args, **kwargs):
      if classtype != type(classtype.__single):
         classtype.__single = object.__new__(classtype, *args, **kwargs)
      return classtype.__single


class EmcExec(object):
   """
   Just a tiny wrapper around ecore.Exe to execute shell command async
   cmd: the command to execute
   grab_output: whenever to collect the stdoutput
   done_cb: function to call when the program ends. Will receive one argument:
            the standard output of the command or an empty string if
            grab_input is False (the default)
            done_cb will also receive any other params you pass to the costructor
   """
   def __init__(self, cmd, grab_output=False, done_cb=None, *args, **kargs):
      self.done_cb = done_cb
      self.args = args
      self.kargs = kargs
      self.grab_output = grab_output
      self.outbuffer = ''
      if grab_output:
         self.exe = Exe(cmd, ECORE_EXE_PIPE_READ | ECORE_EXE_PIPE_READ_LINE_BUFFERED)
         self.exe.on_data_event_add(self.data_cb)
      else:
         self.exe = ecore.Exe(cmd)
      if done_cb:
         self.exe.on_del_event_add(self.del_cb)

   def data_cb(self, exe, event):
      for l in event.lines:
         self.outbuffer += (l + '\n')

   def del_cb(self, exe, event):
      if callable(self.done_cb):
         self.done_cb(self.outbuffer, *self.args, **self.kargs)


class EmcUrl(ecore_con.Url):
   """
   A timy wrapper around ecore_con.Url to retrive an url in memory without
   writing the data to a file, and without the need to accumulate the data
   while they are received.
   The download will automatically start on class instantiation.
   The downloaded data (bytes) will be converted to str using utf8 encoding.

   Args:
      url: the url to retrive
      done_cb: function to call when the operation is completed
      prog_cb: function to call while the operation is in progress
      headers: additional headers for the request, it must be a dict like:
               {'User-Agent': 'my user agent', ...}
      **kargs: any other karguments will be passed back in the complete cb
   """
   def __init__(self, url, done_cb=None, prog_cb=None, headers=None, **kargs):
      self.done_cb = done_cb
      self.kargs = kargs
      self.received_data = []

      ecore_con.Url.__init__(self, url)
      self.on_complete_event_add(self._complete_cb)
      self.on_data_event_add(self._data_cb)
      if prog_cb is not None:
         self.on_progress_event_add(prog_cb)
      if headers is not None:
         for key in headers:
            self.additional_header_add(key, headers[key])
      self.get()

   def _complete_cb(self, event):
      data = b''.join(self.received_data).decode('utf8')
      self.done_cb(event.url, event.status, data, **self.kargs)
      self.delete()

   def _data_cb(self, event):
      self.received_data.append(event.data)
