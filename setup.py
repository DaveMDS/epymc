#!/usr/bin/env python
#
# usage:
#
# python setup.py install [--prefix=]
# python setup.py uninstall [--prefix=]
# python setup.py build_themes
# python setup.py clean --all
# python setup.py sdist|bdist
# python setup.py --help
# python setup.py --help-commands
# python setup.py --help uninstall
#
# distutils reference:
# http://docs.python.org/distutils/
#

import os, sys, glob, subprocess, shutil, fnmatch
from distutils.core import setup, Command
from distutils.log import warn, info, error
from distutils.dir_util import remove_tree
from distutils.command.install_lib import install_lib
from distutils.command.build import build
from distutils.dep_util import newer_group


class BuildThemes(Command):
   description = 'Compile all the themes found in data/themes using edje_cc'
   user_options = []
   def initialize_options(self): pass
   def finalize_options(self): pass
   def run(self):
      for theme_dir in glob.glob(os.path.join('data', 'themes', '*')):
         name = os.path.basename(theme_dir)
         edc_name = os.path.join(theme_dir, name + '.edc')
         edj_name = os.path.join(theme_dir, name + '.edj')
         dst_name = os.path.join('epymc', 'themes', name + '.edj')
         sources = glob.glob(os.path.join(theme_dir, '*.edc')) + \
                   glob.glob(os.path.join(theme_dir, 'images', '*')) + \
                   glob.glob(os.path.join(theme_dir, 'fonts', '*'))
         if newer_group(sources, dst_name):
            info('building theme: "%s" from: %s' % (name, edc_name))
            ret = subprocess.call(['edje_cc', '-v', edc_name,
                                    '-id', os.path.join(theme_dir, 'images'),
                                    '-fd', os.path.join(theme_dir, 'fonts')
                                 ])
            if ret == 0:
               info('Moving generated edje file to epymc/themes/ folder')
               shutil.move(edj_name, dst_name)
            else:
               error('Error generating theme: "%s"' % name)


class Uninstall(Command):
   description = 'attemp an uninstall operation, use the --prefix argument'
   user_options = [('prefix=', None, 'where the package has been installed')]

   def initialize_options(self):
      self.prefix = None

   def finalize_options(self):
      if self.prefix is None:
         self.prefix = '/usr/local'

   def remove_file(self, path):
      if os.path.isfile(path):
         try:
            os.unlink(path)
            info("removing '%s'" % path)
         except OSError:
            warn("error removing '%s'" % path)

   def run(self):
      info('attemp to uninstall from the prefix: %s' % self.prefix)
      py = 'python%d.%d' % (sys.version_info.major, sys.version_info.minor)

      # remove scripts and data files
      self.remove_file(os.path.join(self.prefix, 'bin', 'epymc'))
      self.remove_file(os.path.join(self.prefix, 'share', 'applications', 'epymc.desktop'))
      self.remove_file(os.path.join(self.prefix, 'share', 'icons', 'epymc.png'))

      # remove the module itself
      for search in ['dist-packages', 'site-packages']:
         path = os.path.join(self.prefix, 'lib', py, search, 'epymc')
         if os.path.exists(path) and os.path.isdir(path):
            remove_tree(path, verbose=1)

      # remove the egg-info file
      for search in ['dist-packages', 'site-packages']:
         path = os.path.join(self.prefix, 'lib', py, search, 'EpyMC-*.egg-info')
         for egg in glob.glob(path):
            self.remove_file(egg)


class Build(build):
   def run(self):
      self.run_command("build_themes")
      build.run(self)


class Install(install_lib):
   executables = [
      '*/onlinevideo/*/*.py',
      '*/extapi/youtube-dl',
   ]
   def run(self):
      install_lib.run(self)
      for fn in self.get_outputs():
         for e in self.executables:
            if fnmatch.fnmatch(fn, e):
               mode = ((os.stat(fn).st_mode) | 0o0555) & 0o07777
               info("changing mode of %s to %o", fn, mode)
               os.chmod(fn, mode)


setup (
   name = 'EpyMC',
   version = '0.9',
   author = 'Davide <davemds> Andreoli',
   author_email = 'dave@gurumeditation.it',
   url = 'http://github.com/DaveMDS/epymc',
   description = 'Emotion Media Center',
   long_description = 'EpyMC is a media center written in python that use the Enlightenment Foundation Libraries',
   license = 'GNU GPL v3',
   platforms = 'linux',

   requires = ['efl (>= 1.9.0)', 'beautifulsoup4'],
   provides = ['epymc'],

   packages = [
      'epymc',
      'epymc.extapi',
      'epymc.plugins.input_keyb',
      'epymc.plugins.input_lirc',
      'epymc.plugins.input_joy',
      'epymc.plugins.input_webserver',
      'epymc.plugins.screensaver',
      'epymc.plugins.movies',
      'epymc.plugins.tvshows',
      'epymc.plugins.onlinevideo',
      'epymc.plugins.mame',
      'epymc.plugins.music',
      'epymc.plugins.uitests',
      'epymc.plugins.calibrator',
   ],

   package_data = {
      'epymc': ['themes/*.edj'],
      'epymc.extapi': ['youtube-dl'],
      'epymc.plugins.movies': ['*.png'],
      'epymc.plugins.tvshows': ['*.png'],
      'epymc.plugins.mame': ['*.png', '*.jpg'],
      'epymc.plugins.music': ['*.png'],
      'epymc.plugins.uitests': ['*.png'],
      'epymc.plugins.calibrator': ['*.jpg', '*.png'],
      'epymc.plugins.onlinevideo': [ '*.png',
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
      'uninstall': Uninstall,
      'install_lib': Install,
      'build': Build,
   },
)
