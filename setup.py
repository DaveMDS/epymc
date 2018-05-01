#!/usr/bin/env python
#
# usage:
#
# python3 setup.py develop  (run in place)
# python3 setup.py install [--prefix=]
# python3 setup.py uninstall [--prefix=]
# python3 setup.py build_themes
# python3 setup.py build_i18n
# python3 setup.py update_po
# python3 setup.py check_po
# python3 setup.py clean --all
# python3 setup.py sdist|bdist
# python3 setup.py --help
# python3 setup.py --help-commands
# python3 setup.py --help uninstall
#
# distutils reference:
#  http://docs.python.org/distutils/
#

import os, sys, glob, subprocess, shutil, fnmatch
from distutils.core import setup, Command
from distutils.log import warn, info, error
from distutils.dir_util import remove_tree, mkpath
from distutils.file_util import copy_file
from distutils.command.build import build
from distutils.command.install import install
from distutils.command.install_lib import install_lib
from distutils.dep_util import newer, newer_group
from distutils.version import LooseVersion
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


class check_po(Command):
   description = 'Give statistics about translations status'
   user_options = []

   def initialize_options(self):
      pass

   def finalize_options(self):
      pass

   def run(self):
      try:
         import polib
      except ImportError:
         error('You need python polib installed')
         return

      # print totals
      po = polib.pofile(os.path.join('data', 'locale', 'epymc.pot'))
      info('Total strings in epymc.pot: %d' % len(po.untranslated_entries()))

      # print per-lang statistics
      linguas_file = os.path.join('data', 'locale', 'LINGUAS')
      for lang in sorted(open(linguas_file).read().split()):
         po = polib.pofile(os.path.join('data', 'locale', lang + '.po'))
         bar = '=' * (int(po.percent_translated() / 100 * 30))
         info('%s [%-30s] %3d%% (%d translated, %d fuzzy, %d untranslated, %d obsolete)' % (
               lang, bar, po.percent_translated(),
               len(po.translated_entries()),
               len(po.fuzzy_entries()),
               len(po.untranslated_entries()),
               len(po.obsolete_entries())))


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


class check_runtime_deps(Command):
   description = 'Search for all needed runtime dependencies (and abort if not found)'
   user_options = []

   def initialize_options(self):
      pass

   def finalize_options(self):
      pass

   def check_failed(self, msg):
      raise SystemExit(
         "error: runtime dependency not found!" \
         "\n\n" + msg + "\n\n" \
         "NOTE: this dependency is not needed for building, but " \
         "is mandatory at runtime.\n\n" \
         "You can skip this test for the install stages using: \n"
         "setup.py install --no-runtime-deps-check\n")

   def run(self):
      import importlib

      # checking for python
      min_py_version = (3,4,0)
      if sys.version_info < min_py_version:
         msg = "This python version is too old. " \
               "Found: %d.%d.%d  (need >= %d.%d.%d)" % (
               sys.version_info[0], sys.version_info[1], sys.version_info[2],
               min_py_version[0],   min_py_version[1],   min_py_version[2])
         self.check_failed(msg)

      # checking for python-efl
      minv = '1.20.0'
      try:
         from efl import __version__ as efl_version
      except ImportError:
         self.check_failed("Cannot find python-efl on this system.")

      if LooseVersion(efl_version) < minv:
         msg = "Your python-efl version is too old. " \
               "Found: %s  (need >= %s)" % (efl_version, minv)
         self.check_failed(msg)

      # checking for disc id (or libdiscid)
      try:
         from libdiscid.compat import discid
      except ImportError:
         try:
            import discid
         except ImportError:
            msg = "Cannot find DiscID on this system. " \
                  "You must install the package: python-discid or python-libdiscid"
            self.check_failed(msg)

      # checking all other simpler deps
      deps = [
         ('XDG', 'xdg', 'python-xdg'),
         ('DBus', 'dbus', 'python-dbus'),
         ('PyUdev', 'pyudev', 'python-pyudev'),
         ('DiscID', 'discid', 'python-discid'),
         ('Mutagen', 'mutagen', 'python-mutagen'),
         ('BeautifulSoup', 'bs4', 'python-bs4 or python-beautifulsoup4'),
         ('LXML', 'lxml', 'python-lxml'),
         ('PIL', 'PIL', 'python-pillow or python-pil'),
      ]
      for name, module, pkg in deps:
         try:
            importlib.import_module(module)
         except ImportError:
            msg = "Cannot find %s on this system. " \
                  "You must install the package: %s" % (name, pkg)
            self.check_failed(msg)


