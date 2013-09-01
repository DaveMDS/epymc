#!/usr/bin/env python

import os, glob, subprocess, shutil
from distutils.core import setup, Command
from distutils.log import warn, info, error

#
# usage:
#
# python setup.py install [--prefix=]
# python setup.py build_themes
# python setup.py clean --all
#


class BuildThemes(Command):
   description = 'rebuild all the themes found in data/themes using edje_cc'
   user_options = []
   def initialize_options(self): pass
   def finalize_options(self): pass
   def run(self):
      for theme_dir in glob.glob('data/themes/*'):
         name = os.path.basename(theme_dir)
         edc_name = os.path.join(theme_dir, name + '.edc')
         edj_name = os.path.join(theme_dir, name + '.edj')
         info('building theme: ' + name)
         ret = subprocess.call(['edje_cc', '-v', edc_name,
                                     '-id', os.path.join(theme_dir, 'images'),
                                     '-fd', os.path.join(theme_dir, 'fonts')
                              ])
         if ret == 0:
            info('Moving generated edje file to epymc/themes/ folder')
            dest = os.path.join('epymc', 'themes', name + '.edj')
            shutil.move(edj_name, dest)
         else:
            warn('Error generating theme %s' % name)


setup (
   name = 'EpyMC',
   version = '0.9',
   author = 'Davide "davemds" Andreoli',
   author_email = 'dave@gurumeditation.it',
   url = 'http://code.google.com/p/e17mods/wiki/EpyMC',
   description = 'EFL based Media Center',
   license = 'GNU GPL v3',

   requires = ['efl (>= 1.7.999)'],
   provides = ['epymc'],

   packages = [
      'epymc',
      'epymc.plugins.input_keyb',
      'epymc.plugins.input_lirc',
      'epymc.plugins.input_joy',
      'epymc.plugins.input_webserver',
      'epymc.plugins.movies',
      'epymc.plugins.tvshows',
      'epymc.plugins.onlinevideo',
      'epymc.plugins.mame',
      'epymc.plugins.music',
      'epymc.plugins.uitests',
   ],

   package_data = {
      'epymc': ['themes/*.edj'],
      'epymc.plugins.movies': ['*.png'],
      'epymc.plugins.tvshows': ['*.png'],
      'epymc.plugins.mame': ['*.png', '*.jpg'],
      'epymc.plugins.music': ['*.png'],
      'epymc.plugins.uitests': ['*.png'],
      'epymc.plugins.onlinevideo': [
         '*.png',
         'traileraddict/*',
         'youtube/*',
         'zapiks/*',
         'fantasticc/*',
      ],
   },

   scripts = ['bin/epymc'],

   data_files = [
      ('share/applications/', ['data/desktop/epymc.desktop']),
      ('share/icons/', ['data/desktop/epymc.png']),
   ],

   cmdclass = {
      'build_themes': BuildThemes,
   },

)

