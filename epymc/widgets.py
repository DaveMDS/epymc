#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
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

import os
import evas, ecore, edje, elementary
import utils, gui, input_events


################################################################################
class EmcButton(elementary.Button):
   """ TODO documentation """

   def __init__(self, label = None, icon = None):
      elementary.Button.__init__(self, gui.layout)
      self.style_set('emc')
      self.focus_allow_set(False)
      if label: self.text_set(label)
      if icon: self.content_set(gui.load_icon(icon))
      self.show()

################################################################################
class EmcMenu(elementary.Menu):
   """ TODO doc this """

   def __init__(self, relto = None):
      elementary.Menu.__init__(self, gui.layout)
      if relto:
         # TODO better pos calc
         x, y, w, h = relto.geometry
         self.move(x, y + h)

      input_events.listener_add("EmcMenu", self._input_event_cb)
      self.callback_clicked_add(self._dismiss_cb)
      self.show()

   def item_add(self, parent = None, label = None, icon = None, callback = None, *args, **kwargs):
      item = elementary.Menu.item_add(self, parent, label, icon, self._item_selected_cb, callback, *args, **kwargs)
      if self.selected_item_get() is None:
         item.selected_set(True)

   def close(self):
      input_events.listener_del("EmcMenu")
      elementary.Menu.close(self)

   def _item_selected_cb(self, menu, item, cb, *args, **kwargs):
      input_events.listener_del("EmcMenu")
      if callable(cb):
         cb(menu, item, *args, **kwargs)
      
   def _dismiss_cb(self, menu):
      input_events.listener_del("EmcMenu")

   def _input_event_cb(self, event):
      if event == 'UP':
         item = self.selected_item_get()
         if not item or not item.prev:
            return input_events.EVENT_BLOCK
         while item.prev and item.prev.is_separator():
            item = item.prev
         item.prev.selected_set(True)
         return input_events.EVENT_BLOCK

      elif event == 'DOWN':
         item = self.selected_item_get()
         if not item or not item.next:
            return input_events.EVENT_BLOCK
         while item.next and item.next.is_separator():
            item = item.next
         item.next.selected_set(True)
         return input_events.EVENT_BLOCK

      elif event == 'OK':
         item = self.selected_item_get()
         args, kwargs = self.selected_item_get().data_get()
         cb = args[0]
         if cb and callable(cb):
            cb(self, item, *args[1:], **kwargs)
         # self.close() # not sure I want this :/
         return input_events.EVENT_BLOCK

      elif event == 'BACK' or event == 'EXIT':
         self.close()
         return input_events.EVENT_BLOCK

      elif event in ('LEFT', 'RIGHT'):
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

################################################################################
class EmcRemoteImage(elementary.Image):
   """ TODO documentation """
   """ TODO on image_set abort the download ? """

   def __init__(self, url = None, dest = None):
      elementary.Image.__init__(self, gui.layout)
      self.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      self.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      self.on_move_add(self._cb_move_resize)
      self.on_resize_add(self._cb_move_resize)
      self._spinner = elementary.Progressbar(gui.layout)
      self._spinner.style_set('wheel')
      if url: self.url_set(url, dest)

   def show(self):
      elementary.Image.show(self)

   def hide(self):
      self._spinner.hide()
      elementary.Image.hide(self)

   def url_set(self, url, dest = None):
      if dest and os.path.exists(dest):
         self.file_set(dest)
      else:
         self.file_set('')
         self.start_spin()
         utils.download_url_async(url, dest if dest else 'tmp',
                                  complete_cb = self._cb_download_complete)

   def start_spin(self):
      self.show()
      self._spinner.show()
      self._spinner.pulse(True)

   def stop_spin(self):
      self._spinner.hide()
      self._spinner.pulse(False)

   def _cb_move_resize(self, obj):
      (x, y, w, h) = self.geometry_get()
      self._spinner.resize(w, h)
      self._spinner.move(x, y)
      if self._spinner.clip != self.clip:
         self._spinner.clip = self.clip

   def _cb_download_complete(self, dest, status):
      self.stop_spin()
      if status == 200: # Successfull HTTP code
         self.file_set(dest)
      else:
         # TODO show a dummy image
         self.file_set('')

