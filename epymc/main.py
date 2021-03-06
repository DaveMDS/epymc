#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2018 Davide Andreoli <dave@gurumeditation.it>
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

import os
import sys
import locale
import gettext
import logging
import argparse

from efl import evas
from efl import ecore
from efl import edje
from efl import elementary
from efl import emotion

import epymc.utils as utils

# init gettext
# install the _() and ngettext() func in the main namespace
# localle .mo files are searched directly inside the epymc package
localedir = os.path.join(utils.emc_base_dir, 'locale')
gettext.install('epymc', names=['ngettext'], localedir=localedir)

# set locale to user preferred (aka the one set in env) locale
locale.setlocale(locale.LC_ALL, '')

from epymc import __version__ as emc_v
from epymc import modules
from epymc import gui
from epymc import mainmenu
from epymc import config_gui
from epymc import mediaplayer
from epymc import ini
from epymc import sdb
from epymc import browser
from epymc import storage
from epymc import thumbnailer


def start_epymc(standalone=False):
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Emotion Media Center v%s' % emc_v)
    parser.add_argument('-a', '--activity',
                        help='start directy in the given activity')
    parser.add_argument('-f', '--fullscreen', action='store_true',
                        help='start in fullscreen')
    parser.add_argument('-y', '--youtube-dl', action='store_true',
                        help='use youtube-dl to scrape and play mediaurl')
    parser.add_argument('--standalone', action='store_true',
                        help='start in X without a WM (fullscreen)')
    parser.add_argument('mediaurl', nargs='?',
                        help='local file or remote url to play')
    args = parser.parse_args()

    # setup efl logging (you also need to set EINA_LOG_LEVEL=X)
    logger = logging.getLogger("efl")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("EFL %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # tag for pulse audio... name not working here, icon yes  :/
    os.environ['PULSE_PROP_media.role'] = 'video'
    os.environ['PULSE_PROP_application.name'] = 'Emotion Media Center'
    os.environ['PULSE_PROP_application.icon_name'] = 'epymc'

    # init elementary
    # elementary.init()
    # elementary.need_ethumb()

    # create config/cache dirs if necessary
    if not os.path.exists(utils.user_cache_dir):
        os.makedirs(utils.user_cache_dir)
    if not os.path.exists(utils.user_conf_dir):
        os.makedirs(utils.user_conf_dir)
    try:
        os.mkdir(os.path.join(utils.user_conf_dir, 'plugins'))
    except OSError:
        pass
    try:
        os.mkdir(os.path.join(utils.user_conf_dir, 'themes'))
    except OSError:
        pass
    try:
        os.mkdir(os.path.join(utils.user_conf_dir, 'channels'))
    except OSError:
        pass
    try:
        os.mkdir(os.path.join(utils.user_conf_dir, 'subtitles'))
    except OSError:
        pass

    # TODO add a system dir...but where??
    ini.read_from_files(['epymc.conf',
                         os.path.join(utils.user_conf_dir, 'epymc.conf')])
    ini.setup_defaults()

    # init stuff
    sdb.init()
    thumbnailer.init()
    if not gui.init():
        return 1
    browser.init()
    mainmenu.init()
    config_gui.init()
    mediaplayer.init()
    storage.init()

    # load & init modules
    modules.load_all()
    modules.init_all_by_config()

    # show the mainmenu
    mainmenu.show()

    # use youtube-dl to scrape and play the url given on command line
    if args.youtube_dl and args.mediaurl:
        from epymc.youtubedl import YoutubeDL

        ytdl = YoutubeDL()

        def ytdl_url_cb(real_url):
            if not real_url:
                gui.EmcDialog(style='error',
                              text=_('youtube-dl is unable to scrape the given url'))
            else:
                print('Real video url:', real_url)
                mediaplayer.play_url(real_url)
                mediaplayer.title_set('')

        def ytdl_update_cb(success, dialog):
            if dialog:
                dialog.delete()
            print('Scraping url:', args.mediaurl)
            ytdl.get_real_video_url(args.mediaurl, ytdl_url_cb)

        print('Checking for ytdl updates')
        if ini.get_bool('videochannels', 'autoupdate_ytdl') is True:
            ytdl.check_update(verbose=True, done_cb=ytdl_update_cb)
        else:
            ytdl_update_cb(True, None)

    # if mediaurl given on command line play it (must be a video file)
    elif args.mediaurl:
        if args.mediaurl.startswith(('http://', 'https://')):
            mediaplayer.play_url(args.mediaurl)
            mediaplayer.title_set('')
        elif os.path.exists(args.mediaurl):
            mediaplayer.play_url(os.path.abspath(args.mediaurl))
            mediaplayer.title_set(os.path.basename(args.mediaurl))
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
        x, y, w, handler = gui.win.screen_size
        gui.win.size = (w, handler)
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
    storage.shutdown()
    config_gui.shutdown()
    ini.write_to_file(os.path.join(utils.user_conf_dir, 'epymc.conf'))
    mediaplayer.shutdown()
    browser.shutdown()
    gui.shutdown()
    thumbnailer.shutdown()
    sdb.shutdown()

    print('Bye Bye...')
    return 0


if __name__ == '__main__':
    sys.exit(start_epymc())
