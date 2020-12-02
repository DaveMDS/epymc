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

from typing import Callable, Any

from epymc import events


STANDARD_EVENTS = """
UP DOWN LEFT RIGHT OK BACK EXIT
PLAY STOP PAUSE TOGGLE_PAUSE
FORWARD BACKWARD FAST_FORWARD FAST_BACKWARD
PLAYLIST_NEXT PLAYLIST_PREV PLAYLIST_CHANGED
VOLUME_UP VOLUME_DOWN VOLUME_MUTE
SUBS_DELAY_MORE SUBS_DELAY_LESS SUBS_DELAY_ZERO
TOGGLE_FULLSCREEN
VIEW_LIST VIEW_POSTERGRID VIEW_COVERGRID
BIGGER SMALLER
TOGGLE_DVD_MENU
"""

EVENT_CONTINUE = True
EVENT_BLOCK = False

_listeners = []
_freezed = False


def DBG(*args):
    # print('INPUT_EVENTS: ', *args)
    pass


class Listener:
    """ Class to hold the info for each listener """
    def __init__(self, name: str, cb: Callable, data: Any):
        self.name: str = name
        self.cb: Callable = cb
        self.data: Any = data


def listener_add(name: str, event_cb: Callable, cb_data: Any = None):
    """ Add a new listener to the events chain """
    lis = Listener(name, event_cb, cb_data)
    _listeners.append(lis)

    DBG('Listener Added:', lis)
    for lis in _listeners:
        DBG('  *', lis.name)


def listener_del(name: str):
    """ Delete the given listener """
    DBG('Listener Del:', name)
    for lis in _listeners:
        if lis.name == name:
            _listeners.remove(lis)
            break


def listener_promote(name: str):
    """ Put the given listener on top of the listeners stack """
    DBG('Listener Promote: ' + name)
    for lis in _listeners:
        if lis.name == name:
            _listeners.remove(lis)
            _listeners.append(lis)
            break


def event_emit(event: str):
    """ Emit the given event """
    events.event_emit('KEEP_ALIVE')
    if _freezed:
        return

    DBG('Emit Event:', event, ' listeners:', len(_listeners))
    for lis in reversed(_listeners):
        if lis.data:
            res = lis.cb(event, lis.data)
        else:
            res = lis.cb(event)
        DBG(f"  ->  '{lis.name}' ({'continue' if res else 'block'})")
        if res == EVENT_BLOCK:
            break


def events_freeze():
    """ Stop the emission of all events """
    global _freezed
    _freezed = True


def events_unfreeze():
    """ Restart the emission of all events """
    global _freezed
    _freezed = False
