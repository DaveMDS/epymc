
from setuptools import setup, find_packages



# setuptools reference:
# http://pythonhosted.org/setuptools/setuptools.html
# http://pythonhosted.org/setuptools/pkg_resources.html
# http://docs.python.org/dev/distutils/index.html
# http://peak.telecommunity.com/DevCenter/PkgResources

# other "complex" setup.py scripts:
# http://bazaar.launchpad.net/~gnome-terminator/terminator/trunk/files

# commands to investigate:
# sdist, bdist, bdist_egg, bdist_rpm, bdist_deb
# build, install, develop, clean

# --single-version-externally-managed
# --prefix=
# --install-layout=deb

# Note that the various alternate installation schemes are mutually exclusive:
# you can pass --user, or --home, or --prefix and --exec-prefix,
#   or --install-base and --install-platbase
# but you can't mix from these groups.

# packaging references:
# http://www.debian.org/doc/packaging-manuals/python-policy/
# http://developer.ubuntu.com/packaging/html/python-packaging.html
# http://shallowsky.com/blog/programming/packaging-python-rpm.html
# http://shallowsky.com/blog/programming/python-debian-packages-w-stdeb.html

# http://bugs.gramps-project.org/print_bug_page.php?bug_id=2621


# import setuptools
# print dir(setuptools)
# exit(0)

setup(
   name = 'EpyMC',
   version = '0.9',
   

   # metadata
   author = 'Davide "davemds" Andreoli',
   author_email = 'dave@gurumeditation.it',
   url = 'http://code.google.com/p/e17mods/wiki/EpyMC',
   description = 'EFL based Media Center',
   license = 'GPL3',
   # keywords = 'hello world example examples',  # TODO
   # long_description = 'hello world example examples', # TODO

   packages = find_packages(),
   # packages = [
      # 'epymc',
      # 'epymc.plugins',
      # 'epymc.plugins.movies',
      # 'epymc.plugins.input_keyb',
   # ],

   entry_points = {
      # 'console_scripts': [
         # 'foo = my_package.some_module:main_func',
         # 'bar = other_module:some_func',
      # ],
      'gui_scripts': [
         'epymc = epymc.main:start_epymc',
      ],
      'epymc_modules': [
         'input_keyb = epymc.plugins.input_keyb:KeyboardModule',
         'input_joy = epymc.plugins.input_joy:JoystickModule',
         'input_lirc = epymc.plugins.input_lirc:LircModule',

         'movies = epymc.plugins.movies:MoviesModule',
         'tvshows = epymc.plugins.tvshows:TvShowsModule',
         'onlinevideo = epymc.plugins.onlinevideo:OnlinevideoModule',
         'music = epymc.plugins.music:MusicModule',

         # TODO move those as a standalone module (to demostrate how)
         'uitests = epymc.plugins.uitests:UiTestsModule',
         'input_webserver = epymc.plugins.input_webserver:WebserverModule',
      ]
   },

   
   
   # data files that goens inside the epymc package
   package_data = {
      'epymc': ['themes/*.edj'],
      'epymc.plugins.movies': ['menu_bg.png'],
      'epymc.plugins.tvshows': ['menu_bg.png'],
      'epymc.plugins.onlinevideo': ['menu_bg.png'],
      'epymc.plugins.music': ['menu_bg.png'],
      'epymc.plugins.uitests': ['menu_bg.png'], # TODO move out of main tree
   },

   # data_files = [
      # ('themes', ['themes/default.edj']),
   # ],
   # data_files=[('bitmaps', ['bm/b1.gif', 'bm/b2.gif']),
                  # ('config', ['cfg/data.cfg']),
                  # ('/etc/init.d', ['init-script'])]
   data_files = [
      ('share/applications', ['data/desktop/epymc.desktop']),
      ('share/icons', ['data/desktop/epymc.png']),
   ],

   # dependencies
   install_requires = 'efl >= 1.7.99',

   # ARGH none of the above work :/
   dependency_links = [
     'http://git.enlightenment.org/bindings/python/python-efl.git#egg=efl-1.7.99',
     'git+http://git.enlightenment.org/bindings/python/python-efl.git#egg=efl-1.7.99',
     'git+ssh://git@git.enlightenment.org/bindings/python/python-efl.git#egg=efl-1.7.99',
   ],


)