################################################################################
class EmcDialog(edje.Edje):
   """ TODO doc this
   style can be 'panel' or 'minimal'

   you can also apply special style that perform specific task:
      'info', 'error', 'warning', 'yesno', 'cancel', 'progress'
   """

   special_styles = ['info', 'error', 'warning', 'yesno', 'cancel', 'progress']
   dialogs_counter = 0

   fman = None
   
   def __init__(self, title = None, text = None, content = None,
                spinner = False, style = 'panel',
                done_cb = None, canc_cb = None, user_data = None):
      # load the right edje object
      if style in EmcDialog.special_styles or style == 'minimal':
         group = 'emc/dialog/minimal'
      else:
         group = 'emc/dialog/panel'
      edje.Edje.__init__(self, gui.layout.evas, file = gui.theme_file, group = group)
      self.signal_callback_add('emc,dialog,close', '', self._close_pressed)
      self.signal_callback_add('emc,dialog,hide,done', '',
                               (lambda a,S,d: self._delete_real()))
      self.signal_callback_add('emc,dialog,show,done', '',
                               (lambda a,s,D: None))

      # put the dialog in the dialogs box of the main edje obj,
      # this way we only manage one edje and don't have stacking problems.
      # otherwise dialogs will stole the mouse events.
      self.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      self.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      gui.box_append('dialogs.box.stack', self)

      EmcDialog.dialogs_counter += 1
      self._name = 'Dialog-' + str(EmcDialog.dialogs_counter)
      self._content = content
      self._done_cb = done_cb
      self._canc_cb = canc_cb
      self._user_data = user_data
      self._buttons = []
      self.fman = EmcFocusManager2()

      # vbox
      self._vbox = elementary.Box(gui.win)
      self._vbox.horizontal_set(False)
      self._vbox.size_hint_align_set(evas.EVAS_HINT_FILL, 0.0)
      self._vbox.size_hint_weight_set(evas.EVAS_HINT_EXPAND, 0.0)
      self._vbox.show()
      self.part_swallow('emc.swallow.content', self._vbox)

      if title is not None:
         self.part_text_set('emc.text.title', title)
         self.signal_emit('emc,dialog,title,show', 'emc')
         # TODO hide the title in None
      
      if text is not None:
         self._textentry = elementary.Entry(gui.win)
         self._textentry.style_set('dialog')
         self._textentry.editable_set(False)
         self._textentry.context_menu_disabled_set(True)
         self._textentry.entry_set(text)
         self._textentry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         self._textentry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
         #~ self._textentry.size_hint_align_set(0.5, 0.5)
         self._vbox.pack_end(self._textentry)
         self._textentry.show()
      elif content is not None:
         frame = elementary.Frame(gui.win)
         frame.style_set('pad_medium')
         frame.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
         frame.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
         frame.content_set(content)
         frame.show()
         self._vbox.pack_end(frame)

      if spinner:
         self._spinner = elementary.Progressbar(gui.win)
         self._spinner.style_set('wheel')
         self._spinner.pulse(True)
         self._spinner.show()
         self._vbox.pack_end(self._spinner)

      if style in EmcDialog.special_styles:
         self.signal_emit('emc,dialog,%s,set' % (style), 'emc')
         if title is None:
            self.part_text_set('emc.text.title', style)
            self.signal_emit('emc,dialog,title,show', 'emc')

      if style in ('info', 'error', 'warning'):
         self.button_add('Ok', (lambda btn: self.delete()))

      if style in ('yesno'):
         if self._canc_cb:
            self.button_add('No', (lambda btn: self._canc_cb(self)))
         else:
            self.button_add('No', (lambda btn: self.delete()))

         if self._done_cb:
            self.button_add('Yes', (lambda btn: self._done_cb(self)))
         else:
            self.button_add('Yes', (lambda btn: self.delete()))

      # Do we want the cancel button? we have the red-round-close...
      # if style in ('cancel'):
         # if canc_cb:
            # self.button_add('Cancel', (lambda btn: self._canc_cb(self)))
         # else:
            # self.button_add('Cancel', (lambda btn: self.delete()))

      input_events.listener_add(self._name, self._input_event_cb)
      
      self.show()
      self.signal_emit('emc,dialog,show', 'emc')

   def activate(self):
      print 'DEPRECATED EmcDialog.activate()'

   def delete(self):
      input_events.listener_del(self._name)
      self.fman.delete()
      self.signal_emit('emc,dialog,hide', 'emc')

   def _delete_real(self):
      if self.part_swallow_get('emc.swallow.content'):
         self.part_swallow_get('emc.swallow.content').delete()
      for b in self._buttons:
         b.delete()
      gui.box_remove('dialogs.box.stack', self)
      edje.Edje.delete(self)
      del self

   def _close_pressed(self, a, s, d):
      if self._canc_cb:
         self._canc_cb(self)
      else:
         self.delete()

   def content_get(self):
      return self._content

   def data_get(self):
      return self._user_data

   def button_add(self, label, selected_cb = None, cb_data = None, icon = None):
      if not self._buttons:
         self.signal_emit('emc,dialog,buttons,show', 'emc')

      b = EmcButton(label, icon)
      b.data['cb'] = selected_cb
      b.data['cb_data'] = cb_data
      b.callback_clicked_add(self._cb_buttons)
      self.fman.obj_add(b)
      self.part_box_prepend('emc.box.buttons', b)
      self._buttons.append(b)
      return b

   def buttons_clear(self):
      self.fman.delete()
      self.fman = EmcFocusManager()
      for b in self._buttons:
         b.delete()
      del self._buttons
      self._buttons = []

   def title_set(self, text):
      if text is not None:
         self.part_text_set('emc.text.title', text)
         self.signal_emit('emc,dialog,title,show', 'emc')
      else:
         self.signal_emit('emc,dialog,title,hide', 'emc')

   def title_get(self):
      return self.part_text_get('emc.text.title')

   def text_set(self, text):
      self._textentry.entry_set(text)

   def text_get(self):
      return self._textentry.entry_get()

   def text_append(self, text):
      self._textentry.entry_set(self._textentry.entry_get() + text)

   def spinner_start(self):
      self._spinner.show()
      self._spinner.pulse(True)

   def spinner_stop(self):
      self._spinner.pulse(False)
      self._spinner.hide()

   def progress_set(self, val):
      self.part_external_object_get('emc.dialog.progress').value_set(val)

   def _cb_buttons(self, button):
      selected_cb = button.data['cb']
      cb_data = button.data['cb_data']

      if selected_cb and cb_data:
         selected_cb(button, cb_data)
      elif selected_cb:
         selected_cb(button)

   def _input_event_cb(self, event):

      if event in ['BACK', 'EXIT']:
         if self._canc_cb:
            self._canc_cb(self)
         else:
            self.delete()
         return input_events.EVENT_BLOCK

      # if content is elm List or Genlist then automanage the events
      if self._content and type(self._content) in (elementary.List, elementary.Genlist):
         list = self._content
         item = list.selected_item_get()
         if not item:
            item = list.items_get()[0]

         horiz = False
         if type(self._content) is elementary.List:
            horiz = list.horizontal

         if (horiz and event == 'RIGHT') or \
            (not horiz and event == 'DOWN'):
            next = item.next_get()
            if next:
               next.selected_set(1)
               next.show()
               return input_events.EVENT_BLOCK

         if (horiz and event == 'LEFT') or \
            (not horiz and event == 'UP'):
            prev = item.prev_get()
            if prev:
               prev.selected_set(1)
               prev.show()
               return input_events.EVENT_BLOCK

      if self._buttons:
         if event == 'LEFT':
            self.fman.focus_move('l')
         if event == 'RIGHT':
            self.fman.focus_move('r')
   
      if event == 'OK':
         if self._buttons:
            self._cb_buttons(self.fman.focused_get())
         elif self._done_cb:
            self._done_cb(self)

      if event in ('LEFT', 'RIGHT', 'UP', 'DOWN', 'OK'):
         return input_events.EVENT_BLOCK
      else:
         return input_events.EVENT_CONTINUE

