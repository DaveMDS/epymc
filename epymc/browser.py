#!/usr/bin/env python
#
# Copyright (C) 2010 Davide Andreoli <dave@gurumeditation.it>
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

import evas
import ecore
import elementary

import gui
import mainmenu
import input_events
import ini
from sdb import EmcDatabase

def DBG(msg):
   # print ('BROWSER: ' + msg)
   pass


_views = {}  # key = view_name  value = view class instance
_memorydb = None  # EmcDatabase  key = page url  value = style name
_instances = [] # keep track of EmcBrowser instances. just for dump_all()


def init():
   global _memorydb
   _memorydb = EmcDatabase('broser_view_memory')
   if not ini.has_option('general', 'back_in_lists'):
      ini.set('general', 'back_in_lists', 'True')

def shutdown():
   global _memorydb
   del _memorydb

def dump_everythings():
   print('*' * 70)
   for v in _views:
      print ('loaded view: ' + str(v))
   for b in _instances:
      print b

class EmcBrowser(object):
   """
   This is the browser object, it is used to show various page each containing
   a list. Usually you need a single instance of this class for all your needs.
   In order you have to: create an instance, add a page using the page_add()
   method and add items to the page using item_add(). Later you can
   create new pages or use the back(), clear(), show(), hide() methods.

   At creation you can set the following callbacks:
      * item_selected_cb(page_url, item_url):
         Called when an item is selected
      * icon_get_cb(page_url, item_url):
         Called when a view need to show the icon of your item,
         must return the icon to use for the given url
         TODO what icon are supported?? name? object? standard?
      * poster_get_cb(page_url, item_url):
         Called when a view need to show the poster/cover/big_image of your
         item, must return the full path of a valid image file.
         You can also return a valid url (http://) to automatically
         download the image to a random temp file. In addition you can also
         set the destinatioon path for the give url, just use ';'.
         ex: 'http://my.url/of/the/image;/my/local/dest/path'
      * info_get_cb(page_url, item_url):
         Called when a view need to show the info of your item,
         must return a string with the murkupped text that describe the item
      * fanart_get_cb(page_url, item_url):
         Called when a view need to show the fanart of your item,
         must return the full path of a valid image file
         
   TODO doc default_style and style in general
   """

   def __init__ (self, name, default_style = 'List', item_selected_cb = None,
                  icon_get_cb = None, icon_end_get_cb = None,
                  info_get_cb = None, poster_get_cb = None,
                  fanart_get_cb = None):

      DBG('EmcBrowser __init__')
      _instances.append(self)
      self.name = name
      self.default_style = default_style

      self.item_selected_cb = item_selected_cb
      self.icon_get_cb = icon_get_cb
      self.icon_end_get_cb = icon_end_get_cb
      self.info_get_cb = info_get_cb
      self.poster_get_cb = poster_get_cb
      self.fanart_get_cb = fanart_get_cb
      
      self.pages = []
      self.current_view = None
      self.is_back = False
      self.is_refresh = False

   def __str__(self):
      text  = '=' * 70 + '\n'
      text += '===  %s  %s\n' % (self.name, '=' * (63-len(self.name)))
      text += '== name: %s  pages: %d curview: %s\n' % \
              (self.name, len(self.pages), self.current_view)
      for p in self.pages:
         text += '== page: ' + str(p) + '\n'
      text += '=' * 70 + '\n'
      # for s in _style_memory:
         # text += 'style mem: %s  style: %s\n' % (s, _style_memory[s])
      # text += '*' * 70 + '\n'
      return text

   def delete(self):
      _instances.remove(self)
      del self

   def _search_style_in_parent(self):
      for p in reversed(self.pages):
         if _memorydb.id_exists(p['url']):
            return _memorydb.get_data(p['url'])
      return None
      
   def page_add(self, url, title, style = None, item_selected_cb = None,
                 icon_get_cb = None, icon_end_get_cb = None,
                 info_get_cb = None, poster_get_cb = None, fanart_get_cb = None):
      """
      When you create a page you need to give at least the url and the title
      """
      # create a new page data (if not a refresh operation)
      if self.is_refresh:
         view = self.pages[-1]['view']
      else:
         # choose the style of the new page
         if _memorydb.id_exists(url):
            style = _memorydb.get_data(url)
         else:
            style = self._search_style_in_parent()
         if not style:
            style = self.default_style

         # get the correct view instance
         view = self._create_or_get_view(style)
         
         # append the new page info in the pages list
         self.pages.append({'view': view, 'url': url, 'title': title,
                            'item_selected_cb': item_selected_cb,
                            'icon_get_cb': icon_get_cb,
                            'icon_end_get_cb': icon_end_get_cb,
                            'info_get_cb': info_get_cb,
                            'poster_get_cb': poster_get_cb,
                            'fanart_get_cb': fanart_get_cb})

      # first time, we don't have a current_view, set it
      if not self.current_view:
         self.current_view = view

      # set topbar title
      full = '> ' + ''.join([page['title'] + ' > ' for page in self.pages])
      full = full[0:-3]
      gui.text_set("topbar/title", full)

      # same style for the 2 pages, ask the view to perform the correct animation
      if (view == self.current_view):
         if self.is_refresh:
            view.page_show(page['title'], 0)
         elif self.is_back:
            view.page_show(page['title'], -1)
         elif len(self.pages) < 2:
            view.page_show(page['title'], 0)
         else:
            view.page_show(page['title'], 1)
      else:
         # different style...hide one view and show the other
         self.current_view.clear()
         self.current_view.hide()
         view.page_show(page['title'], 0)
         view.show()

      # update state
      self.current_view = view
      self.is_refresh = False
      self.is_back = False

      # back item (optional)
      if ini.get_bool('general', 'back_in_lists') == True:
         self.item_add('emc://back', 'back', dont_count = True)

      # use this for extra debug
      # print self

   def item_add(self, url, label, dont_count = False):
      """
      Use this method to add an item in the current (last added) page
      Url should be (but its not mandatory) a full correct url in the form:
      file:///home/user/some/dir

      The browser object understand some special url starting with emc://
      emc://back - If you use this url the item will automatically make the
                  browser go back when selected, and no item_selected_cb
                  will be called
      """
      self.current_view.item_add(url, label, self, dont_count)

   def back(self):
      """ TODO Function doc """
      
      # discard current page
      self.pages.pop()

      # no more page to go back, hide view and return to main menu
      if len(self.pages) <= 0:
         self.hide()
         self.current_view.clear()
         mainmenu.show()
         return

      # discard previous also, will recreate...
      page_data = self.pages.pop()

      # recreate the page
      self.is_back = True
      parent_url = self.pages[-1]['url'] if len(self.pages) > 1 else None
      func = self.item_selected_cb
      if func: func(parent_url, page_data['url'])

   def refresh(self, recreate=False):
      if recreate:
         # recreate the page calling the selected_cb on the parent-page
         self.is_refresh = True
         page_url = self.pages[-1]['url'] if len(self.pages) > 0 else None
         parent_url = self.pages[-2]['url'] if len(self.pages) > 1 else None
         func = self.item_selected_cb
         if func: func(parent_url, page_url)
      else:
         self.current_view.refresh()

   def change_style(self, style):

      view = self._create_or_get_view(style)
      
      # change only if needed
      if view == self.current_view:
         return

      # clear & hide the current view
      self.current_view.clear()
      self.current_view.hide()

      # set the new view in the current (always the last) page
      self.pages[-1]['view'] = view

      # remember the user choice
      global _memorydb
      page_url = self.pages[-1]['url']
      _memorydb.set_data(page_url, style)

      # recreate the page
      self.refresh(recreate=True)

   def clear(self):
      """ TODO Function doc """
      pass #TODO implement

   def show(self):
      """ TODO Function doc """
      gui.signal_emit("topbar,show")
      self.current_view.show()
      input_events.listener_add('browser-' + self.name, self._input_event_cb)

   def hide(self):
      """ TODO Function doc """
      gui.signal_emit("topbar,hide")
      input_events.listener_del('browser-' + self.name)
      self.current_view.hide()

   # private stuff
   def _input_event_cb(self, event):

      if event == "BACK":
         self.back()
      elif event == 'VIEW_LIST':
         self.change_style("List")
      elif event == 'VIEW_GRID':
         self.change_style("Grid")
      else:
         return self.current_view.input_event_cb(event)

      return input_events.EVENT_BLOCK

   def _create_or_get_view(self, view_name):
      if _views.has_key(view_name):
         DBG('View exists: ' + view_name)
         return _views[view_name]
      # call the constructor of the given class style ex: ViewList()
      DBG('Create view: ' + view_name)
      _views[view_name] = eval('View' + view_name + '()')
      return _views[view_name]

   # Stuff for Views
   def _item_selected(self, url):
      """ TODO Function doc """
      if url.startswith("emc://"):
         if url.endswith("//back"):
            self.back()
      else:
         if self.pages[-1]['item_selected_cb']:
            func = self.pages[-1]['item_selected_cb']
         else:
            func = self.item_selected_cb
         if callable(func): func(self.pages[-1]["url"], url)

   def _icon_get(self, url):
      """ TODO Function doc """
      if url.startswith('emc://'):
         if url.endswith('/back'):
            return gui.load_icon('icon/back')

      if self.pages[-1]['icon_get_cb']:
         func = self.pages[-1]['icon_get_cb']
      else:
         func = self.icon_get_cb
      if not callable(func): return None
      icon = func(self.pages[-1]["url"], url)
      if not icon: return None
      return gui.load_icon(icon)

   def _icon_end_get(self, url):
      """ TODO Function doc """
      if url.startswith('emc://'):
         return None
      if self.pages[-1]['icon_end_get_cb']:
         func = self.pages[-1]['icon_end_get_cb']
      else:
         func = self.icon_end_get_cb
      if not callable(func): return None
      icon = func(self.pages[-1]["url"], url)
      if not icon: return None
      return gui.load_icon(icon)

   def _poster_get(self, url):
      """ TODO Function doc """
      if self.pages[-1]['poster_get_cb']:
         func = self.pages[-1]['poster_get_cb']
      else:
         func = self.poster_get_cb
      return func(self.pages[-1]["url"], url) if callable(func) else None

   def _fanart_get(self, url):
      """ TODO Function doc """
      if self.pages[-1]['fanart_get_cb']:
         func = self.pages[-1]['fanart_get_cb']
      else:
         func = self.fanart_get_cb
      return func(self.pages[-1]["url"], url) if callable(func) else None

   def _info_get(self, url):
      """ TODO Function doc """
      if self.pages[-1]['info_get_cb']:
         func = self.pages[-1]['info_get_cb']
      else:
         func = self.info_get_cb
      return func(self.pages[-1]["url"], url) if callable(func) else None


