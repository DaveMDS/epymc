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




if __name__ == "__main__":

    elementary.init()

    # create config dir if necessary
    user_dir = utils.config_dir_get()
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    
    #TODO add a system dir...but where??
    ini.read_from_files(['epymc.conf', os.path.join(user_dir, 'epymc.conf')])

    # init stuff
    downloader.init()
    sdb.init()
    gui.init_window()
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
    modules.shutdown_all() #TODO check this !!!
    ini.write_to_file(os.path.expanduser('~/.config/epymc/epymc.conf'))
    sdb.shutdown()
    downloader.shutdown()
    elementary.shutdown()

