#!/usr/bin/env python

import evas
import elementary #REMOVEME


import gui
import mainmenu

# root list, list items and items weight
_root = None # elm_list
_root_items = {}  # key: name  value: elm_list_item
_root_items_weight = {}  # key: elm_list_item  value: weight(int)


def cb_root_back(list, list_item):
   hide()

def cb_mainmenu():
   show()

def init():
   global _root

   mainmenu.item_add("config", 100, "Config", None, cb_mainmenu)

   pager = gui.part_get("config_pager")
   pager.style_set("slide_invisible")

   _root = elementary.List(pager)
   pager.content_push(_root)

   root_item_add("modules", 20, "Modules", None, None)
   root_item_add("fs", 30, "Fullscreen", None, None)
   root_item_add("back", 999, "Back", None, cb_root_back)


def root_item_add(name, weight, label, icon = None, callback = None):
   global _root

   before = None
   for it in _root.items_get():
      if weight <= _root_items_weight[it]:
         before = it
         break

   if before:
      item = _root.item_insert_before(before, label, icon, None, callback)
   else:
      item = _root.item_append(label, icon, None, callback)

   _root_items[name] = item
   _root_items_weight[item] = weight
   _root.go()

def root_item_del(name):
   item = _root_items[name]
   del _root_items_weight[item]
   item.delete()
   del _root_items[name]

def show():
   gui.signal_emit("config,show")


def hide():
   gui.signal_emit("config,hide")

