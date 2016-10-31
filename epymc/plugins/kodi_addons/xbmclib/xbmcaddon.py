# This Python file uses the following encoding: utf-8

import os
import locale
import polib
from xml.etree import ElementTree 

user_dir = os.path.expanduser('~/.config/epymc/kodi')
addons_dir = os.path.expanduser('~/.config/epymc/kodi/addons')


class Addon(object):

   def __init__(self, id=None):
      self.id = id or addon_id # addon_id comes from sitecustomize.py
      self._class_id = self.id # this will be passed back in methods to emc
      self._strings_po = None  # already parsed POFile instance
      self._strings_et = None  # already parsed xml lang file (ElementTree)

   @emc_method_call
   def getAddonInfo(self, id):
      return emc_wait_replay()
      
   def getSetting(self, id):
      print("NOT IMPLEMENTED: getSetting ({})".format(id))
      return '0' # TODO

   def getLocalizedString(self, id):
      # search and parse strings.po (or string.xml)
      if self._strings_po is None and self._strings_et is None:
         # TODO also support: "en_US" (only "en" atm)
         lang, encoding = locale.getdefaultlocale()
         lang_name = iso639_table.get(lang[:2], 'English') if lang else 'English'
         # po file
         for lang in (lang_name, 'English'):
            po_file = os.path.join(addons_dir, self.id, 'resources',
                                  'language', lang, 'strings.po')
            try:
               self._strings_po = polib.pofile(po_file)
            except IOError:
               continue
            else:
               break
         # or xml file
         if self._strings_po is None:
            for lang in (lang_name, 'English'):
               xml_file = os.path.join(addons_dir, self.id, 'resources',
                                      'language', lang, 'strings.xml')
               if not os.path.exists(xml_file):
                  continue
               # try different encoding (if encoding not provided in xml)
               for enc in (None, 'utf-8', 'iso-8859-1'):
                  parser = ElementTree.XMLParser(encoding=enc)
                  try:
                     self._strings_et = ElementTree.parse(xml_file, parser=parser)
                  except ElementTree.ParseError:
                     pass
                  else:
                     break

               if self._strings_et is not None:
                  break

      # already parsed po file
      if self._strings_po is not None:
         ctx = '#{}'.format(id)
         for entry in self._strings_po:
            if entry.msgctxt == ctx:
               return entry.msgstr
         return 'Localize ERROR1 {}'.format(id)

      # already parsed xml lang file
      elif self._strings_et is not None:
         el = self._strings_et.find(".//string[@id='{}']".format(id))
         if el is not None:
            return el.text
         return 'Localize ERROR2 {}'.format(id)

      return 'Localize ERROR3 {}'.format(id)

iso639_table = {
# From http://kodi.wiki/view/List_of_language_codes_(ISO-639:1988)
   'aa': 'Afar',
   'ab': 'Abkhazian',
   'af': 'Afrikaans',
   'am': 'Amharic',
   'ar': 'Arabic',
   'as': 'Assamese',
   'ay': 'Aymara',
   'az': 'Azerbaijani',
   'ba': 'Bashkir',
   'be': 'Byelorussian',
   'bg': 'Bulgarian',
   'bh': 'Bihari',
   'bi': 'Bislama',
   'bn': 'Bengali; Bangla',
   'bo': 'Tibetan',
   'br': 'Breton',
   'ca': 'Catalan',
   'co': 'Corsican',
   'cs': 'Czech',
   'cy': 'Welsh',
   'da': 'Danish',
   'de': 'German',
   'dz': 'Bhutani',
   'el': 'Greek',
   'en': 'English',
   'eo': 'Esperanto',
   'es': 'Spanish',
   'et': 'Estonian',
   'eu': 'Basque',
   'fa': 'Persian',
   'fi': 'Finnish',
   'fj': 'Fiji',
   'fo': 'Faeroese',
   'fr': 'French',
   'fy': 'Frisian',
   'ga': 'Irish',
   'gd': 'Scots Gaelic',
   'gl': 'Galician',
   'gn': 'Guarani',
   'gu': 'Gujarati',
   'ha': 'Hausa',
   'he': 'Hebrew',
   'hi': 'Hindi',
   'hr': 'Croatian',
   'hu': 'Hungarian',
   'hy': 'Armenian',
   'ia': 'Interlingua',
   'id': 'Indonesian',
   'ie': 'Interlingue',
   'ik': 'Inupiak',
   'is': 'Icelandic',
   'it': 'Italian',
   'ja': 'Japanese',
   'ji': 'Yiddish',
   'jw': 'Javanese',
   'ka': 'Georgian',
   'kk': 'Kazakh',
   'kl': 'Greenlandic',
   'km': 'Cambodian',
   'kn': 'Kannada',
   'ko': 'Korean',
   'ks': 'Kashmiri',
   'ku': 'Kurdish',
   'ky': 'Kirghiz',
   'la': 'Latin',
   'ln': 'Lingala',
   'lo': 'Laothian',
   'lt': 'Lithuanian',
   'lv': 'Latvian, Lettish',
   'mg': 'Malagasy',
   'mi': 'Maori',
   'mk': 'Macedonian',
   'ml': 'Malayalam',
   'mn': 'Mongolian',
   'mo': 'Moldavian',
   'mr': 'Marathi',
   'ms': 'Malay',
   'mt': 'Maltese',
   'my': 'Burmese',
   'na': 'Nauru',
   'ne': 'Nepali',
   'nl': 'Dutch',
   'no': 'Norwegian',
   'oc': 'Occitan',
   'om': '(Afan) Oromo',
   'or': 'Oriya',
   'pa': 'Punjabi',
   'pl': 'Polish',
   'ps': 'Pashto, Pushto',
   'pt': 'Portuguese',
   'qu': 'Quechua',
   'rm': 'Rhaeto-Romance',
   'rn': 'Kirundi',
   'ro': 'Romanian',
   'ru': 'Russian',
   'rw': 'Kinyarwanda',
   'sa': 'Sanskrit',
   'sd': 'Sindhi',
   'sg': 'Sangro',
   'sh': 'Serbo-Croatian',
   'si': 'Singhalese',
   'sk': 'Slovak',
   'sl': 'Slovenian',
   'sm': 'Samoan',
   'sn': 'Shona',
   'so': 'Somali',
   'sq': 'Albanian',
   'sr': 'Serbian',
   'ss': 'Siswati',
   'st': 'Sesotho',
   'su': 'Sundanese',
   'sv': 'Swedish',
   'sw': 'Swahili',
   'ta': 'Tamil',
   'te': 'Tegulu',
   'tg': 'Tajik',
   'th': 'Thai',
   'ti': 'Tigrinya',
   'tk': 'Turkmen',
   'tl': 'Tagalog',
   'tn': 'Setswana',
   'to': 'Tonga',
   'tr': 'Turkish',
   'ts': 'Tsonga',
   'tt': 'Tatar',
   'tw': 'Twi',
   'uk': 'Ukrainian',
   'ur': 'Urdu',
   'uz': 'Uzbek',
   'vi': 'Vietnamese',
   'vo': 'Volapuk',
   'wo': 'Wolof',
   'xh': 'Xhosa',
   'yo': 'Yoruba',
   'zh': 'Chinese',
   'zu': 'Zulu',
}