################################################################################
#### List View      ############################################################
################################################################################
class ViewList(object):
   """
   This is the basic view, it use a genlist to show items and have a
   poster and a short info on the right. 2 genlist are used to perform
   animation between the page.
   This view is the reference one with all the documentation, can be also
   used as a starting base for new views.
   """

   ### Mandatory methods, all the views must implement this functions
   def __init__(self):
      """
      This is the init founction for the view, it is called one time only
      when the view is needed for the first time. Here you must do your
      initialization stuff.
      """
      DBG('Init view: plain list')

      self.timer = self.timer2 = None
      self.items_count = 0;

      # EXTERNAL Genlist1
      self.gl1 = gui.part_get('browser/list/genlist1')
      self.gl1.style_set("browser")
      self.gl1.homogeneous_set(True)
      self.gl1.always_select_mode_set(True)
      self.gl1.focus_allow_set(False)
      self.gl1.callback_clicked_double_add(self._cb_item_selected)
      self.gl1.callback_selected_add(self._cb_item_hilight)
      self.current_list = self.gl1

      # EXTERNAL Genlist2
      self.gl2 = gui.part_get('browser/list/genlist2')
      self.gl2.style_set("browser")
      self.gl2.homogeneous_set(True)
      self.gl2.always_select_mode_set(True)
      self.gl2.focus_allow_set(False)
      self.gl2.callback_clicked_double_add(self._cb_item_selected)
      self.gl2.callback_selected_add(self._cb_item_hilight)

      # genlist item class
      self.itc = elementary.GenlistItemClass(item_style="default",
                                 text_get_func = self.__genlist_label_get,
                                 content_get_func = self.__genlist_icon_get,
                                 state_get_func = self.__genlist_state_get)

      # RemoteImage (poster)
      self.__im = gui.EmcRemoteImage(gui.win)
      gui.swallow_set('browser/list/poster', self.__im)

   def page_show(self, title, dir):
      """
      This function is called everytime a new page need to be showed.
      The 'dir' param tell you direction of the browse:
        -1 means we are going back
         1 means forward
         0 means no previous page
      You can use the 'dir' param to perform the correct animation if needed
      """
      DBG('page show ' + str(dir))

      if (dir != 0):
         if self.current_list == self.gl1:
            self.current_list = self.gl2
         else:
            self.current_list = self.gl1

      if dir == 1:
         gui.signal_emit('browser,list,flip_left')
      elif dir == -1:
         gui.signal_emit('browser,list,flip_right')

      self.current_list.clear()
      self.items_count = 0

   def item_add(self, url, label, parent_browser, dont_count = False):
      """
      Here you must add the item to the current visible page
      You can use the 'parent_browser' object to query more info about
      the item using: parent_browser._icon_get() _poster_get() ect..

      When an item will be selected you should call:
      parent_browser._item_selected(url) with the url of the selected item
      """
      DBG("item_add( , %s, %s)" % (url, label))
      item_data = (url, label, parent_browser)
      it = self.current_list.item_append(self.itc, item_data)
      if not self.current_list.selected_item_get():
         it.selected_set(1)

      if not dont_count:
         self.items_count += 1
         gui.text_set('browser/list/total', '%d items' % (self.items_count))

   def show(self):
      """ Show the view """
      gui.signal_emit("browser,list,show")

   def hide(self):
      """ Hide the view """
      if self.timer: self.timer.delete()
      if self.timer2: self.timer2.delete()
      gui.signal_emit("browser,list,hide")

   def clear(self):
      """ Clear the view """
      if self.timer: self.timer.delete()
      if self.timer2: self.timer2.delete()
      self.gl1.clear()
      self.gl2.clear()
      self.items_count = 0

   def refresh(self):
      for item in self.current_list.realized_items_get():
         item.update()
      # fake an item-hilight to refresh info, poster and fanart
      self._cb_item_hilight(self.current_list, self.current_list.selected_item)
      

   def input_event_cb(self, event):
      """ Here you can manage input events for the view """

      item = self.current_list.selected_item_get()
      (url, label, parent_browser) = item.data_get()

      if event == "DOWN":
         next = item.next_get()
         if next:
            next.selected_set(1)
            next.show()
            return input_events.EVENT_BLOCK

      elif event == "UP":
         prev = item.prev_get()
         if prev:
            prev.selected_set(1)
            prev.show()
            return input_events.EVENT_BLOCK

      elif event == "OK":
         parent_browser._item_selected(url)
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

   ### GenList Item Class
   def __genlist_label_get(self, obj, part, item_data):
      (url, label, parent_browser) = item_data
      DBG("LABEL: " + label)
      return label

   def __genlist_icon_get(self, obj, part, data):
      (url, label, parent_browser) = data
      DBG("_content get(): " + label)
      if part == 'elm.swallow.icon':
         return parent_browser._icon_get(url)
      elif part == 'elm.swallow.end':
         return parent_browser._icon_end_get(url)
      return None

   def __genlist_state_get(self, obj, part, item_data):
      return False

   ### GenList Callbacks
   def _cb_item_selected(self, list, item):
      (url, label, parent_browser) = item.data_get()
      parent_browser._item_selected(url)

   def _cb_item_hilight(self, list, item):
      if self.timer: self.timer.delete()
      if self.timer2: self.timer2.delete()
      self.timer = ecore.timer_add(0.5, self._cb_timer, item.data_get())
      self.timer2 = ecore.timer_add(1.0, self._cb_timer2, item.data_get())

   def _cb_timer(self, data):
      (url, label, parent_browser) = data

      # Fill the textblock with item info info
      text = parent_browser._info_get(url)
      gui.text_set('browser/list/info', text or "")

      # Ask for the item poster and show (or auto-download) it
      poster = parent_browser._poster_get(url)
      if poster and poster.startswith("http://"):
         if poster.find(';') != -1:
            (url, dest) = poster.split(';')
            self.__im.url_set(url, dest)
         else:
            self.__im.url_set(poster)
      elif poster and poster.startswith("icon/"):
         self.__im.file_set(gui.theme_file, poster)
      else:
         self.__im.file_set(poster if poster else "")

      return False # don't repeat the timer

   def _cb_timer2(self, data):
      (url, label, parent_browser) = data

      # Ask for the item fanart
      fanart = parent_browser._fanart_get(url)
      if fanart: gui.background_set(fanart)

      return False # don't repeat the timer


