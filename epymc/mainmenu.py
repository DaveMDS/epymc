#!/usr/bin/env python
#
# Copyright (C) 2010-2012 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of EpyMC.
#
# EpyMC is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# EpyMC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with EpyMC. If not, see <http://www.gnu.org/licenses/>.

import gui
import mainmenu
import config_gui
import input_events


_items = {}  # key: name  value: elm_list_item
_items_weight = {}  # key: elm_list_item  value: weight(int)



def cb_exit():
   gui.ask_to_exit()


def init():
   li = gui.part_get("mainmenu/list")
   li.style_set("mainmenu");
   li.focus_allow_set(False)
   mainmenu.item_add("exit", 200, "Exit", None, cb_exit)

def show():
   list = gui.part_get("mainmenu/list")
   list.callback_clicked_double_add(_cb_item_selected)
   if not list.selected_item_get():
      list.items_get()[0].selected_set(1)
   list.go()
   gui.signal_emit("mainmenu,show")
   input_events.listener_add('mainmenu', input_event_cb)

def hide():
   list = gui.part_get("mainmenu/list")
   list.callback_clicked_double_del(_cb_item_selected)
   input_events.listener_del('mainmenu')
   gui.signal_emit("mainmenu,hide")

def item_add(name, weight, label, icon = None, callback = None):
   list = gui.part_get("mainmenu/list")

   before = None
   for it in list.items_get():
      if weight <= _items_weight[it]:
         before = it
         break

   #~ print 'ADD ' + name + ' W ' + str(weight) + ' before ' + str(before)
   if before:
      item = list.item_insert_before(before, label, icon, None, None, callback)
   else:
      item = list.item_append(label, icon, None, None, callback)

   _items[name] = item
   _items_weight[item] = weight

def _cb_item_selected(list, item):
   cb = item.data_get()[0][0]
   if cb: cb()

def item_del(name):
   item = _items[name]
   del _items_weight[item]
   item.delete()
   del _items[name]

def input_event_cb(event):
   list = gui.part_get("mainmenu/list")
   item = list.selected_item_get()
   if not item:
      item = list.items_get()[0]
      item.selected_set(1)

   if event == 'DOWN':
      next = item.next_get()
      if next:
         next.selected_set(1)
      else:
         list.items_get()[0].selected_set(1)
      return input_events.EVENT_BLOCK

   elif event == 'UP':
      prev = item.prev_get()
      if prev:
         prev.selected_set(1)
      else:
         list.items_get()[-1].selected_set(1)
      return input_events.EVENT_BLOCK

   elif event == 'OK':
      _cb_item_selected(list, item)
      return input_events.EVENT_BLOCK

   elif event == 'EXIT':
      gui.ask_to_exit()
      return input_events.EVENT_BLOCK


   return input_events.EVENT_CONTINUE
