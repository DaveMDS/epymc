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

from efl import elementary as elm

from epymc import gui, input_events

_list: gui.EmcList  # MainmenuList widget (the main horizontal list)


def init():
    global _list

    _list = gui.EmcList(parent=gui.layout, horizontal=True,
                        focus_allow=True, focus_on_select=True,
                        select_mode=elm.ELM_OBJECT_SELECT_MODE_ALWAYS,
                        style='mainmenu', name='MainMenuList')
    _list.policy = elm.ELM_SCROLLER_POLICY_OFF, elm.ELM_SCROLLER_POLICY_OFF
    gui.swallow_set('mainmenu.list.swallow', _list)

    item_add('exit', 200, _('Exit'), 'icon/exit', lambda: gui.ask_to_exit())


def show():
    _list.focus_allow = True
    _list.focus = True
    _list.callback_clicked_double_add(_cb_item_activated)
    _list.callback_selected_add(_cb_item_selected)
    if not _list.selected_item:
        _list.first_item.selected = True
    _list.go()
    gui.signal_emit('mainmenu,show')
    input_events.listener_add('mainmenu', input_event_cb)
    gui.clock_update()


def hide():
    _list.focus_allow = False
    _list.callback_clicked_double_del(_cb_item_activated)
    _list.callback_selected_del(_cb_item_selected)
    input_events.listener_del('mainmenu')
    gui.signal_emit('mainmenu,hide')


def item_add(name, weight, label, icon, callback, subitems=None):
    # print('ADD ' + name + ' W ' + str(weight) + ' before ' + str(before.text if before else None))
    if subitems is None:
        subitems = []

    img = gui.load_image(icon)

    sublist = gui.EmcList(_list, style='mainmenu_sublist', name='MainMenuSubList',
                          focus_allow=False, focus_on_select=False)
    for _label, _icon, _url in subitems:
        si = sublist.item_append(_label, gui.load_icon(_icon) if _icon else None)
        si.data['url'] = _url

    before = None
    for it in _list.items:
        if weight <= it.data['weight']:
            before = it
            break

    if before:
        item = _list.item_insert_before(before, label, img, sublist)
    else:
        item = _list.item_append(label, img, sublist)

    item.data['sublist'] = sublist
    item.data['weight'] = weight
    item.data['name'] = name
    item.data['callback'] = callback


def _cb_item_selected(li, item):
    item.bring_in()
    sublist = item.data['sublist']
    if sublist and sublist.selected_item:
        sublist.selected_item.selected = False


def _cb_item_activated(li, item):
    callback = item.data['callback']
    subitem = item.data['sublist'].selected_item
    if subitem:
        callback(subitem.data['url'])
    else:
        callback()


def item_activate(name):
    for it in _list.items:
        if it.data.get('name') == name:
            _cb_item_activated(_list, it)
            return
    print('WARNING: cannot find the requested activity: "%s"' % name)


def item_del(name):
    for item in _list.items:
        if item.data['name'] == name:
            item.delete()


def input_event_cb(event):
    if not _list.focus:
        return input_events.EVENT_CONTINUE

    item = _list.selected_item
    if not item:
        item = _list.first_item
        item.selected = True

    elif event == 'DOWN':
        sublist = item.data['sublist']
        subitem = sublist.selected_item
        if subitem and subitem.next:
            subitem.next.selected = True
        elif not subitem and sublist.first_item:
            sublist.first_item.selected = True
        else:
            return input_events.EVENT_CONTINUE
        return input_events.EVENT_BLOCK

    elif event == 'UP':
        sublist = item.data['sublist']
        subitem = sublist.selected_item
        if subitem and subitem.prev:
            subitem.prev.selected = True
        elif subitem:
            subitem.selected = False
        else:
            return input_events.EVENT_CONTINUE
        return input_events.EVENT_BLOCK

    elif event == 'OK':
        _cb_item_activated(_list, item)
        return input_events.EVENT_BLOCK

    elif event == 'EXIT':
        gui.ask_to_exit()
        return input_events.EVENT_BLOCK

    return input_events.EVENT_CONTINUE
