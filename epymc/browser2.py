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


_views = {}  # key = view name   value = view class instance
_memorydb = None  # EmcDatabase  key = page url  value = style name


def init():
   global _memorydb
   _memorydb = EmcDatabase('broser_view_memory22')
   if not ini.has_option('general', 'back_in_lists'):
      ini.set('general', 'back_in_lists', 'True') # 'True' should be True,
                                                  # but rise an error if option
                                                  # doesn't exist in .conf  :/

def shutdown():
   global _memorydb
   del _memorydb


class EmcBrowserITC():
   def __init__(self):
      pass

   def item_selected(self, url, browser, user_data):
      pass

   def label_get(self, url, browser, user_data):
      return "Unknow"

   def fanart_get(self, url, browser, user_data):
      return None

   def poster_get(self, url, browser, user_data):
      return None

   def info_get(self, url, browser, user_data):
      return None

   def icon_get(self, url, browser, user_data):
      return None

   def icon_end_get(self, browser, url, user_data):
      return None




class EmcBrowser(object):
   """
   This is the browser object, it is used to show various page each containing
   a list. Usually you need a single instance of this class for all your needs.
   In order you have to: 
    1. create an instance of the EmcBrowser class
         ex: my_browser = EmcBrowser("my_browser")
    2. add a page using the page_add() method
         ex: my_browser.page_add(url, title, populate_func)
    3. inside the populate_func you must add all the items using the
       item_add() method.
         ex: 
   
   Later you can add new pages or use the back(), clear(), show(), hide() methods.

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

   def __init__ (self, name, default_style = 'List', em_itc = None):

      DBG('EmcBrowser2 __init__')
      self.name = name
      self.default_style = default_style
      self.em_itc = em_itc
      self.pages = []
      self.current_view = None
      self.is_back = False
      self.is_refresh = False
      
      self.back_itc = BackITC()

   def _search_style_in_parent(self):
      for p in reversed(self.pages):
         if _memorydb.id_exists(p['url']):
            return _memorydb.get_data(p['url'])
      return None

   def page_add(self, url, title, populate_func, style = None):
      """
      When you create a page you need to give at least the url, the title
      and the populate func. The populate_func is called when you add a 
      page and also later when the browser need to reshow the created page
      (when the user goes back or in general when the page need to be recreated)
      """

      if not callable(populate_func):
         DBG('WARNING: POLULATE_F NOT CALLABLE')
         return
      
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
         self.pages.append({'view': view, 'url': url,
                           'title': title, 'populate_func': populate_func})

      # first time, we don't have a current_view, set it
      if not self.current_view:
         self.current_view = view

      # set topbar title
      full = '> ' + ''.join([page['title'] + ' > ' for page in self.pages])
      gui.text_set("topbar/title", full[0:-3])

      # same style for the 2 pages, ask the view to perform the correct animation
      if (view == self.current_view):
         if self.is_back:
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
         self.item_add('emc://back', self.back_itc)
      
      # polulate the page
      populate_func(url)

      # just for debug
      #self._dump_all()

   def item_add(self, url, em_itc = None, user_data = None):
      """
      Use this method to add an item in the current (last added) page
      Url should be (but its not mandatory) a full correct url in the form:
      file:///home/user/some/dir

      The browser object understand some special url starting with emc://
      emc://back - If you use this url the item will automatically make the
                  browser go back when selected, and no item_selected_cb
                  will be called
      """
      if (not em_itc or self.em_itc):
         DBG('No item class for url: ' + url + ' skipping...')
         return
      
      # WRN: ITEM_DATA keep consistent
      item_data = (url, self, em_itc or self.em_itc, user_data)
      self.current_view.item_add(item_data)

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
      page = self.pages.pop()

      # recreate the page
      self.is_back = True
      self.page_add(page['url'], page['title'], page['populate_func'])

   def refresh(self):
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
      self.is_refresh = True
      DBG("RECREATE "+page_url)
      page = self.pages[-1]
      self.page_add(page_url, page['title'], page['populate_func'])

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

   def _dump_all(self):
      DBG('*' * 70)
      DBG('*' * 70)
      DBG('name: ' + self.name + '  pages: ' + str(len(self.pages)));
      for p in self.pages:
         DBG('page: ' + str(p));
      DBG('current view: ' + str(self.current_view))
      DBG('*' * 70)
      for v in _views:
         DBG('view: ' + str(v));
      DBG('*' * 70)
      # for s in _style_memory:
         # DBG('style mem: %s  style: %s' % (s, _style_memory[s]));
      DBG('*' * 70)


################################################################################
   # Stuff for Views
"""
   def _icon_get(self, url):
      # if url.startswith('emc://'):
         # if url.endswith('/back'):
            # return gui.load_icon('icon/back')
# 
      # if self.pages[-1]['icon_get_cb']:
         # func = self.pages[-1]['icon_get_cb']
      # else:
         # func = self.icon_get_cb
      # if not callable(func): return None
      # icon = func(self.pages[-1]["url"], url)
      # if not icon: return None
      # return gui.load_icon(icon)
      return None