class Build(build):
   def run(self):
      self.run_command("build_themes")
      self.run_command("build_i18n")
      build.run(self)


class Develop(Command):
   description = 'Run in-place from build dir without any install need'
   user_options = []

   def initialize_options(self):
      pass

   def finalize_options(self):
      pass

   def env_prepend(self, name, value):
      if name in os.environ:
         os.environ[name] = value + os.pathsep + os.environ[name]
      else:
         os.environ[name] = value

   def run(self):
      self.run_command("build")
      # PATH for the binaries to be searched in build/scripts-X.Y/
      self.env_prepend('PATH', './build/scripts-{0}.{1}/'.format(*sys.version_info))
      # PYTHONPATH for the epymc modules be searched in build/lib/
      self.env_prepend('PYTHONPATH', './build/lib/')
      # XDG config home in develop/config/
      conf = os.path.abspath('./develop/config/')
      if not os.path.exists(conf):
         os.makedirs(conf)
      os.environ['XDG_CONFIG_HOME'] = conf
      # XDG cache home in develop/cache/
      cache = os.path.abspath('./develop/cache/')
      if not os.path.exists(cache):
         os.makedirs(cache)
      os.environ['XDG_CACHE_HOME'] = cache
      # run epymc !
      os.system('epymc')  # TODO pass additional args


class Install(install):
   user_options = install.user_options + [
                  ('no-runtime-deps-check', None,
                   'disable the check for runtime dependencies')]

   def initialize_options(self):
      install.initialize_options(self)
      self.no_runtime_deps_check = False

   def finalize_options(self):
      install.finalize_options(self)

   def run(self):
      if not self.no_runtime_deps_check:
         self.run_command("check_runtime_deps")
      install.run(self)
 

class InstallLib(install_lib):
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

   requires = [
      'efl (>= 1.20.0)',
      'beautifulsoup4',
      'lxml',
      'mutagen',
      'dbus',
      'pyudev',
      'libdiscid',
      'xdg'
   ],

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
      'epymc.plugins.opticals',
      'epymc.plugins.mp_omxplayer',
   ],

   package_data = {
      'epymc': ['themes/*.edj', 'locale/*/LC_MESSAGES/*.mo'],
      'epymc.plugins.movies': ['*.png'],
      'epymc.plugins.tvshows': ['*.png'],
      'epymc.plugins.mame': ['*.png', '*.jpg'],
      'epymc.plugins.music': ['*.png'],
      'epymc.plugins.uitests': ['*.png', '*.jpg'],
      'epymc.plugins.calibrator': ['*.jpg', '*.png'],
      'epymc.plugins.onlinevideo': [ '*.png',
         'themoviedb/*',
         'youtube/*',
         'vimeo/*',
         'zapiks/*',
         'fantasticc/*',
         'porncom/*',
         'southparkstudios/*',
      ],
      'epymc.plugins.input_webserver': [
         'default/*',
         'mobile/*',
      ]
   },

   scripts = ['bin/epymc', 'bin/epymc_standalone',
              'bin/epymc_thumbnailer',
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
      'develop': Develop,
      'install': Install,
      'install_lib': InstallLib,
      'uninstall': Uninstall,
      'update_po': update_po,
      'check_po': check_po,
      'check_runtime_deps': check_runtime_deps,
   },
   command_options = {
      'install': {'record': ('setup.py', RECORD_FILE)}
   },
)
