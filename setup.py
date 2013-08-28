
from setuptools import setup, find_packages


# reference:
# http://pythonhosted.org/setuptools/setuptools.html
# http://pythonhosted.org/setuptools/pkg_resources.html
# http://peak.telecommunity.com/DevCenter/PkgResources


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

   
   
   # data files
   package_data = {
      'epymc': ['themes/*.edj'],
   },

   # data_files = [
      # ('themes', ['themes/default.edj']),
   # ],
   # data_files=[('bitmaps', ['bm/b1.gif', 'bm/b2.gif']),
                  # ('config', ['cfg/data.cfg']),
                  # ('/etc/init.d', ['init-script'])]

   # dependencies
   install_requires = 'efl >= 1.7.99',

   # ARGH none of the above work :/
   dependency_links = [
     'http://git.enlightenment.org/bindings/python/python-efl.git#egg=efl-1.7.99',
     'git+http://git.enlightenment.org/bindings/python/python-efl.git#egg=efl-1.7.99',
     'git+ssh://git@git.enlightenment.org/bindings/python/python-efl.git#egg=efl-1.7.99',
   ],


)
