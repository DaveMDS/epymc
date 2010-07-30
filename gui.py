#!/usr/bin/env python

import evas
import elementary

import ini
import downloader
import mediaplayer

_win = None
_layout = None

def _cb_win_del(win):
    ask_to_exit()

# TODO move this callback somewhere...maybe in mediaplayer?
def _cb_volume_slider_changed(slider):
    mediaplayer.volume_set(slider.value)

def init_window():
    global _win
    global _layout
    
    # window
    win = elementary.Window("emc_win", elementary.ELM_WIN_BASIC)
    win.title_set("Enlightenment Media Center")
    #~ win.autodel_set(True) #TODO exit app on del !!
    win.callback_destroy_add(_cb_win_del)
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

    part_get('volume/slider').callback_changed_add(_cb_volume_slider_changed)
    ##TESTING
    #~ im = EmcRemoteImage(win)
    #~ im.url_set("http://hwcdn.themoviedb.org/posters/900/4bc95e22017a3c57fe02a900/wanted-thumb.jpg")
    #~ im.resize(300,300)
    #~ im.move(100,200)
    #~ im.show()
    ##


def ask_to_exit():
    d = EmcDialog(title = 'Exit MediaCenter ?')
    d.button_add('Yes', _cb_exit_yes)
    d.button_add('No', _cb_exit_no, d)
    d.activate()
    
def _cb_exit_yes(button):
    elementary.exit()

def _cb_exit_no(button, dialog):
    dialog.delete()
    del dialog

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


################################################################################
import os

class EmcRemoteImage(elementary.Image):
    """ TODO doc this """

    def __init__(self, parent):
        elementary.Image.__init__(self, parent)
        self._parent = parent
        self._pb = elementary.Progressbar(parent)
        self._pb.style_set("wheel")
        self.on_move_add(self._cb_move_resize)
        self.on_resize_add(self._cb_move_resize)

    def show(self):
        (x, y, w, h) = self.geometry_get()
        print 'SHOW %d %d %d %d' % (x, y, w, h)
        elementary.Image.show(self)
        self._pb.show()

    def hide(self):
        self._pb.hide()
        elementary.Image.hide(self)

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

    def _cb_move_resize(self, obj):
        (x, y, w, h) = self.geometry_get()
        #~ print 'MOVE %d %d %d %d' % (x, y, w, h)
        self._pb.resize(w, h)
        self._pb.move(x, y)
        self._pb.raise_()

    def _cb_download_complete(self, url, dest, header):
        self.stop_spin()
        self.file_set(dest)
        self.size_hint_min_set(100, 100) #TODO FIXME (needed by tmdb search results list)

    def _cb_download_progress(self):
        pass

        
   #TODO on image_set abort the download ? 

################################################################################
import gui
import input

_dialog_counter = 0

class EmcDialog(elementary.InnerWindow):
    """ TODO doc this
        style can be 'minimal' (default), 'minimal_vertical' or 'default'
    """

    def __init__(self, title = None, text = None, content = None,
                       spinner = False, style = 'minimal'):
        global _dialog_counter
        
        elementary.InnerWindow.__init__(self, gui._win)
        self.style_set(style)

        _dialog_counter += 1
        self._name = 'Dialog-' + str(_dialog_counter)
        self._buttons = list()
        self._current_button_num = 0
        self._content = content
        self._vbox = elementary.Box(gui._win)
        self._vbox.horizontal_set(False)
        self._vbox.show()
        
        self._hbox = elementary.Box(gui._win)
        self._hbox.horizontal_set(True)
        self._hbox.show()

        self._vbox.pack_end(self._hbox)
        elementary.InnerWindow.content_set(self, self._vbox)

        if text:
            self._anchorblock = elementary.AnchorBlock(gui._win)
            self._anchorblock.text_set(text)
            self._vbox.pack_start(self._anchorblock)
            self._anchorblock.show()
        elif content:
            self._vbox.pack_start(content)

        if spinner:
            self._spinner = elementary.Progressbar(gui._win)
            self._spinner.style_set('wheel')
            self._spinner.pulse(True)
            self._spinner.show()
            self._vbox.pack_start(self._spinner)

        if title:
            self._title = elementary.Label(gui._win)
            self._title.label_set(title)
            self._vbox.pack_start(self._title)
            self._title.show()

    def activate(self):
        input.listener_add(self._name, self._input_event_cb)
        elementary.InnerWindow.activate(self)

    def delete(self):
        input.listener_del(self._name)
        elementary.InnerWindow.delete(self)

    def content_get(self):
        return self._content

    def button_add(self, label, selected_cb = None, cb_data = None):
        b = elementary.Button(self)
        self._buttons.append(b)
        b.label_set(label)
        b.disabled_set(0 if (len(self._buttons) == 1) else 1)
        b.data['cb'] = selected_cb
        b.data['cb_data'] = cb_data
        b.callback_clicked_add(self._buttons_cb)
        b.on_mouse_in_add(self._cb_button_mouse_in)

        self._hbox.pack_start(b)
        b.show()
    
    def _buttons_cb(self, button):
        selected_cb = button.data['cb']
        cb_data = button.data['cb_data']
        
        if selected_cb and cb_data:
            selected_cb(button, cb_data)
        elif selected_cb:
            selected_cb(button)

    def _cb_button_mouse_in(self, button, event):
        if button != self._buttons[self._current_button_num]:
            self._buttons[self._current_button_num].disabled_set(1)
            self._current_button_num = self._buttons.index(button)
            self._buttons[self._current_button_num].disabled_set(0)
    
    def _input_event_cb(self, event):

        if event == 'BACK':
            self.delete()
            return input.EVENT_BLOCK

        # if content is elm List then automanage the events
        if self._content and type(self._content) is elementary.List:
            list = self._content
            item = list.selected_item_get()
            if not item:
                item = list.items_get()[0]
                
            if event == 'DOWN':
                next = item.next_get()
                if next:
                    next.selected_set(1)
                    next.show()
                    return input.EVENT_BLOCK
            
            if event == 'UP':
                prev = item.prev_get()
                if prev:
                    prev.selected_set(1)
                    prev.show()
                    return input.EVENT_BLOCK

        if event == 'OK':
            self._buttons_cb(self._buttons[self._current_button_num])

        elif event == 'LEFT':
            if self._current_button_num < len(self._buttons) - 1:
                self._buttons[self._current_button_num].disabled_set(1)
                self._current_button_num += 1
                self._buttons[self._current_button_num].disabled_set(0)

        elif event == 'RIGHT':
            if self._current_button_num > 0:
                self._buttons[self._current_button_num].disabled_set(1)
                self._current_button_num -= 1
                self._buttons[self._current_button_num].disabled_set(0)

        return input.EVENT_BLOCK
