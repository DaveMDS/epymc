#!/usr/bin/env python

import gui
import mainmenu
import config_gui
import input


_items = {}  # key: name  value: elm_list_item
_items_weight = {}  # key: elm_list_item  value: weight(int)



def cb_exit():
    gui.ask_to_exit()


def init():
    mainmenu.item_add("exit", 200, "Exit", None, cb_exit)

    list = gui.part_get("mainmenu_list")


def show():
    list = gui.part_get("mainmenu_list")
    list.callback_clicked_add(_cb_item_selected)
    list.go()
    gui.signal_emit("mainmenu,show")
    input.listener_add('mainmenu', input_event_cb)

def hide():
    list = gui.part_get("mainmenu_list")
    list.callback_clicked_del(_cb_item_selected)
    input.listener_del('mainmenu')
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
    list = gui.part_get("mainmenu_list")
    item = list.selected_item_get()
    if not item:
        item = list.items_get()[0]
        item.selected_set(1)
    
    if event == "down":
        next = item.next_get()
        if next:
            next.selected_set(1)
            return input.EVENT_BLOCK

    elif event == "up":
        prev = item.prev_get()
        if prev:
            prev.selected_set(1)
            return input.EVENT_BLOCK

    elif event == "ok":
        _cb_item_selected(list, item)
        return input.EVENT_BLOCK

    elif event == "back":
        gui.ask_to_exit()
        return input.EVENT_BLOCK


    return input.EVENT_CONTINUE
