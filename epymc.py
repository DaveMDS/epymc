#!/usr/bin/env python

import sys
import os

import evas
import ecore
import ecore.file
import edje
import elementary
import emotion

import epymc.modules as modules
import epymc.utils as utils
import epymc.gui as gui
import epymc.config_gui as config_gui
import epymc.mainmenu as mainmenu
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
      os.makedir(os.path.join(user_config_dir, "modules"))
      os.makedir(os.path.join(user_config_dir, "themes"))

   #TODO add a system dir...but where??
   ini.read_from_files(['epymc.conf',
                        os.path.join(user_config_dir, 'epymc.conf')])

   # alert if CURL support not available (no download ability)
   if not ecore.file.download_protocol_available("http://"):
      print("WARNING. Ecore must be comiled with CURL support. Download disabled")

   # init stuff
   sdb.init()
   browser.init()
   if not gui.init(): return 2
   config_gui.init()
   mainmenu.init()

   # load & init modules
   modules.load_all()
   modules.init_all_by_config()

   # show the mainmenu
   mainmenu.show()

   # run the main loop
   elementary.run()

   # shutdown
   modules.shutdown_all()
   ini.write_to_file(os.path.join(user_config_dir, 'epymc.conf'))
   gui.shoutdown()
   browser.shutdown()
   sdb.shutdown()

   # shutdown elementary
   elementary.shutdown()
   
   print 'Bye Bye...'
   return 0

if __name__ == "__main__":
   sys.exit(main())
