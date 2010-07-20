#!/usr/bin/env python

import gui
import mainmenu
import config_gui


_items = {}  # key: name  value: elm_list_item
_items_weight = {}  # key: elm_list_item  value: weight(int)



def cb_exit(list, list_item):
    gui.shutdown()

def cb_config(list, list_item):
    config_gui.show()


def init():
    mainmenu.item_add("config", 100, "Configurations", None, cb_config)
    mainmenu.item_add("exit", 200, "Exit", None, cb_exit)


def show():
    list = gui.part_get("mainmenu_list")
    list.go()
    gui.signal_emit("mainmenu,show")

def hide():
    gui.signal_emit("mainmenu,hide")

def item_add(name, weight, label, icon = None, callback = None):
    list = gui.part_get("mainmenu_list")

    before = None
    for it in list.items_get():
        if weight <= _items_weight[it]:
            before = it
            break

    #~ print 'ADD ' + name + ' W ' + str(weight) + ' before ' + str(before)
    
    if before:
        item = list.item_insert_before(before, label, icon, None, callback)
    else:
        item = list.item_append(label, icon, None, callback)

    _items[name] = item
    _items_weight[item] = weight

def item_del(name):
    item = _items[name]
    del _items_weight[item]
    item.delete()
    del _items[name]

   