################################################################################
class EmcNotify(edje.Edje):
   """ TODO doc this"""

   def __init__(self, text, icon = 'icon/star', hidein = 5.0):
      group = 'emc/notify/default'
      edje.Edje.__init__(self, gui.layout.evas, file = gui.theme_file, group = group)
      self.part_text_set('emc.text.caption', text)
      self._icon = gui.load_image(icon)
      self.part_swallow('emc.swallow.icon', self._icon)
      gui.box_append('notify.box.stack', self)
      if hidein > 0.0:
         self.timer = ecore.Timer(hidein, self.hide_timer_cb)
      else:
         self.timer = None
      self.show()

   def hide_timer_cb(self):
      gui.box_remove('notify.box.stack', self)
      self._icon.delete()
      self.delete()
      return ecore.ECORE_CALLBACK_CANCEL

   def close(self):
      if self.timer:
         self.timer.delete()
      self.hide_timer_cb()

   def text_set(self, text):
      self.part_text_set('emc.text.caption', text)
   
   def icon_set(self, icon):
      self.part_text_set('emc.text.caption', text)
      # TODO need to del the old image ??
      self._icon = gui.load_image(icon)

###############################################################################
class EmcSourceSelector(EmcDialog):
   """ TODO doc this
   """

   def __init__(self, title = 'Source Selector', done_cb=None, cb_data=None):
      self._selected_cb = done_cb
      self._selected_cb_data = cb_data
      self._glist = elementary.Genlist(gui.win)
      self._glist.style_set('dialog')
      self._glist.homogeneous_set(True)
      self._glist.select_mode_set(elementary.ELM_OBJECT_SELECT_MODE_ALWAYS)
      self._glist.focus_allow_set(False)
      self._glist.callback_clicked_double_add(self._cb_item_selected)
      self._glist_itc = elementary.GenlistItemClass(item_style = 'default',
                                 text_get_func = self._genlist_folder_label_get,
                                 content_get_func = self._genlist_folder_icon_get)
      self._glist_itc_back = elementary.GenlistItemClass(item_style = 'default',
                                 text_get_func = self._genlist_back_label_get,
                                 content_get_func = self._genlist_back_icon_get)
      
      EmcDialog.__init__(self, title, content=self._glist, style='panel')
      self.button_add('select', selected_cb = self._cb_done_selected)
      btn = self.button_add('browse', selected_cb = self._cb_browse_selected)
      self.fman.focused_set(btn)

      self.populate(os.getenv('HOME'))

   def populate(self, folder):
      self._glist.clear()

      parent_folder = os.path.normpath(os.path.join(folder, '..'))
      if folder != parent_folder:
         self._glist.item_append(self._glist_itc_back, parent_folder)

      for fname in sorted(os.listdir(folder)):
         fullpath = os.path.join(folder, fname)
         if fname[0] != '.' and os.path.isdir(fullpath):
            self._glist.item_append(self._glist_itc, fullpath)

      self._glist.first_item.selected = True;

   def _cb_item_selected(self, list, item):
      self.populate(item.data_get())

   def _cb_done_selected(self, button):
      item = self._glist.selected_item_get()
      if item and callable(self._selected_cb):
         if self._selected_cb_data:
            self._selected_cb('file://' + item.data_get(), self._selected_cb_data)
         else:
            self._selected_cb('file://' + item.data_get())
      self.delete()

   def _cb_browse_selected(self, button):
      item = self._glist.selected_item_get()
      self.populate(item.data_get())

   def _genlist_folder_label_get(self, obj, part, item_data):
      return os.path.basename(item_data)

   def _genlist_folder_icon_get(self, obj, part, item_data):
      if part == 'elm.swallow.icon':
         return gui.load_icon('icon/folder')
      return None
   
   def _genlist_back_label_get(self, obj, part, item_data):
      return 'back'

   def _genlist_back_icon_get(self, obj, part, data):
      if part == 'elm.swallow.icon':
         return gui.load_icon('icon/back')
      return None

