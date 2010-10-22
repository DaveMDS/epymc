#!/usr/bin/env python

import sys
import os

import evas
import edje
import elementary

import modules
import utils
import gui
import config_gui
import mainmenu
import ini
import sdb
import downloader
import browser


def main():
   #init elementary
   elementary.init()

   # create config dir if necessary
   user_config_dir = utils.config_dir_get()
   if not os.path.exists(user_config_dir):
      os.makedirs(user_config_dir)
      os.makedir(os.path.join(user_config_dir, "modules"))
      os.makedir(os.path.join(user_config_dir, "themes"))

   #TODO add a system dir...but where??
   ini.read_from_files(['epymc.conf',
                        os.path.join(user_config_dir, 'epymc.conf')])

   # init stuff
   sdb.init()
   browser.init()
   if not gui.init(): return 2
   config_gui.init()
   mainmenu.init()
   downloader.init()

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
   downloader.shutdown()
   browser.shutdown()
   sdb.shutdown()

   # shutdown elementary
   elementary.shutdown()
   
   print 'Bye Bye...'

if __name__ == "__main__":
   sys.exit(main())
