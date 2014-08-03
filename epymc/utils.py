#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2014 Davide Andreoli <dave@gurumeditation.it>
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

import os, tempfile, glob, re, hashlib

try:
   from urllib.parse import quote as urllib_quote
except:
   from urllib import quote as urllib_quote

from efl import ecore
from efl.ecore import FileDownload, Exe, ECORE_EXE_PIPE_READ, ECORE_EXE_PIPE_READ_LINE_BUFFERED


def DBG(msg):
   print('UTILS: ' + str(msg))
   pass


emc_base_dir = os.path.dirname(__file__)
user_conf_dir = os.path.expanduser('~/.config/epymc') # TODO use xdg-stuff

DBG('emc_base_dir: %s' % emc_base_dir)
DBG('user_conf_dir: %s' % user_conf_dir)


iso639_table = {
   'zu': ('zul', 'Zulu'),
   'zh': ('zho', 'Chinese'),
   'za': ('zha', 'Zhuang'),
   'yo': ('yor', 'Yoruba'),
   'yi': ('yid', 'Yiddish'),
   'xh': ('xho', 'Xhosa'),
   'wo': ('wol', 'Wolof'),
   'wa': ('wln', 'Walloon'),
   'vo': ('vol', 'Volapük'),
   'vi': ('vie', 'Vietnamese'),
   've': ('ven', 'Venda'),
   'uz': ('uzb', 'Uzbek'),
   'ur': ('urd', 'Urdu'),
   'uk': ('ukr', 'Ukrainian'),
   'ug': ('uig', 'Uighur'),
   'ty': ('tah', 'Tahitian'),
   'tw': ('twi', 'Twi'),
   'tt': ('tat', 'Tatar'),
   'ts': ('tso', 'Tsonga'),
   'tr': ('tur', 'Turkish'),
   'to': ('ton', 'Tonga (Tonga Islands)'),
   'tn': ('tsn', 'Tswana'),
   'tl': ('tgl', 'Tagalog'),
   'tk': ('tuk', 'Turkmen'),
   'ti': ('tir', 'Tigrinya'),
   'th': ('tha', 'Thai'),
   'tg': ('tgk', 'Tajik'),
   'te': ('tel', 'Telugu'),
   'ta': ('tam', 'Tamil'),
   'sw': ('swa', 'Swahili (macrolanguage)'),
   'sv': ('swe', 'Swedish'),
   'su': ('sun', 'Sundanese'),
   'st': ('sot', 'Southern Sotho'),
   'ss': ('ssw', 'Swati'),
   'sr': ('srp', 'Serbian'),
   'sq': ('sqi', 'Albanian'),
   'so': ('som', 'Somali'),
   'sn': ('sna', 'Shona'),
   'sm': ('smo', 'Samoan'),
   'sl': ('slv', 'Slovenian'),
   'sk': ('slk', 'Slovak'),
   'si': ('sin', 'Sinhala'),
   'sg': ('sag', 'Sango'),
   'se': ('sme', 'Northern Sami'),
   'sd': ('snd', 'Sindhi'),
   'sc': ('srd', 'Sardinian'),
   'sa': ('san', 'Sanskrit'),
   'rw': ('kin', 'Kinyarwanda'),
   'ru': ('rus', 'Russian'),
   'ro': ('ron', 'Romanian'),
   'rn': ('run', 'Rundi'),
   'rm': ('roh', 'Romansh'),
   'qu': ('que', 'Quechua'),
   'pt': ('por', 'Portuguese'),
   'ps': ('pus', 'Pushto'),
   'pl': ('pol', 'Polish'),
   'pi': ('pli', 'Pali'),
   'pa': ('pan', 'Panjabi'),
   'os': ('oss', 'Ossetian'),
   'or': ('ori', 'Oriya (macrolanguage)'),
   'om': ('orm', 'Oromo'),
   'oj': ('oji', 'Ojibwa'),
   'oc': ('oci', 'Occitan (post 1500)'),
   'ny': ('nya', 'Nyanja'),
   'nv': ('nav', 'Navajo'),
   'nr': ('nbl', 'South Ndebele'),
   'no': ('nor', 'Norwegian'),
   'nn': ('nno', 'Norwegian Nynorsk'),
   'nl': ('nld', 'Dutch'),
   'ng': ('ndo', 'Ndonga'),
   'ne': ('nep', 'Nepali (macrolanguage)'),
   'nd': ('nde', 'North Ndebele'),
   'nb': ('nob', 'Norwegian Bokmål'),
   'na': ('nau', 'Nauru'),
   'my': ('mya', 'Burmese'),
   'mt': ('mlt', 'Maltese'),
   'ms': ('msa', 'Malay (macrolanguage)'),
   'mr': ('mar', 'Marathi'),
   'mn': ('mon', 'Mongolian'),
   'ml': ('mal', 'Malayalam'),
   'mk': ('mkd', 'Macedonian'),
   'mi': ('mri', 'Maori'),
   'mh': ('mah', 'Marshallese'),
   'mg': ('mlg', 'Malagasy'),
   'lv': ('lav', 'Latvian'),
   'lu': ('lub', 'Luba-Katanga'),
   'lt': ('lit', 'Lithuanian'),
   'lo': ('lao', 'Lao'),
   'ln': ('lin', 'Lingala'),
   'li': ('lim', 'Limburgan'),
   'lg': ('lug', 'Ganda'),
   'lb': ('ltz', 'Luxembourgish'),
   'la': ('lat', 'Latin'),
   'ky': ('kir', 'Kirghiz'),
   'kw': ('cor', 'Cornish'),
   'kv': ('kom', 'Komi'),
   'ku': ('kur', 'Kurdish'),
   'ks': ('kas', 'Kashmiri'),
   'kr': ('kau', 'Kanuri'),
   'ko': ('kor', 'Korean'),
   'kn': ('kan', 'Kannada'),
   'km': ('khm', 'Central Khmer'),
   'kl': ('kal', 'Kalaallisut'),
   'kk': ('kaz', 'Kazakh'),
   'kj': ('kua', 'Kuanyama'),
   'ki': ('kik', 'Kikuyu'),
   'kg': ('kon', 'Kongo'),
   'ka': ('kat', 'Georgian'),
   'jv': ('jav', 'Javanese'),
   'ja': ('jpn', 'Japanese'),
   'iu': ('iku', 'Inuktitut'),
   'it': ('ita', 'Italian'),
   'is': ('isl', 'Icelandic'),
   'io': ('ido', 'Ido'),
   'ik': ('ipk', 'Inupiaq'),
   'ii': ('iii', 'Sichuan Yi'),
   'ig': ('ibo', 'Igbo'),
   'ie': ('ile', 'Interlingue'),
   'id': ('ind', 'Indonesian'),
   'ia': ('ina', 'Interlingua'),
   'hz': ('her', 'Herero'),
   'hy': ('hye', 'Armenian'),
   'hu': ('hun', 'Hungarian'),
   'ht': ('hat', 'Haitian'),
   'hr': ('hrv', 'Croatian'),
   'ho': ('hmo', 'Hiri Motu'),
   'hi': ('hin', 'Hindi'),
   'he': ('heb', 'Hebrew'),
   'ha': ('hau', 'Hausa'),
   'gv': ('glv', 'Manx'),
   'gu': ('guj', 'Gujarati'),
   'gn': ('grn', 'Guarani'),
   'gl': ('glg', 'Galician'),
   'gd': ('gla', 'Scottish Gaelic'),
   'ga': ('gle', 'Irish'),
   'fy': ('fry', 'Western Frisian'),
   'fr': ('fra', 'French'),
   'fo': ('fao', 'Faroese'),
   'fj': ('fij', 'Fijian'),
   'fi': ('fin', 'Finnish'),
   'ff': ('ful', 'Fulah'),
   'fa': ('fas', 'Persian'),
   'eu': ('eus', 'Basque'),
   'et': ('est', 'Estonian'),
   'es': ('spa', 'Spanish'),
   'eo': ('epo', 'Esperanto'),
   'en': ('eng', 'English'),
   'el': ('ell', 'Modern Greek'),
   'ee': ('ewe', 'Ewe'),
   'dz': ('dzo', 'Dzongkha'),
   'dv': ('div', 'Dhivehi'),
   'de': ('deu', 'German'),
   'da': ('dan', 'Danish'),
   'cy': ('cym', 'Welsh'),
   'cv': ('chv', 'Chuvash'),
   'cu': ('chu', 'Church Slavic'),
   'cs': ('ces', 'Czech'),
   'cr': ('cre', 'Cree'),
   'co': ('cos', 'Corsican'),
   'ch': ('cha', 'Chamorro'),
   'ce': ('che', 'Chechen'),
   'ca': ('cat', 'Catalan'),
   'bs': ('bos', 'Bosnian'),
   'br': ('bre', 'Breton'),
   'bn': ('ben', 'Bengali'),
   'bm': ('bam', 'Bambara'),
   'bi': ('bis', 'Bislama'),
   'bg': ('bul', 'Bulgarian'),
   'be': ('bel', 'Belarusian'),
   'ba': ('bak', 'Bashkir'),
   'az': ('aze', 'Azerbaijani'),
   'ay': ('aym', 'Aymara'),
   'av': ('ava', 'Avaric'),
   'as': ('asm', 'Assamese'),
   'ar': ('ara', 'Arabic'),
   'an': ('arg', 'Aragonese'),
   'am': ('amh', 'Amharic'),
   'ak': ('aka', 'Akan'),
   'af': ('afr', 'Afrikaans'),
   'ae': ('ave', 'Avestan'),
   'ab': ('abk', 'Abkhazian'),
   'aa': ('aar', 'Afar'),
   None: (None, None)
}