###############################################################################
class EmcFocusManager(object):
   """
   This class manage a list of elementary objects, usually buttons.
   You provide all the objects that can receive focus and the class
   will take care of selecting the right object when you move the selection
   """
   # this is here to hide another bug somewhere, seems __init__ is
   # not executed as I get:
   #   'EmcFocusManager' object has no attribute 'objs'
   # happend when the delete() method is executed...
   # ...obj should always exists, also without this line.  :/
   objs = []

   def __init__(self):
      self.objs = []
      self.focused = None

   def delete(self):
      """
      Delete the FocusManager instance and free all the resources used
      """
      if self.objs:
         for o in self.objs:
            o.on_mouse_in_del(self._mouse_in_cb)
         del self.objs
      del self

   def obj_add(self, obj):
      """
      Add an object to the chain, obj must be an evas object that support
      disabled_set() 'interface', usually an elementary obj will do the work.
      """
      if not self.focused:
         self.focused = obj
         obj.disabled_set(False)
      else:
         obj.disabled_set(True)
      obj.on_mouse_in_add(self._mouse_in_cb)
      self.objs.append(obj)

   def focused_set(self, obj):
      """
      Give focus to the given obj
      """
      if self.focused:
         self.focused.disabled_set(True)
      obj.disabled_set(False)
      self.focused = obj

   def focused_get(self):
      """
      Get the object that has focus
      """
      return self.focused

   def focus_move(self, direction):
      """
      Try to move the selection in th given direction.
      direction can be: 'l'eft, 'r'ight, 'u'p or 'd'own
      """
      x, y = self.focused.center
      nearest = None
      distance = 99999
      for obj in self.objs:
         if obj != self.focused:
            ox, oy = obj.center
            # discard objects in the wrong direction
            if   direction == 'l' and ox >= x: continue
            elif direction == 'r' and ox <= x: continue
            elif direction == 'u' and oy >= y: continue
            elif direction == 'd' and oy <= y: continue

            # simple calc distance (with priority in the current direction)
            if direction in ['l', 'r']:
               dis = abs(x - ox) + (abs(y - oy) * 10)
            else:
               dis = (abs(x - ox) * 10) + abs(y - oy)

            # remember the nearest object
            if dis < distance:
               distance = dis
               nearest = obj

      # select the new object if found
      if nearest:
         self.focused_set(nearest)

   def all_get(self):
      """
      Get the list of all the objects that was previously added
      """
      return self.objs

   def _mouse_in_cb(self, obj, event):
      if self.focused != obj:
         self.focused_set(obj)


