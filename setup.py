#!/usr/bin/env python

import os, glob, subprocess, shutil
from distutils.log import warn, info, error
from setuptools import setup, find_packages, Command

#
# usage:
#
# python setup.py install [--prefix|--user|--root]
# python setup.py uninstall
# python setup.py build_themes
# python setup.py clean [--all]
#
#
# setuptools reference:
# http://pythonhosted.org/setuptools/setuptools.html
# http://pythonhosted.org/setuptools/pkg_resources.html
# http://docs.python.org/dev/distutils/index.html
# http://peak.telecommunity.com/DevCenter/PkgResources
# http://ziade.org/2007/09/30/extending-setuptools-adding-a-new-command/
#
# commands to investigate:
# sdist, bdist, bdist_egg, bdist_rpm, bdist_deb, develop
#
# packaging references:
# http://www.debian.org/doc/packaging-manuals/python-policy/
# http://developer.ubuntu.com/packaging/html/python-packaging.html
# http://shallowsky.com/blog/programming/packaging-python-rpm.html
# http://shallowsky.com/blog/programming/python-debian-packages-w-stdeb.html
# http://bugs.gramps-project.org/print_bug_page.php?bug_id=2621
#

# ERR<8850>:ecore lib/ecore/ecore_pipe.c:626 _ecore_pipe_read() Only read 3 bytes from the pipe, although we need to read 4 bytes.
# munmapping !

class CustomCommand(Command):
   description = ''
   user_options = []
   def initialize_options(self): pass
   def finalize_options(self): pass
   def run(self): pass


class BuildThemes(CustomCommand):
   description = 'rebuild all the themes found in data/themes using edje_cc'
   def run(self):
      for theme_dir in glob.glob('data/themes/*'):
         name = os.path.basename(theme_dir)
         edc_name = os.path.join(theme_dir, name + '.edc')
         edj_name = os.path.join(theme_dir, name + '.edj')
         info('building theme: ' + name)
         subprocess.call(['edje_cc', '-v', edc_name,
                                     '-id', os.path.join(theme_dir, 'images'),
                                     '-fd', os.path.join(theme_dir, 'fonts')
                        ])
         dest = os.path.join('epymc', 'themes', name + '.edj')
         shutil.move(edj_name, dest)
         os.chmod(dest, 0644)


class Uninstall(CustomCommand):
   description = "Attempt an uninstall from the install --record file"
   def run(self):
      dirs = []
      files = [line.strip() for line in open('install_record.txt')]
      for f in files:
         if os.path.isfile(f):
            if not os.path.dirname(f) in dirs:
               dirs.append(os.path.dirname(f))
            try:
               os.unlink(f)
               info('removing file %s' % f)
            except OSError:
               warn('could NOT delete %s' % f)

      for d in reversed(dirs):
         try:
            os.rmdir(d)
            info('removing empty dir %s' % d)
         except OSError:
            warn('NOT removing not empty dir %s' % d)


setup(
   name = 'EpyMC',
   version = '0.9',
   author = 'Davide "davemds" Andreoli',
   author_email = 'dave@gurumeditation.it',
   url = 'http://code.google.com/p/e17mods/wiki/EpyMC',
   description = 'EFL based Media Center',
   license = 'GNU GPL v3',

   requires = ['efl (>= 1.7.999)'],
   provides = ['epymc'],

   # Automatically search all packages (dirs that have an __init__.py file)
   packages = find_packages(),

   entry_points = {
      # This will create the 'epymc' executable script
      'gui_scripts': [
         'epymc = epymc.main:start_epymc',
      ],
      # This define a custom entry point called 'epymc_modules'
      # 'epymc_modules': [
         # 'input_keyb = epymc.plugins.input_keyb:KeyboardModule',
         # 'input_joy = epymc.plugins.input_joy:JoystickModule',
         # 'input_lirc = epymc.plugins.input_lirc:LircModule',
# 
         # 'movies = epymc.plugins.movies:MoviesModule',
         # 'tvshows = epymc.plugins.tvshows:TvShowsModule',
         # 'onlinevideo = epymc.plugins.onlinevideo:OnlinevideoModule',
         # 'music = epymc.plugins.music:MusicModule',
         # 'mame = epymc.plugins.mame:MameModule',

         # TODO move those as a standalone module (to demostrate how)
         # ...and to test that the setuptools entrypoints magic work
         #    also using the single_version_externally_managed option.
         # 'uitests = epymc.plugins.uitests:UiTestsModule',
         # 'input_webserver = epymc.plugins.input_webserver:WebserverModule',
      # ]
   },

   # Include all the data files found in every packages.
   include_package_data = True,

   # Those are the data files that goes outside of the packages.
   data_files = [
      ('share/applications', ['data/desktop/epymc.desktop']),
      ('share/icons', ['data/desktop/epymc.png']),
   ],

   # Custom commands for the setup.py invocation.
   cmdclass = {
      'build_themes': BuildThemes,
      'uninstall': Uninstall,
   },

   # In real the package IS zip safe, but lots of data files (such as .edj
   # themes and images) would need to be extracted in order for efl to load them.
   # So as an optization we tell setuptools to not create the zipped egg.
   zip_safe = False,
)