def iso639_1_to_3(iso1):
   """ Convert ISO 639-1 lanuage code to ISO 639-3 (ex: "it" to "ita") """
   return iso639_table[iso1][0] if iso1 in iso639_table else None

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

def url2path(url):
   # TODO ... convert the url to a local path !!
   return url[7:]

def hum_size(bytes):
   bytes = float(bytes)
   if bytes >= 1099511627776:
      terabytes = bytes / 1099511627776
      size = '%.2fT' % terabytes
   elif bytes >= 1073741824:
      gigabytes = bytes / 1073741824
      size = '%.2fG' % gigabytes
   elif bytes >= 1048576:
      megabytes = bytes / 1048576
      size = '%.2fM' % megabytes
   elif bytes >= 1024:
      kilobytes = bytes / 1024
      size = '%.2fK' % kilobytes
   else:
      size = '%.2fb' % bytes
   return size

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
   return hashlib.md5(txt.encode('utf-8')).hexdigest()
   
def natural_sort(l): 
   convert = lambda text: int(text) if text.isdigit() else text.lower() 
   alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)] 
   return sorted(l, key=alphanum_key)

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
      filename = generator.next()
      print(filename)
   except StopIteration:
      print('file list done')

   """
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
                  _cb_download_progress, dwl_data = dwl_data, *args, **kargs)

def download_abort(dwl_handler):
   ecore.file_download_abort(dwl_handler)


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
   def __init__(self, cmd, grab_output = False, done_cb = None, *args, **kargs):
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