###############################################################################
class EmcFocusManager2(object):
   """
   This class manage a list of elementary objects, usually buttons.
   You provide all the objects that can receive focus and the class
   will take care of selecting the right object when you move the selection
   Dont forget to call the delete() method when not needed anymore!!
   If you want the class to automanage input events just pass an unique name
   as the autoeventsname param. 
   """

   def __init__(self, autoeventsname=None):
      self.objs = []
      self.focused = None
      self.autoeventsname = autoeventsname
      if autoeventsname is not None:
         input_events.listener_add(autoeventsname, self._input_event_cb)

   def delete(self):
      """ Delete the FocusManager instance and free all the used resources """
      if self.autoeventsname is not None:
         input_events.listener_del(self.autoeventsname)

      if self.objs:
         for o in self.objs:
            o.on_mouse_in_del(self._mouse_in_cb)
         del self.objs
      del self

   def obj_add(self, obj):
      """
      Add an object to the chain, obj must be an evas object that support
      the focus_set() 'interface', usually an elementary obj will do the work.
      """
      if not self.focused:
         self.focused = obj
         # obj.focus_set(True)
         obj.disabled_set(False)
      else:
         # obj.focus_set(False)
         obj.disabled_set(True)
      obj.on_mouse_in_add(self._mouse_in_cb)
      self.objs.append(obj)

   def focused_set(self, obj):
      """ Give focus to the given obj """
      # obj.focus_set(True)
      if self.focused:
         self.focused.disabled_set(True)
      obj.disabled_set(False)
      self.focused = obj

   def focused_get(self):
      """ Get the object that has focus """
      return self.focused

   def focus_move(self, direction):
      """
      Try to move the selection in th given direction.
      direction can be: 'l'eft, 'r'ight, 'u'p or 'd'own
      """
      x, y = self.focused.center
      nearest = None
      distance = 99999
      for obj in self.objs:
         if obj != self.focused:
            ox, oy = obj.center
            # discard objects in the wrong direction
            if   direction == 'l' and ox >= x: continue
            elif direction == 'r' and ox <= x: continue
            elif direction == 'u' and oy >= y: continue
            elif direction == 'd' and oy <= y: continue

            # simple calc distance (with priority in the current direction)
            if direction in ['l', 'r']:
               dis = abs(x - ox) + (abs(y - oy) * 10)
            else:
               dis = (abs(x - ox) * 10) + abs(y - oy)

            # remember the nearest object
            if dis < distance:
               distance = dis
               nearest = obj

      # select the new object if found
      if nearest:
         self.focused_set(nearest)

   def all_get(self):
      """ Get the list of all the objects that was previously added """
      return self.objs

   def _mouse_in_cb(self, obj, event):
      if self.focused != obj:
         self.focused_set(obj)

   def _input_event_cb(self, event):
      if event == 'LEFT':
         self.focus_move('l')
         return input_events.EVENT_BLOCK
      if event == 'RIGHT':
         self.focus_move('r')
         return input_events.EVENT_BLOCK
      if event == 'UP':
         self.focus_move('u')
         return input_events.EVENT_BLOCK
      if event == 'DOWN':
         self.focus_move('d')
         return input_events.EVENT_BLOCK
      return input_events.EVENT_CONTINUE

