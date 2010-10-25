#!/usr/bin/env python

import os

import evas
import elementary

import utils
import ini
import downloader
import mediaplayer
import gui
import input


win = None
layout = None
theme_file = None


def init():
   global win
   global layout
   global theme_file

   # set default theme in config file
   if not ini.has_option('general', 'theme'):
      ini.set('general', 'theme', 'default')
   name = ini.get('general', 'theme');

   # search the theme file, or use the default one
   theme_file = utils.get_resource_file('themes', name + '.edj', 'default.edj')
   if not theme_file:
      print "ERROR: can't find a working theme file, exiting..."
      return False
   
   #~ elementary.theme_overlay_add(theme_file)
   elementary.theme_extension_add(theme_file)

   # window
   win = elementary.Window("epymc", elementary.ELM_WIN_BASIC)
   win.title_set("Enlightenment Media Center")
   win.callback_destroy_add(_cb_win_del)
   if ini.has_option('general', 'fullscreen'):
      if ini.get_bool('general', 'fullscreen') == True:
         win.fullscreen_set(1)
   else:
      ini.set('general', 'fullscreen', False)

   # main layout (main theme)
   layout = elementary.Layout(win)
   layout.file_set(theme_file, "epymc_main_layout")
   layout.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
   win.resize_object_add(layout)
   layout.show()

   win.show()

   part_get('volume/slider').callback_changed_add(_cb_volume_slider_changed)


   # fill view buttons box in topbar
   bt = elementary.Button(win)
   bt.icon_set(load_icon('icon/list'))
   bt.callback_clicked_add(_cb_btn_change_view, "VIEW_LIST")
   layout.edje_get().part_box_append('topbar/box', bt)
   bt.show()

   bt = elementary.Button(win)
   bt.icon_set(load_icon('icon/grid'))
   bt.callback_clicked_add(_cb_btn_change_view, "VIEW_GRID")
   layout.edje_get().part_box_append('topbar/box', bt)
   bt.show()

   ##TESTING
   #~ im = EmcRemoteImage(win)
   #~ im.url_set("http://hwcdn.themoviedb.org/posters/900/4bc95e22017a3c57fe02a900/wanted-thumb.jpg")
   #~ im.resize(300,300)
   #~ im.move(100,200)
   #~ im.show()
   ##
   input.listener_add('gui', input_event_cb)
   
   return True

def shoutdown():
   input.listener_del('gui')
   pass

def input_event_cb(event):
   if event == "TOGGLE_FULLSCREEN":
      #~ win.fullscreen_set(not win.fullscreen_get())
      win.fullscreen = not win.fullscreen
      return input.EVENT_BLOCK

   input.EVENT_CONTINUE

def _cb_win_del(win):
   ask_to_exit()

# TODO move this callback somewhere...maybe in mediaplayer?
def _cb_volume_slider_changed(slider):
   mediaplayer.volume_set(slider.value)

def _cb_btn_change_view(btn, view):
   input.event_emit(view)

def load_icon(icon):
   """
   icon can be a full path (if start with a '/' or
   can be a theme icon (ex: icon/folder).
   see icons.edc for all the existing icon
   """
   #TODO if icon in an EvasObject just return it
   ic = elementary.Icon(gui.win)
   if icon[0] == '/':
      ic.file_set(icon)
   else:
      ic.file_set(theme_file, icon)
   ic.size_hint_aspect_set(evas.EVAS_ASPECT_CONTROL_VERTICAL, 1, 1)
   return ic
    
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

def toggle_fullscreen():
   pass


def part_get(name):
   global layout
   return layout.edje_get().part_external_object_get(name)

def signal_emit(sig, src = 'emc'):
   global layout
   layout.edje_get().signal_emit(sig, src)

def text_set(part, text):
   global layout
   layout.edje_get().part_text_set(part, text)

def swallow_set(part, obj):
   global layout
   layout.edje_get().part_swallow(part, obj)


