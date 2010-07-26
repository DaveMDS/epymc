#!/usr/bin/env python

import evas
import elementary

import ini
import downloader

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

    ##TESTING
    #~ im = EmcRemoteImage(win)
    #~ im.url_set("http://hwcdn.themoviedb.org/posters/900/4bc95e22017a3c57fe02a900/wanted-thumb.jpg")
    #~ im.resize(300,300)
    #~ im.move(100,200)
    #~ im.show()
    ##

def part_get(name):
    global _layout
    return _layout.edje_get().part_external_object_get(name)

def signal_emit(sig, src = 'emc'):
    global _layout
    _layout.edje_get().signal_emit(sig, src)

def text_set(part, text):
    global _layout
    _layout.edje_get().part_text_set(part, text)

def swallow_set(part, obj):
    global _layout
    _layout.edje_get().part_swallow(part, obj)
    
def shutdown():
    elementary.exit()

################################################################################
import os

class EmcRemoteImage(elementary.Image):
    """ TODO doc this """

    def __init__(self, parent):
        elementary.Image.__init__(self, parent)
        self._parent = parent
        self._pb = elementary.Progressbar(parent)
        self._pb.style_set("wheel")

    def show(self):
        (x, y, w, h) = self.geometry_get()
        print 'SHOW %d %d %d %d' % (x, y, w, h)
        elementary.Progressbar.show(self)
        self._pb.resize(w, h)
        self._pb.move(x, y)

    def hide(self):
        elementary.Progressbar.hide(self)
        self._pb.hide()

    def url_set(self, url, dest = None):
        # if dest exists then set the image and return
        if dest and os.path.exists(dest):
            self.file_set(dest)
            return

        downloader.download_url_async(url, dest=(dest if dest else "tmp"),
                                      complete_cb=self._cb_download_complete,
                                      progress_cb=self._cb_download_progress)
        self.file_set('')
        self.start_spin()

    def start_spin(self):
        self.show()
        self._pb.show()
        self._pb.pulse(True)

    def stop_spin(self):
        self._pb.hide()
        self._pb.pulse(False)


    def _cb_download_complete(self, url, dest, header):
        self.stop_spin()
        self.file_set(dest)

    def _cb_download_progress(self):
        pass

        
   #TODO on image_set abort the download ? 