###############################################################################
# class EmcVKeyboard(elementary.InnerWindow):
class EmcVKeyboard(EmcDialog):
   """ TODO doc this """
   def __init__(self, accept_cb = None, dismiss_cb = None,
                title = None, text = None):
      """ TODO doc this """

      self.accept_cb = accept_cb
      self.dismiss_cb = dismiss_cb
      self.current_button = None

      # table
      tb = elementary.Table(gui.win)
      tb.homogeneous_set(True)
      tb.show()

      # set dialog title
      self.part_text_set('emc.text.title', title or 'Insert text')

      # entry
      self.entry = elementary.Entry(gui.win) # TODO use scrolled_entry instead
      self.entry.style_set('vkeyboard')
      self.entry.editable_set(False)
      self.entry.single_line_set(True)
      self.entry.focus_allow_set(False)
      self.entry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      self.entry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      if text: self.text_set(text)
      tb.pack(self.entry, 0, 0, 10, 1)
      self.entry.show()

      # focus manager
      self.efm = EmcFocusManager2()

      # standard keyb
      for i, c in enumerate(['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']):
         self._pack_btn(tb, i, 1, 1, 1, c, cb = self._default_btn_cb)
      for i, c in enumerate(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']):
         self._pack_btn(tb, i, 2, 1, 1, c, cb = self._default_btn_cb)
      for i, c in enumerate(['k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't']):
         self._pack_btn(tb, i, 3, 1, 1, c, cb = self._default_btn_cb)
      for i, c in enumerate(['u', 'v', 'w', 'x', 'y', 'z', '.', '@', '-', '_']):
         self._pack_btn(tb, i, 4, 1, 1, c, cb = self._default_btn_cb)

      self._pack_btn(tb, 0, 5, 3, 1, 'UPPERCASE', cb = self._uppercase_cb)
      self._pack_btn(tb, 3, 5, 4, 1, 'SPACE', cb = self._space_cb)
      self._pack_btn(tb, 7, 5, 3, 1, 'ERASE', cb = self._erase_cb)

      self._pack_btn(tb, 0, 6, 4, 1, 'Dismiss', 'icon/cancel', self._dismiss_cb)
      self._pack_btn(tb, 6, 6, 4, 1, 'Accept',  'icon/ok',     self._accept_cb)

      # init the parent EmcDialog class
      EmcDialog.__init__(self, title = title, style = 'minimal', content = tb)

       # catch input events
      input_events.listener_add('vkbd', self.input_event_cb)

   def _pack_btn(self, tb, x, y, w, h, label, icon = None, cb = None):
      b = EmcButton(label=label, icon=icon)
      b.size_hint_weight_set(evas.EVAS_HINT_EXPAND, 0.0)
      b.size_hint_align_set(evas.EVAS_HINT_FILL, 0.0)
      if cb: b.callback_clicked_add(cb)
      b.data['cb'] = cb
      self.efm.obj_add(b)
      tb.pack(b, x, y, w, h)
      return b

   def delete(self):
      input_events.listener_del('vkbd')
      self.efm.delete()
      EmcDialog.delete(self)

   def text_set(self, text):
      self.entry.text = text
      self.entry.cursor_end_set()

   def _dismiss_cb(self, button):
      if self.dismiss_cb and callable(self.dismiss_cb):
         self.dismiss_cb(self)
      self.delete()

   def _accept_cb(self, button):
      if self.accept_cb and callable(self.accept_cb):
         self.accept_cb(self, self.entry.entry_get())
      self.delete()

   def _default_btn_cb(self, button):
      self.entry.cursor_end_set()
      self.entry.entry_insert(button.text)

   def _erase_cb(self, button):
      if len(self.entry.text) > 0:
         self.entry.text = self.entry.text[0:-1]
         self.entry.cursor_end_set()

   def _space_cb(self, button):
      self.entry.entry_insert(' ')

   def _uppercase_cb(self, button):
      for btn in self.efm.all_get():
         c = btn.text
         if len(c) == 1 and c.isalpha():
            if c.islower():
               btn.text = c.upper()
               button.text = 'LOWERCASE'
            else:
               btn.text = c.lower()
               button.text = 'UPPERCASE'
      self.entry.cursor_end_set()

   def input_event_cb(self, event):
      if event == 'OK':
         btn = self.efm.focused_get()
         if callable(btn.data['cb']):
            btn.data['cb'](btn)
      elif event == 'EXIT':
         self._dismiss_cb(None)
      elif event == 'LEFT':  self.efm.focus_move('l')
      elif event == 'RIGHT': self.efm.focus_move('r')
      elif event == 'UP':    self.efm.focus_move('u')
      elif event == 'DOWN':  self.efm.focus_move('d')         
      
      return input_events.EVENT_BLOCK
  
