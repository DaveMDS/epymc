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

import os
import epymc.utils as utils
import epymc.gui as gui


def DBG(*args):
    print('YTDL:', *args)
    pass


class YoutubeDL(object):
    """ Helper class to interact with the youtube-dl executable """

    def __init__(self):
        self.exe = os.path.join(utils.user_cache_dir, 'youtube-dl')
        self._update_dialog = None
        self._done_cb = None
        self._done_cb_kargs = None
        self._url_dialog = None

    @property
    def installed(self):
        """ True if youtube-dl is already installed """
        return os.path.exists(self.exe)

    def get_real_video_url(self, url, done_cb, **kargs):
        """ Scrape the given url using youtube-dl
        Args:
           url: any url supported by youtube-dl
           done_cb: function to call when the process is completed
              signature: func(real_url, **kargs)
           **kargs: any other keyword arguments will be passed back in done_cb
        """
        DBG('Getting real url for:', url)
        self._done_cb = done_cb
        self._done_cb_kargs = kargs
        txt = _('Please wait while searching the video...') + '<br><br>' + \
              _('For info and credits please visit:') + '<br>' + \
              '<info>rg3.github.io/youtube-dl</>'
        self._url_dialog = gui.EmcDialog(style='minimal', title=_('Youtube-DL'),
                                         text=txt, spinner=True)
        utils.EmcExec('{} --get-url --format best "{}"'.format(self.exe, url),
                      grab_output=True, done_cb=self._get_real_video_url_cb)

    def _get_real_video_url_cb(self, cmd_output):
        self._url_dialog.delete()
        self._done_cb(cmd_output, **self._done_cb_kargs)

    def check_update(self, verbose=True, quiet=False, done_cb=None, **kargs):
        """ Check if a newer version is available and download if needed

        Args:
           verbose (bool): Show the progress dialog also while checking versions
           quiet (bool): Do not show any dialog at all
           done_cb: function to call when the process is completed
              signature: func(success, dialog, **kargs)
           **kargs: any other keyword arguments will be passed back in done_cb
        """
        self._local_version = None
        self._remote_version = None
        self._update_dialog = None
        self._update_text = ''
        self._quiet_update = quiet
        self._done_cb = done_cb
        self._done_cb_kargs = kargs

        txt = _('Checking for updates, please wait.') + '<br>'
        if verbose:
            self._update_dialog = gui.EmcDialog(style='progress', text=txt,
                                                title=_('Youtube-DL'))
        else:
            self._update_text += txt

        # check local version...
        utils.EmcExec('{} --version'.format(self.exe), grab_output=True,
                      done_cb=self._local_vers_cb)
        # check remote version...
        utils.EmcUrl('http://youtube-dl.org/latest/version',
                     done_cb=self._remote_vers_cb)

    def _local_vers_cb(self, version):
        self._local_version = version.strip() if version else _('Unknown')
        DBG('Local version:', self._local_version)
        txt = '<name>{}:</name> {}<br>'.format(_('Local version'),
                                               self._local_version)
        if self._update_dialog:
            self._update_dialog.text_append(txt)
        else:
            self._update_text += txt
        self._local_or_remote_done()

    def _remote_vers_cb(self, url, status, version):
        self._remote_version = version.strip() if status == 200 else _('Unknown')
        DBG('Upstream version:', self._remote_version)
        txt = '<name>{}:</name> {}<br>'.format(_('Upstream version'),
                                               self._remote_version)
        if self._update_dialog:
            self._update_dialog.text_append(txt)
        else:
            self._update_text += txt
        self._local_or_remote_done()

    def _local_or_remote_done(self):
        if self._local_version is None or self._remote_version is None:
            return

        if self._local_version == _('Unknown') or \
                self._remote_version == _('Unknown') or \
                self._remote_version != self._local_version:
            self._download_latest()
            return

        txt = '<success>{}</success>'.format(_('Already updated'))
        if self._update_dialog:
            self._update_dialog.text_append(txt)
            self._update_dialog.progress_set(1.0)
        else:
            self._update_text += txt
        if callable(self._done_cb):
            self._done_cb(True, self._update_dialog, **self._done_cb_kargs)
        elif self._update_dialog:
            self._update_dialog.delete()

    def _download_latest(self):
        txt = '<info>{}</info><br>'.format(_('Updating to latest release...'))
        if self._update_dialog:
            self._update_dialog.text_append(txt)
        elif self._quiet_update is False:
            self._update_text += txt
            self._update_dialog = gui.EmcDialog(style='progress',
                                                title=_('Youtube-DL'),
                                                text=self._update_text)

        utils.download_url_async('http://youtube-dl.org/latest/youtube-dl',
                                 dest=self.exe + '.temp',
                                 progress_cb=self._dwn_progress_cb,
                                 complete_cb=self._dwn_complete_cb)

    def _dwn_progress_cb(self, dest, dltotal, dlnow):
        if self._update_dialog:
            self._update_dialog.progress_set((dlnow / dltotal) if dltotal else 0)

    def _dwn_complete_cb(self, dest, status):
        if status == 200:
            os.chmod(dest, 0o0744)  # (make it executable)
            os.rename(dest, self.exe)  # (atomically remove ".temp")
            txt = '<success>{}</success>'.format(_('Download completed'))
            if self._update_dialog:
                self._update_dialog.text_append(txt)
            else:
                self._update_text += txt
        else:
            DBG("ERROR: download failed")
            txt = '<failure>{}</failure>'.format(_('Download failed'))
            if self._update_dialog:
                self._update_dialog.text_append(txt)
            else:
                self._update_text += txt
        if callable(self._done_cb):
            self._done_cb(True if status == 200 else False, self._update_dialog,
                          **self._done_cb_kargs)
        elif self._update_dialog:
            self._update_dialog.delete()
