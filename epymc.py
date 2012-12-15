#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
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

import sys, os

import evas, ecore, ecore.file, edje, elementary, emotion

import epymc.modules as modules
import epymc.utils as utils
import epymc.gui as gui
import epymc.widgets as widgets
import epymc.config_gui as config_gui
import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.ini as ini
import epymc.sdb as sdb
import epymc.browser as browser


def main():
   #init elementary
   elementary.init()

   # set the base path
   utils.base_dir_set(os.path.dirname(__file__))

   # create config dir if necessary
   user_config_dir = utils.config_dir_get()
   if not os.path.exists(user_config_dir):
      os.makedirs(user_config_dir)
      os.mkdir(os.path.join(user_config_dir, 'modules'))
      os.mkdir(os.path.join(user_config_dir, 'themes'))
      os.mkdir(os.path.join(user_config_dir, 'channels'))

   #TODO add a system dir...but where??
   ini.read_from_files(['epymc.conf',
                        os.path.join(user_config_dir, 'epymc.conf')])
   ini.setup_defaults()

   # alert if CURL support not available (no download ability)
   if not ecore.file.download_protocol_available('http://'):
      print('ERROR. Ecore does not have CURL support.')
      return 2

   # init stuff
   sdb.init()
   browser.init()
   if not gui.init(): return 2
   config_gui.init()
   mainmenu.init()
   mediaplayer.init()

   # load & init modules
   modules.load_all()
   modules.init_all_by_config()

   # show the mainmenu
   mainmenu.show()

   # alert if the evas engine is not the requested one
   if elementary.engine_get() != ini.get('general', 'evas_engine'):
      widgets.EmcDialog(style = 'warning', text = 'Cannot start the engine: %s<br>' \
                        'Falling back to standard_x11'  % ini.get('general', 'evas_engine'))

   # run the main loop
   elementary.run()

   # shutdown
   modules.save_enabled()
   modules.shutdown_all()
   config_gui.shutdown()
   ini.write_to_file(os.path.join(user_config_dir, 'epymc.conf'))
   mediaplayer.shutdown()
   gui.shutdown()
   browser.shutdown()
   sdb.shutdown()

   # shutdown elementary
   elementary.shutdown()
   
   print 'Bye Bye...'
   return 0

if __name__ == '__main__':
   sys.exit(main())
