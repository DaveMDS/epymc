#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2014 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of EpyMC, an EFL based Media Center written in Python.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, os, gettext

from efl import evas, ecore, edje, elementary, emotion

import epymc.modules as modules
import epymc.utils as utils
import epymc.gui as gui
import epymc.mainmenu as mainmenu
import epymc.config_gui as config_gui
import epymc.mediaplayer as mediaplayer
import epymc.ini as ini
import epymc.sdb as sdb
import epymc.browser as browser


def start_epymc():

   # init gettext
   localedir = os.path.join(utils.emc_base_dir, 'locale')
   gettext.install('epymc', localedir=localedir)

   # init elementary
   elementary.init()

   # create config dir if necessary
   if not os.path.exists(utils.user_conf_dir):
      os.makedirs(utils.user_conf_dir)
      os.mkdir(os.path.join(utils.user_conf_dir, 'plugins'))
      os.mkdir(os.path.join(utils.user_conf_dir, 'themes'))
      os.mkdir(os.path.join(utils.user_conf_dir, 'channels'))

   #TODO add a system dir...but where??
   ini.read_from_files(['epymc.conf',
                        os.path.join(utils.user_conf_dir, 'epymc.conf')])
   ini.setup_defaults()

   # init stuff
   sdb.init()
   browser.init()
   gui_return = gui.init()
   if gui_return < 1: return 2
   mainmenu.init()
   config_gui.init()
   mediaplayer.init()

   # load & init modules
   modules.load_all()
   modules.init_all_by_config()

   # show the mainmenu
   mainmenu.show()

   # alert if the evas engine is not the requested one
   if gui_return == 2:
      gui.EmcDialog(style = 'warning',
                    text = 'Cannot initialize the engine:<br>%s<br>' \
                           'Falling back to standard_x11'  % \
                           ini.get('general', 'evas_engine'))

   # run the main loop
   elementary.run()

   # shutdown
   modules.save_enabled()
   modules.shutdown_all()
   config_gui.shutdown()
   ini.write_to_file(os.path.join(utils.user_conf_dir, 'epymc.conf'))
   mediaplayer.shutdown()
   gui.shutdown()
   browser.shutdown()
   sdb.shutdown()

   # shutdown elementary
   elementary.shutdown()
   
   print('Bye Bye...')
   return 0

if __name__ == '__main__':
   sys.exit(start_epymc())
