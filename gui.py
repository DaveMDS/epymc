#!/usr/bin/env python

import evas
import elementary

import ini

_win = None
_layout = None

def init_window():
    global _win
    global _layout
    
    # window
    win = elementary.Window("emc_win", elementary.ELM_WIN_BASIC)
    win.title_set("Enlightenment Media Center")
    win.autodel_set(True) #TODO exit app on del !!
    _win = win
    if ini.has_option('general', 'fullscreen'):
        if ini.get_bool('general', 'fullscreen') == True:
            win.fullscreen_set(1)
    else:
        ini.set('general', 'fullscreen', False)

    # main layout
    ly = elementary.Layout(win)
    ly.file_set("default.edj", "main")
    ly.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
    win.resize_object_add(ly)
    ly.show()
    _layout = ly;

    win.show()

def part_get(name):
    global _layout
    return _layout.edje_get().part_external_object_get(name)

def signal_emit(sig, src = 'emc'):
    global _layout
    _layout.edje_get().signal_emit(sig, src)

def text_set(part, text):
    global _layout
    _layout.edje_get().part_text_set(part, text)
    
def shutdown():
    elementary.exit()

