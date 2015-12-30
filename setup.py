#!/usr/bin/env python
#
# usage:
#
# python setup.py install [--prefix=]
# python setup.py uninstall [--prefix=]
# python setup.py build_themes
# python setup.py build_i18n
# python setup.py update_po
# python setup.py clean --all
# python setup.py sdist|bdist
# python setup.py --help
# python setup.py --help-commands
# python setup.py --help uninstall
#
# distutils reference:
#  http://docs.python.org/distutils/
#

import os, sys, glob, subprocess, shutil, fnmatch
from distutils.core import setup, Command
from distutils.log import warn, info, error
from distutils.dir_util import remove_tree, mkpath
from distutils.file_util import copy_file
from distutils.command.install_lib import install_lib
from distutils.command.build import build
from distutils.dep_util import newer, newer_group
from epymc import __version__ as emc_version


class build_themes(Command):
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


class build_i18n(Command):
   description = 'Compile all the po files'
   user_options = []

   def initialize_options(self):
      pass

   def finalize_options(self):
      pass

   def run(self):
      linguas_file = os.path.join('data', 'locale', 'LINGUAS')
      for lang in open(linguas_file).read().split():
         po_file = os.path.join('data', 'locale', lang + '.po')
         mo_file = os.path.join('epymc', 'locale', lang, 'LC_MESSAGES', 'epymc.mo')
         mkpath(os.path.dirname(mo_file), verbose=False)
         if newer(po_file, mo_file):
            info('compiling po file: %s -> %s' % (po_file, mo_file))
            cmd = 'msgfmt -o %s -c %s' % (mo_file, po_file)
            os.system(cmd)


class update_po(Command):
   description = 'Prepare all i18n files and update them as needed'
   user_options = []

   def initialize_options(self):
      pass

   def finalize_options(self):
      pass

   def run(self):
      # build the string of all the source files to be translated
      sources = ''
      for dirpath, dirs, files in os.walk('epymc'):
         for name in fnmatch.filter(files, '*.py'):
            sources += ' ' + os.path.join(dirpath, name)

      # create or update the reference pot file
      pot_file = os.path.join('data', 'locale', 'epymc.pot')
      info('updating pot file: %s' % (pot_file))
      cmd = 'xgettext --from-code=UTF-8 --force-po ' \
                     '--output=%s %s' % (pot_file, sources)
      os.system(cmd)

      # create or update all the .po files
      linguas_file = os.path.join('data', 'locale', 'LINGUAS')
      for lang in open(linguas_file).read().split():
         po_file = os.path.join('data', 'locale', lang + '.po')
         mo_file = os.path.join('epymc', 'locale', lang, 'LC_MESSAGES', 'epymc.mo')
         if os.path.exists(po_file):
            # update an existing po file
            info('updating po file: %s' % (po_file))
            cmd = 'msgmerge -N -U -q %s %s' % (po_file, pot_file)
            os.system(cmd)
         else:
            # create a new po file
            info('creating po file: %s' % (po_file))
            mkpath(os.path.dirname(po_file), verbose=False)
            copy_file(pot_file, po_file, verbose=False)


RECORD_FILE = "installed_files-%d.%d.txt" % sys.version_info[:2]
class Uninstall(Command):
    description = 'remove all the installed files recorded at installation time'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def remove_entry(self, entry):
        if os.path.isfile(entry):
            try:
                info("removing file %s" % entry)
                os.unlink(entry)
            except OSError as e:
                error(e)

            directory = os.path.dirname(entry)
            while os.listdir(directory) == []:
                try:
                    info("removing empty directory %s" % directory)
                    os.rmdir(directory)
                except OSError as e:
                    error(e)
                directory = os.path.dirname(directory)

    def run(self):
        if not os.path.exists(RECORD_FILE):
            info('ERROR: No %s file found!' % RECORD_FILE)
        else:
            for entry in open(RECORD_FILE).read().split():
                self.remove_entry(entry)


class Build(build):
   def run(self):
      self.run_command("build_themes")
      self.run_command("build_i18n")
      build.run(self)


class Install(install_lib):
   executables = [
      '*/onlinevideo/*/*.py'
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
   version = emc_version,
   author = 'Davide <davemds> Andreoli',
   author_email = 'dave@gurumeditation.it',
   url = 'http://github.com/DaveMDS/epymc',
   description = 'Emotion Media Center',
   long_description = 'EpyMC is a media center written in python that use the Enlightenment Foundation Libraries',
   license = 'GNU GPL v3',
   platforms = 'linux',

   requires = ['efl (>= 1.10.0)', 'beautifulsoup4', 'mutagen'],
   provides = ['epymc'],

   packages = [
      'epymc',
      'epymc.extapi',
      'epymc.plugins.input_keyb',
      'epymc.plugins.input_lirc',
      'epymc.plugins.input_joy',
      'epymc.plugins.input_webserver',
      'epymc.plugins.input_mpris2',
      'epymc.plugins.screensaver',
      'epymc.plugins.movies',
      'epymc.plugins.tvshows',
      'epymc.plugins.onlinevideo',
      'epymc.plugins.mame',
      'epymc.plugins.music',
      'epymc.plugins.uitests',
      'epymc.plugins.calibrator',
      'epymc.plugins.filemanager',
      'epymc.plugins.photos',
      'epymc.plugins.watchdog',
   ],

   package_data = {
      'epymc': ['themes/*.edj', 'locale/*/LC_MESSAGES/*.mo'],
      'epymc.plugins.movies': ['*.png'],
      'epymc.plugins.tvshows': ['*.png'],
      'epymc.plugins.mame': ['*.png', '*.jpg'],
      'epymc.plugins.music': ['*.png'],
      'epymc.plugins.uitests': ['*.png'],
      'epymc.plugins.calibrator': ['*.jpg', '*.png'],
      'epymc.plugins.onlinevideo': [ '*.png',
         'themoviedb/*',
         'youtube/*',
         'vimeo/*',
         'zapiks/*',
         'fantasticc/*',
         'southparkstudios/*',
      ],
      'epymc.plugins.input_webserver': [
         'default/*',
         'mobile/*',
      ]
   },

   scripts = ['bin/epymc', 'bin/epymc_standalone',
              'epymc/plugins/watchdog/epymc_watchdog'],

   data_files = [
      ('share/applications/', ['data/desktop/epymc.desktop']),
      ('/usr/share/xsessions/', ['data/desktop/epymc_xsession.desktop']),
      ('share/icons/hicolor/64x64/apps/', [
                        'data/desktop/epymc.png',
                        'data/desktop/epymc-movies.png',
                        'data/desktop/epymc-music.png',
                        'data/desktop/epymc-olvideos.png',
                        'data/desktop/epymc-tv.png',
                        'data/desktop/epymc-mame.png',
                        'data/desktop/epymc-photos.png']),
   ],

   cmdclass = {
      'build_themes': build_themes,
      'build_i18n': build_i18n,
      'build': Build,
      'install_lib': Install,
      'uninstall': Uninstall,
      'update_po': update_po,
   },
   command_options = {
      'install': {'record': ('setup.py', RECORD_FILE)}
   },
)


# alert if run from python < 3 (lots of translation issue with 2.7)
if sys.version_info.major == 2:
   print('')
   print('##########################################################')
   print('PYTHON 2.X IS NOT SUPPORTED ANYMORE')
   print('You are using python2! It is old! EpyMC works much better')
   print('with py3, even more if you are not using the english texts.')
   print('YOU MUST SWITCH TO PYTHON 3 !!!')
   print('##########################################################')
   print('')