################################################################################
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
      #~ print 'SHOW %d %d %d %d' % (x, y, w, h)
      elementary.Image.show(self)

   def hide(self):
      self._pb.hide()
      elementary.Image.hide(self)

   def url_set(self, url, dest = None):
      if dest and os.path.exists(dest):
         # if dest exists then just set the image
         self.file_set(dest)
      else:
         # else start spin & download
         self.file_set('')
         self.start_spin()
         downloader.download_url_async(url, dest = (dest if dest else "tmp"),
                                    complete_cb = self._cb_download_complete,
                                    progress_cb = self._cb_download_progress)

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
class EmcDialog(elementary.InnerWindow):
   """ TODO doc this
   style can be 'minimal' (default), 'minimal_vertical' or 'default'
   you can also apply special style that perform specific task:
      'info', 'error', 'warning', 'yesno'
   note that special style don't need activate() to be called

   TODO does we need activate at all?
   """

   special_styles = ['info', 'error', 'warning', 'yesno']
   dialogs_counter = 0
   
   def __init__(self, title = None, text = None, content = None,
                spinner = False, style = 'minimal', done_cb = None):
      elementary.InnerWindow.__init__(self, gui.win)
      EmcDialog.dialogs_counter += 1

      if style in EmcDialog.special_styles:
         self.style_set('minimal')
      else:
         self.style_set(style)

      self._name = 'Dialog-' + str(EmcDialog.dialogs_counter)
      self._buttons = list()
      self._current_button_num = 0
      self._content = content
      self._done_cb = done_cb

      # vbox
      self._vbox = elementary.Box(gui.win)
      self._vbox.horizontal_set(False)
      self._vbox.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      self._vbox.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      self._vbox.show()
      elementary.InnerWindow.content_set(self, self._vbox)

      # hbox (buttons)
      self._hbox = elementary.Box(gui.win)
      self._hbox.horizontal_set(True)
      self._hbox.show()

      self._vbox.pack_end(self._hbox)
      
      if text:
         self._anchorblock = elementary.AnchorBlock(gui.win)
         self._anchorblock.text_set(text)
         self._vbox.pack_start(self._anchorblock)
         self._anchorblock.show()
      elif content:
         self._vbox.pack_start(content)
         content.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         content.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)

      if spinner:
         self._spinner = elementary.Progressbar(gui.win)
         self._spinner.style_set('wheel')
         self._spinner.pulse(True)
         self._spinner.show()
         self._vbox.pack_start(self._spinner)

      if title:
         self._title = elementary.Label(gui.win)
         self._title.label_set(title)
         self._vbox.pack_start(self._title)
         self._title.show()

      if style in ['info', 'error', 'warning']:
         self.button_add('Ok', (lambda btn: self.delete()))
         self.activate()

      if style in ['yesno']:
         self.button_add('Yes', (lambda btn: self._done_cb(self)))
         self.button_add('No', (lambda btn: self.delete()))
         self.activate()

   def activate(self):
      input.listener_add(self._name, self._input_event_cb)
      elementary.InnerWindow.activate(self)

   def delete(self):
      input.listener_del(self._name)
      elementary.InnerWindow.delete(self)

   def content_get(self):
      return self._content

   def button_add(self, label, selected_cb = None, cb_data = None, icon = None):
      b = elementary.Button(self)
      self._buttons.append(b)
      b.label_set(label)
      b.disabled_set(0 if (len(self._buttons) == 1) else 1)
      b.data['cb'] = selected_cb
      b.data['cb_data'] = cb_data
      b.callback_clicked_add(self._cb_buttons)
      b.on_mouse_in_add(self._cb_button_mouse_in)
      if icon:
         b.icon_set(load_icon(icon))

      self._hbox.pack_start(b)
      b.show()

   def text_set(self, text):
      self._anchorblock.text_set(text)

   def spinner_start(self):
      self._spinner.pulse(True)

   def spinner_stop(self):
      self._spinner.pulse(False)

   def _cb_buttons(self, button):
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
         self._cb_buttons(self._buttons[self._current_button_num])

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
