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

from typing import Dict, Mapping

import os
from pathlib import Path
from configparser import ConfigParser

# from efl import evas, ecore, elementary

from epymc.modules import EmcModule
from epymc.browser import EmcBrowser, EmcItemClass
from epymc.gui import EmcDialog
from epymc.utils import EmcExec
import epymc.mainmenu as mainmenu
import epymc.input_events as input_events
# import epymc.browser as browser
import epymc.utils as utils
import epymc.gui as gui
import epymc.ini as ini


# pylint: disable=invalid-name
def DBG(msg):
    print('RETRO: %s' % msg)
    #  pass


class Emulator:
    """ Describe a single emulator """
    def __init__(self, name: str, data: Mapping):
        self.name = name
        self.label = data.get('name', 'Unknown')
        self.emulator = data.get('emulator', 'retroarch')
        self.cores = data.get('cores', '').split()
        self.extensions = data.get('extensions', '.zip').split()

    def __repr__(self):
        return f'<Emulator "{self.name}" cores="{self.cores}">'

    def run_game(self, rom_path):
        for core in self.cores:
            core_path = MOD.cores_path / (core + '_libretro.so')
            if core_path.exists():
                cmd = f'{self.emulator} -v -f -L "{core_path}" "{rom_path}"'
                input_events.events_freeze()
                EmcExec(cmd, done_cb=lambda _: input_events.events_unfreeze())
                return True

        EmcDialog(style='error', title='Cannot find a suitable retroarch core',
                  text=f'Cores: {", ".join(self.cores)}<br>'
                       f'Cores path: {MOD.cores_path}')
        return False


MOD_PATH = Path(os.path.dirname(__file__))
MOD: 'RetroModule'
EMULATORS: Dict[str, Emulator] = {}


def get_image_path(emu_name: str, image_name: str):
    image_name += '.svg'
    data_path = MOD_PATH / 'recalbox-next' / emu_name / 'data'
    path = data_path / image_name
    if path.exists():
        return path.as_posix()
    for lang in ('eu', 'us', 'jp'):  # TODO make priority configurable
        path = data_path / lang / image_name
        if path.exists():
            return path.as_posix()


def read_emulators_ini_files():
    """ read emulators.ini (system and user) and populate EMULATORS """
    if not EMULATORS:
        ini_path_sys = MOD_PATH / 'emulators.ini'
        ini_path_user = Path(utils.user_conf_dir) / 'emulators.ini'
        parser = ConfigParser()
        parser.read((ini_path_sys, ini_path_user))
        for section in parser.sections():
            EMULATORS[section] = Emulator(section, parser[section])


class RetroarchItemClass(EmcItemClass):
    def item_selected(self, url, emu):
        input_events.events_freeze()
        EmcExec('retroarch --fullscreen',
                done_cb=lambda _: input_events.events_unfreeze())

    def label_get(self, url, emu):
        return _('Run retroarch')

    def icon_get(self, url, emu):
        return 'icon/retro'

    def info_get(self, url, emu):
        return '<title>Retroarch</title><br>' \
               'Run retroarch menu for configuration<br><br>' \
               f'<name>Rom path</name> {MOD.roms_path}<br>' \
               f'<name>Retroarch path</name> {MOD.retroa_path}<br>' \
               f'<name>Cores path</name> {MOD.cores_path}'


class EmulatorItemClass(EmcItemClass):
    def item_selected(self, url, emu):
        MOD.browser.page_add(url, emu.label, None, MOD.populate_games_page)

    def label_get(self, url, emu):
        return emu.label

    def poster_get(self, url, emu):
        return get_image_path(emu.name, 'consolegame')

    def icon_end_get(self, url, emu):
        return get_image_path(emu.name, 'icon_filled')

    def info_get(self, url, emu):
        return f'<title>{emu.label}</title><br>' \
               f'<name>Roms path</name> {MOD.roms_path}/{emu.name}'


class GameItemClass(EmcItemClass):
    def item_selected(self, url, emu):
        emu.run_game(url)

    def label_get(self, url, emu):
        return os.path.basename(url)


class RetroModule(EmcModule):
    name = 'retro'
    label = _('RetroArch Games')
    icon = 'icon/retro'
    info = _('This module add the ability to browse and play games '
             'using the RetroArch emulator.')

    def __init__(self):
        global MOD
        MOD = self

        DBG('Init RETRO')
        self.browser: EmcBrowser
        self.roms_path: Path  # default to ~/.config/epymc/roms
        self.retroa_path: Path  # default to ~/.config/retroarch
        self.cores_path: Path  # default to ~/.config/retroarch/cores

        # init browser and mainmenu
        self.browser = EmcBrowser('RETRO', icon='icon/retro')
        mainmenu.item_add('retro', 50, _('RetroArch'),
                          'icon/retro', self.cb_mainmenu)
        ini.add_section('retro')

        # default roms_path (in epymc.ini)
        if not ini.has_option('retro', 'roms_path'):
            path = os.path.join(utils.user_conf_dir, 'roms')
            ini.set('retro', 'roms_path', path)
        self.roms_path = ini.get_path('retro', 'roms_path')
        if not self.roms_path.exists():
            self.roms_path.mkdir()

        # default retroarch_path (in epymc.ini)
        if not ini.has_option('retro', 'retroarch_path'):
            path = os.path.expanduser('~/.config/retroarch')
            ini.set('retro', 'retroarch_path', path)
        self.retroa_path = ini.get_path('retro', 'retroarch_path')

        # cores path
        self.cores_path = self.retroa_path / 'cores'

    def __shutdown__(self):
        DBG('Shutdown RETRO')
        self.browser.delete()
        mainmenu.item_del('retro')

    def cb_mainmenu(self):
        """ Mainmenu clicked, build the root page """
        # read emulators.ini
        read_emulators_ini_files()

        # set backdrop image
        gui.background_set((MOD_PATH / 'mainbg.jpg').as_posix())

        # restore a previous browser state (if available)
        if self.browser.freezed:
            self.browser.unfreeze()
            return

        self.browser.page_add('retro://root', _('RetroArch'), None,
                              self.populate_emulators_page)
        self.browser.show()
        mainmenu.hide()

        # check the retroarch executable exists and is in PATH
        EmcExec('retroarch --version', grab_output=True, 
                done_cb=self._retroarch_check_cb)

    def _retroarch_check_cb(self, output):
        if not output:
            EmcDialog(style='error', title='Cannot find retroarch executable',
                      text='Make sure retroarch is installed and it is in PATH')
            return
        # ok, retroarch found, check the retroarch path
        if not self.retroa_path.exists():
            EmcDialog(style='error', title='Cannot find retroarch folder',
                      text='Check that retroarch_path in epymc.conf is correct')

    def populate_emulators_page(self, browser, url):
        """ Create the emulators list """
        self.browser.item_add(RetroarchItemClass(), 'retro://retroarch', None)
        for emu in EMULATORS.values():
            roms_path = self.roms_path / emu.name
            if roms_path.exists():
                url = 'retro://' + emu.name
                self.browser.item_add(EmulatorItemClass(), url, emu)

    def populate_games_page(self, browser, url):
        """ Create the games list """
        folder = url.replace('retro://', '')
        emu = EMULATORS[folder]
        path = self.roms_path / folder
        for rom in sorted(path.iterdir()):
            if rom.suffix.lower() in emu.extensions:
                game_url = path / rom
                self.browser.item_add(GameItemClass(), game_url, emu)
