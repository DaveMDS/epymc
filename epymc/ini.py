#!/usr/bin/env python
#
# Copyright (C) 2010-2012 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of EpyMC.
#
# EpyMC is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# EpyMC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with EpyMC. If not, see <http://www.gnu.org/licenses/>.

import ConfigParser

_config = ConfigParser.ConfigParser()

def read_from_files(files):
   readed = _config.read(files)
   print 'Readed config from files:'
   for f in readed: print ' * ' + f
   print ''
   add_section('general')

def write_to_file(file):
   print('Writing config to file: ' + file)
   with open(file, 'wb') as configfile:
      _config.write(configfile)

def add_section(section):
   if not _config.has_section(section):
      _config.add_section(section)

def has_section(section):
   return _config.has_section(section)

def has_option(section, option):
   return _config.has_option(section, option)

def get(section, option):
   if not _config.has_option(section, option):
      return None
   return _config.get(section, option)

def get_string_list(section, option, separator = ' '):
   if not _config.has_option(section, option):
      return []
   string = get(section, option)
   ret = []
   for s in string.split(separator):
      if len(s) > 0:
         ret.append(s if separator == ' ' else s.strip())
   return ret

def get_int(section, option):
   return _config.getint(section, option)

def get_float(section, option):
   return _config.getfloat(section, option)

def get_bool(section, option):
   return _config.getboolean(section, option)

def set(section, option, value):
   _config.set(section, option, value)

def set_string_list(section, option, values, separator = ' '):
   string = separator.join(values)
   set(section, option, string)

