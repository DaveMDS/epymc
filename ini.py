#!/usr/bin/env python

import ConfigParser

_config = ConfigParser.ConfigParser()

def read_from_files(files):
    readed = _config.read(files)
    print "Readed config from files:"
    for f in readed: print " * " + f
    print ""
    if not _config.has_section('general'):
        _config.add_section('general')

def write_to_file(file):
    print("Writing config to file: " + file)
    with open(file, 'wb') as configfile:
        _config.write(configfile)

def add_section(section):
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