################################################################################
#### Grid View  ################################################################
################################################################################
class ViewGrid(object):
   def __init__(self):
      """ TODO Function doc """
      DBG('Init view: grid')

      self.itc = elementary.GengridItemClass(item_style="default",
                                       text_get_func=self.gg_label_get,
                                       content_get_func=self.gg_icon_get,
                                       state_get_func=self.gg_state_get,
                                       del_func=self.gg_del)
      gg = elementary.Gengrid(gui.win)
      gg.style_set("browser")
      gg.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
      gg.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
      gg.horizontal_set(False)
      gg.bounce_set(False, True)
      gg.item_size_set(150, 150)
      gg.align_set(0.5, 0.0)
      gg.callback_selected_add(self.gg_higlight)
      gg.callback_clicked_add(self.gg_selected)
      gui.swallow_set("browser/grid/gengrid", gg)
      self.gg = gg

   def page_show(self, title, dir):
      self.gg.clear()
      gui.text_set("browser/grid/title", title)

   def item_add(self, url, label, parent_browser, dont_count = False):
      item_data = (url, label, parent_browser)
      it = self.gg.item_append(self.itc, item_data)
      if not self.gg.selected_item_get():
         it.selected_set(True)

   def show(self):
      gui.signal_emit("browser,grid,show")

   def hide(self):
      gui.signal_emit("browser,grid,hide")

   def clear(self):
      self.gg.clear()

   def refresh(self):
      item = self.gg.first_item_get()
      while item:
         item.update()
         item = item.next_get()

   def input_event_cb(self, event):
      item = self.gg.selected_item_get()
      (url, label, parent_browser) = item.data_get()

      if event == "RIGHT":
         # TODO FIX DOUBLE MOVE
         # elm_focus_highlight_enable_set(Eina_Bool enable); ????
         # elm_object_focus_allow_set
         next = item.next_get()
         if next:
            next.selected_set(1)
            next.bring_in()
            return input_events.EVENT_BLOCK

      elif event == "LEFT":
         prev = item.prev_get()
         if prev:
            prev.selected_set(1)
            prev.bring_in()
            return input_events.EVENT_BLOCK

      elif event == "UP":
         (x, y) = item.pos_get()
         # TODO
         return input_events.EVENT_BLOCK

      elif event == "DOWN":
         (x, y) = item.pos_get()
         # TODO
         return input_events.EVENT_BLOCK

      elif event == "OK":
         parent_browser._item_selected(url)
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

   # gengrid model
   def gg_label_get(self, obj, part, item_data):
      (url, label, parent_browser) = item_data
      return label

   def gg_icon_get(self, obj, part, data):
      (url, label, parent_browser) = data
      if part == 'elm.swallow.icon':
         return parent_browser._icon_get(url)
      elif part == 'elm.swallow.end':
         return parent_browser._icon_end_get(url)
      return None

   def gg_state_get(self, obj, part, item_data):
      return False

   def gg_del(self, obj, item_data):
      pass

   # gengrid callbacks
   def gg_higlight(self, gg, item, *args, **kwargs):
      pass

   def gg_selected(self, gg, item, *args, **kwargs):
      (url, label, parent_browser) = item.data_get()
      parent_browser._item_selected(url)
