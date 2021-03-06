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

from epymc.modules import EmcModule
import epymc.mainmenu as mainmenu
import epymc.mediaplayer as mediaplayer
import epymc.events as events
import epymc.utils as utils
import epymc.storage as storage
from epymc.storage import EmcDevType
from epymc.gui import EmcDialog
from epymc.musicbrainz import MusicBrainz


def DBG(msg):
    # print('OPTICALS: %s' % msg)
    pass


class OpticalsModule(EmcModule):
    name = 'opticals'
    label = _('Optical Discs')
    icon = 'icon/optical'
    info = _('This module add support for playing DVD and Audio CD')

    _supported_types = (EmcDevType.DVD, EmcDevType.AUDIOCD)

    def __init__(self):
        DBG('Init module')
        self.insert_disk_dialog = None
        subitems = [
            (_('Play'), None, 'opticals://play'),
            (_('Eject'), None, 'opticals://eject'),
        ]
        mainmenu.item_add(self.name, 4, self.label, self.icon,
                          self.mainmenu_cb, subitems)

    def __shutdown__(self):
        DBG('Shutdown module')
        mainmenu.item_del(self.name)

    def check_and_play_disk(self):
        for device in storage.list_devices(self._supported_types):
            if device.type == EmcDevType.DVD:
                self.play_dvd(device)
                return True
            elif device.type == EmcDevType.AUDIOCD:
                self.play_audiocd(device)
                return True
        return False

    def play_dvd(self, device):
        self.insert_disk_dialog_destroy()
        mediaplayer.play_url('dvd://' + device.device)

    def play_audiocd(self, device):
        self.insert_disk_dialog_destroy()
        ret = MusicBrainz().get_cdrom_info(device.device, self._audiocd_info_cb,
                                           device=device)
        if isinstance(ret, dict):
            self._audiocd_info_cb(ret, device)
        elif ret is False:
            self._audiocd_info_cb(None, device)

    @staticmethod
    def _audiocd_info_cb(album, device):
        playlist = mediaplayer.playlist
        playlist.clear()
        if album is None:
            # MusicBrainz failed, just show plain tracks
            for i in range(1, device.audio_tracks + 1):
                url = 'cdda://{}'.format(i)
                meta = {
                    'url': url, 'tracknumber': i,
                    'title': _('Audio track {}').format(i),
                }
                playlist.append(url=url, metadata=meta)
        else:
            # Use MusicBrainz infos
            for trk in album['tracks']:
                url = 'cdda://{}'.format(trk['num'])
                meta = {
                    'url': url,
                    'title': trk['title'],
                    'length': trk['length'],
                    'tracknumber': trk['num'],
                    'artist': ', '.join(album['artists']),
                    'album': album['title'],
                    'poster': album['cover_url'],
                }
                playlist.append(url=url, metadata=meta)

    def mainmenu_cb(self, url=None):
        if url is None or url == 'opticals://play':
            if not self.check_and_play_disk():
                self.insert_disk_dialog_create()
        elif url == 'opticals://eject':
            utils.EmcExec('eject')

    def insert_disk_dialog_create(self):
        self.insert_disk_dialog = \
            EmcDialog(style='cancel', title=_('No disc found'),
                      text=_('Please insert a disc (DVD or Audio CD)'),
                      canc_cb=self.insert_disk_dialog_destroy)
        events.listener_add('opticals', self.events_cb)

    def insert_disk_dialog_destroy(self, dia=None):
        events.listener_del('opticals')
        if self.insert_disk_dialog is not None:
            self.insert_disk_dialog.delete()
            self.insert_disk_dialog = None

    def events_cb(self, event):
        if event == 'STORAGE_CHANGED':
            self.check_and_play_disk()