"""

################################################################################

class BackITC(EmcBrowserITC):
   def __init__(self):
      EmcBrowserITC.__init__(self) # not really needed
   
   def label_get(self, url, browser, user_data):
      return "back"
   
   def info_get(self, url, browser, user_data):
      return "Back to previous page"
      
   def icon_get(self, url, browser, user_data):
      return gui.load_icon('icon/back')
   
   def item_selected(self, url, browser, user_data):
      browser.back()


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

      # EXTERNAL Genlist1
      self.gl1 = gui.part_get('browser/list/genlist1')
      self.gl1.style_set("browser")
      self.gl1.homogeneous_set(True)
      self.gl1.always_select_mode_set(True)
      self.gl1.callback_clicked_add(self._cb_item_selected)
      self.gl1.callback_selected_add(self._cb_item_hilight)
      self.current_list = self.gl1

      # EXTERNAL Genlist2
      self.gl2 = gui.part_get('browser/list/genlist2')
      self.gl2.style_set("browser")
      self.gl2.homogeneous_set(True)
      self.gl2.always_select_mode_set(True)
      self.gl2.callback_clicked_add(self._cb_item_selected)
      self.gl2.callback_selected_add(self._cb_item_hilight)

      # genlist item class
      self.itc = elementary.GenlistItemClass(item_style="default",
                                 text_get_func = self.__genlist_label_get,
                                 icon_get_func = self.__genlist_icon_get,
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

   def item_add(self, item_data): #label, parent_browser):
      """
      Here you must add the item to the current visible page
      You can use the 'parent_browser' object to query more info about
      the item using: parent_browser._icon_get() _poster_get() ect..

      When an item will be selected you should call:
      parent_browser._item_selected(url) with the url of the selected item
      """
      it = self.current_list.item_append(self.itc, item_data)
      if not self.current_list.selected_item_get():
         it.selected_set(1)

   def show(self):
      """ Show the view """
      gui.signal_emit("browser,list,show")

   def hide(self):
      """ Hide the view """
      gui.signal_emit("browser,list,hide")

   def clear(self):
      """ Clear the view """
      self.gl1.clear()
      self.gl2.clear()

   def refresh(self):
      item = self.current_list.first_item_get()
      while item:
         item.update()
         item = item.next_get()

   def input_event_cb(self, event):
      """ Here you can manage input events for the view """

      item = self.current_list.selected_item_get()
      (url, browser, em_itc, user_data) = item.data_get() # WRN: ITEM_DATA keep consistent

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
         em_itc.item_selected(url, browser, user_data)
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

   ### GenList Item Class
   def __genlist_label_get(self, obj, part, item_data):
      (url, browser, em_itc, user_data) = item_data # WRN: ITEM_DATA keep consistent
      return em_itc.label_get(url, browser, user_data)

   def __genlist_icon_get(self, obj, part, item_data):
      (url, browser, em_itc, user_data) = item_data # WRN: ITEM_DATA keep consistent
      if part == 'elm.swallow.icon':
         return em_itc.icon_get(url, browser, user_data)
      elif part == 'elm.swallow.end':
         return em_itc.icon_end_get(url, browser, user_data)
      return None

   def __genlist_state_get(self, obj, part, item_data):
      return False

   ### GenList Callbacks
   def _cb_item_selected(self, list, item):
      (url, browser, em_itc, user_data) = item.data_get() # WRN: ITEM_DATA keep consistent
      em_itc.item_selected(url, browser, user_data)

   def _cb_item_hilight(self, list, item):
      try: self.last_item
      except AttributeError:
         self.last_item = None

      if item != self.last_item:
         if self.timer: self.timer.delete()
         if self.timer2: self.timer2.delete()
         self.timer = ecore.timer_add(0.5, self._cb_timer, item.data_get())
         self.timer2 = ecore.timer_add(1.0, self._cb_timer2, item.data_get())

      self.last_item = item

   def _cb_timer(self, item_data):
      (url, browser, em_itc, user_data) = item_data # WRN: ITEM_DATA keep consistent

      # Ask for the item poster and show (or auto-download) it
      poster = em_itc.poster_get(url, browser, user_data)
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

      # Fill the textblock with item info info
      text = em_itc.info_get(url, browser, user_data)
      gui.text_set('browser/list/info', text or "")

      return False # don't repeat the timer

   def _cb_timer2(self, item_data):
      (url, browser, em_itc, user_data) = item_data # WRN: ITEM_DATA keep consistent

      # Ask for the item poster and show (or auto-download) it
      fanart = em_itc.fanart_get(url, browser, user_data)
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
                                       label_get_func=self.gg_label_get,
                                       icon_get_func=self.gg_icon_get,
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

   def item_add(self, item_data):
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
      (url, browser, em_itc, user_data) = item.data_get() # WRN: ITEM_DATA keep consistent

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
         em_itc.item_selected(url, browser, user_data)
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

   # gengrid model
   def gg_label_get(self, obj, part, item_data):
      (url, browser, em_itc, user_data) = item_data # WRN: ITEM_DATA keep consistent
      return em_itc.label_get(url, browser, item_data)

   def gg_icon_get(self, obj, part, item_data):
      (url, browser, em_itc, user_data) = item_data # WRN: ITEM_DATA keep consistent
      if part == 'elm.swallow.icon':
         return em_itc.icon_get(url, browser, user_data)
      elif part == 'elm.swallow.end':
         return em_itc.icon_end_get(url, browser, user_data)
      return None

   def gg_state_get(self, obj, part, item_data):
      return False

   def gg_del(self, obj, item_data):
      pass

   # gengrid callbacks
   def gg_higlight(self, gg, item, *args, **kwargs):
      pass

   def gg_selected(self, gg, item, *args, **kwargs):
      (url, browser, em_itc, user_data) = item.data_get() # WRN: ITEM_DATA keep consistent
      em_itc.item_selected(url, browser, user_data)
