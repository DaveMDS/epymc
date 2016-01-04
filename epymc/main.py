#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2015 Davide Andreoli <dave@gurumeditation.it>
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

from __future__ import absolute_import, print_function

import sys, os, gettext, logging, argparse

from efl import evas, ecore, edje, elementary, emotion

import epymc.utils as utils

# init gettext
# install the _() and ngettext() func in the main namespace
# localle .mo files are searched directly inside the epymc package
localedir = os.path.join(utils.emc_base_dir, 'locale')
gettext.install('epymc', names='ngettext', localedir=localedir)

import epymc.modules as modules
import epymc.gui as gui
import epymc.mainmenu as mainmenu
import epymc.config_gui as config_gui
import epymc.mediaplayer as mediaplayer
import epymc.ini as ini
import epymc.sdb as sdb
import epymc.browser as browser


def start_epymc(standalone=False):

   # parse command line arguments
   parser = argparse.ArgumentParser(description='Emotion Media Center')
   parser.add_argument('-a', '--activity',
                       help='start directy in the given activity')
   parser.add_argument('-f', '--fullscreen', action='store_true',
                       help='start in fullscreen')
   parser.add_argument('--standalone', action='store_true',
                       help='start in X without a WM (fullscreen)')
   parser.add_argument('mediafile', nargs='?')
   args = parser.parse_args()

   # setup efl logging (you also need to set EINA_LOG_LEVEL=X)
   l = logging.getLogger("efl")
   h = logging.StreamHandler()
   h.setFormatter(logging.Formatter("EFL %(levelname)s %(message)s"))
   l.addHandler(h)
   l.setLevel(logging.DEBUG)

   # tag for pulse audio... name not working here, icon yes  :/
   os.environ['PULSE_PROP_media.role'] = 'video'
   os.environ['PULSE_PROP_application.name'] = 'Emotion Media Center'
   os.environ['PULSE_PROP_application.icon_name'] = 'epymc'
   
   # init elementary
   elementary.init()
   elementary.need_ethumb()

   # create config/cache dirs if necessary
   if not os.path.exists(utils.user_cache_dir):
      os.makedirs(utils.user_cache_dir)
   if not os.path.exists(utils.user_conf_dir):
      os.makedirs(utils.user_conf_dir)
   try: os.mkdir(os.path.join(utils.user_conf_dir, 'plugins'))
   except OSError: pass
   try: os.mkdir(os.path.join(utils.user_conf_dir, 'themes'))
   except OSError: pass
   try: os.mkdir(os.path.join(utils.user_conf_dir, 'channels'))
   except OSError: pass
   try: os.mkdir(os.path.join(utils.user_conf_dir, 'subtitles'))
   except OSError: pass

   #TODO add a system dir...but where??
   ini.read_from_files(['epymc.conf',
                        os.path.join(utils.user_conf_dir, 'epymc.conf')])
   ini.setup_defaults()

   # init stuff
   sdb.init()
   if not gui.init():
      return 1
   browser.init()
   mainmenu.init()
   config_gui.init()
   mediaplayer.init()

   # load & init modules
   modules.load_all()
   modules.init_all_by_config()

   # show the mainmenu
   mainmenu.show()

   # if mediafile given on command line play it (must be a video file)
   if args.mediafile and os.path.exists(args.mediafile):
      mediaplayer.play_url(os.path.abspath(args.mediafile))
      mediaplayer.title_set(os.path.basename(args.mediafile))
   # or autostart the give activity (ex: --activity movies)
   elif args.activity:
      mainmenu.item_activate(args.activity)
   # fullscreen requested from command line
   if args.fullscreen:
      gui.fullscreen_set(True)

   # run standalone (inside X without a WM)
   if standalone or args.standalone:
      from efl import ecore_x
      ecore_x.init()
      # set fullscreen
      x, y, w, h = gui.win.screen_size
      gui.win.size = (w, h)
      # give focus to the win
      ecore_x_win = ecore_x.Window_from_xid(gui.win.xwindow_xid)
      ecore_x_win.focus()

   # alert if run from python < 3 (lots of translation issue with 2.7)
   if utils.is_py2():
      txt = '<b>PYTHON 2 IS NOT SUPPORTED ANYMORE!</b><br><br>' \
            'You are using python2, it is old!<br>' \
            'EpyMC works much better with py3, even more if you are not ' \
            'using the english language.<br><br>' \
            '<b>YOU MUST SWITCH TO PYTHON 3 !!!</b>'
      gui.EmcDialog(style='warning', text=txt)

   # run the main loop
   elementary.run()

   # shutdown
   modules.save_enabled()
   modules.shutdown_all()
   config_gui.shutdown()
   ini.write_to_file(os.path.join(utils.user_conf_dir, 'epymc.conf'))
   mediaplayer.shutdown()
   browser.shutdown()
   gui.shutdown()
   sdb.shutdown()

   # shutdown elementary
   elementary.shutdown()
   
   print('Bye Bye...')
   return 0

if __name__ == '__main__':
   sys.exit(start_epymc())
