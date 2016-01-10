#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2015 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of EpyMC, an EFL based Media Center written in Python.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function

import os
import sys

from efl import evas, ecore, elementary as elm
from efl.elementary.genlist import Genlist, GenlistItem, GenlistItemClass,\
   ELM_OBJECT_SELECT_MODE_ALWAYS, ELM_LIST_COMPRESS, ELM_GENLIST_ITEM_SCROLLTO_TOP, \
   ELM_GENLIST_ITEM_SCROLLTO_MIDDLE, ELM_GENLIST_ITEM_SCROLLTO_IN
from efl.elementary.gengrid import Gengrid, GengridItem, GengridItemClass
from efl.elementary.layout import Layout
from efl.elementary.label import Label, ELM_WRAP_NONE, \
   ELM_LABEL_SLIDE_MODE_NONE, ELM_LABEL_SLIDE_MODE_AUTO

from epymc import gui, mainmenu, input_events, ini
from epymc.sdb import EmcDatabase
from epymc.utils import Singleton
from epymc.gui import EmcImage, EmcScrolledEntry, EmcButton, EmcDialog, \
   EXPAND_BOTH, FILL_BOTH

def DBG(msg):
   # print('BROWSER: %s' % msg)
   pass


_views = {}       # key=>view_name  value=>view class instance
_memorydb = None  # EmcDatabase  key=>page_url  value=style_name
_instances = []   # keep track of EmcBrowser instances. just for dump_all()
_topbar_fman = None # Topbar buttons EmcFocusManager

ANIM_NONE = 0
ANIM_BACK = -1
ANIM_FORWARD = 1


def init():
   global _memorydb
   global _topbar_fman

   _memorydb = EmcDatabase('browser_view_memory')

   # setup default configs
   ini.get('general', 'back_in_lists', default_value='True')
   ini.get('general', 'ignore_views_restrictions', default_value='False')
   ini.get('general', 'view_postergrid_size', default_value=150)
   ini.get('general', 'view_covergrid_size', default_value=150)

    # fill buttons box in topbar
   topbar_button_add('view_list', 'icon/view_list',
                     input_events.event_emit, 'VIEW_LIST')
   topbar_button_add('view_postergrid', 'icon/view_postergrid',
                     input_events.event_emit, 'VIEW_POSTERGRID')
   topbar_button_add('view_covergrid', 'icon/view_covergrid',
                     input_events.event_emit, 'VIEW_COVERGRID')

def shutdown():
   global _memorydb
   del _memorydb

def topbar_button_add(name, icon, cb_func, *cb_args):
   bt = EmcButton(icon=icon)
   bt.callback_clicked_add(_topbar_buttons_cb)
   bt.data['cb_func'] = cb_func
   bt.data['cb_args'] = cb_args
   gui.box_append('topbar.box', bt)
   bt.show()

def _topbar_buttons_cb(bt):
   cb_func, cb_args = bt.data.get('cb_func'), bt.data.get('cb_args')
   cb_func(*cb_args) if cb_args else cb_func()

def dump_everythings():
   print('*' * 70)
   for v in _views:
      print('loaded view: ' + str(v))
   for b in _instances:
      print(b)


class EmcItemClass(Singleton):
   """ TODO Class doc """

   def item_selected(self, url, user_data):
      """ Called when an item is selected """
      # DBG(('item_selected(%s)' % url))
      pass

   def label_get(self, url, user_data):
      """ Called when a view need to show the label of your item.
          Must return the string to show. """
      # DBG(('label_get(%s)' % url))
      return 'Unknow'

   def label_end_get(self, url, user_data):
      """ Called when a view need to show the secondary label of your item.
          Must return the string to show, or None """
      return None

   def icon_get(self, url, user_data):
      """ Called when a view need to show the icon of your item.
          Must return the name of the icon to use for the given url
          see gui.load_icon() for detail on what you can pass as the name"""
      # DBG(('icon_get(%s)' % url))
      return None

   def icon_end_get(self, url, user_data):
      # DBG(('icon_end_get(%s)' % url))
      return None

   def info_get(self, url, user_data):
      """ Called when a view need to show the info of your item.
          Must return a string with the murkupped text that describe the item """
      # DBG(('info_get(%s)' % url))
      return None

   def poster_get(self, url, user_data):
      """ Called when a view need to show the poster of your
          item, must return the full path of a valid image file.
          The poster MUST have a 1:2 aspect.
          You can also return a valid url (http://) to automatically
          download the image to a random temp file.
          In addition you can also set the destination path for the given url,
          to set an url AND a destination just return a tuple, as:
          (url, local_path)
          """
      # DBG(('poster_get(%s)' % url))
      return None

   def cover_get(self, url, user_data):
      """ Like poster_get but th image should be squared (or a bit larger) """
      # DBG(('poster_get(%s)' % url))
      return None

   def fanart_get(self, url, user_data):
      """ Called when a view need to show the fanart of your item.
          Must return the full path of a valid image file """
      # DBG(('fanart_get(%s)' % url))
      return None


class BackItemClass(EmcItemClass):
   def item_selected(self, url, user_data):
      user_data.back()

   def label_get(self, url, user_data):
      return _('Back')

   def icon_get(self, url, user_data):
      return 'icon/back'


class FolderItemClass(EmcItemClass):
   """ Base item class to be subclassed for ALL folder items """
   def item_selected(self, url, user_data):
      raise NotImplementedError

   def label_get(self, url, user_data):
      return os.path.basename(url)

   def icon_get(self, url, user_data):
      return 'icon/folder'

   def poster_get(self, url, user_data):
      return 'special/folder/' + os.path.basename(url)


class EmcBrowser(object):
   """
   This is the browser object, it is used to show various page each containing
   a list. Usually you need a single instance of this class for all your needs.
   In order you have to:
    1. implement at least one class that inherit from EmcItemClass
    2. create an instance of EmcBrowser
    3. add a page to the browser using the page_add() method
    4. add items to the current page using item_add(MyItemClass(), url, user_data)
   Later you can create new pages or use back(), clear(), show(), hide()
   """

   def __init__(self, name, default_style='List'):

      DBG('EmcBrowser __init__')
      _instances.append(self)
      self.name = name
      self.default_style = default_style

      self.pages = []
      self.current_view = None
      self.autoselect_url = None

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

   def page_add(self, url, title, styles, populate_cb, *args, **kwargs):
      """
      When you create a page you need to give at least the url, the title
      and the populate callback. Every other arguments will be passed back
      in the callback. style can be None to use the default page style,
      usually the plain list.

      Args:
         url: A unique string id for the page
         title: Readable text for the user
         styles: A tuple with all the style that the page can show.
                 Available styles: 'List', 'PosterGrid', 'CoverGrid'
                 If set to None it default to the default style given at
                 the Browser instance creation.
                 The first item is the default one.
         populate_cb: Function to call when the page need to be populated.
                      Signature: func(browser, url, *args, **kwargs)
      """

      # in py2 ensure url is not unicode (shelve will not like unicode as key)
      if sys.version_info[0] < 3 and isinstance(url, unicode):
         url = url.encode('utf8')

      # choose the style of the new page
      if styles is None:
         styles = (self.default_style,)
      if _memorydb.id_exists(url):
         style = _memorydb.get_data(url)
      else:
         style = self._search_style_in_parent()
      if not style:
         style = styles[0]
      if ini.get_bool('general', 'ignore_views_restrictions') is False:
         if not style in styles:
            style = styles[0]

      # get the correct view instance
      view = self._create_or_get_view(style)

      # append the new page in the pages list
      page = {'view': view, 'url': url, 'title': title, 'styles': styles,
              'cb': populate_cb, 'args': args, 'kwargs': kwargs}
      self.pages.append(page)

      # first time, we don't have a current_view, set it
      if not self.current_view:
         self.current_view = view

      # switch to the new page
      self._populate_page(page)

   def item_add(self, item_class, url, user_data=None):
      """
      Use this method to add an item in the current (last added) page
      Url should be (but its not mandatory) a full correct url in the form:
      file:///home/user/some/dir, it MUST be unique in all the browser
      and MUST not contain any strange chars.
      """
      if url == self.autoselect_url:
         self.current_view.item_add(item_class, url, user_data, True)
      else:
         self.current_view.item_add(item_class, url, user_data)

   def back(self):
      """ TODO Function doc """
      # discard current page
      old_page = self.pages.pop()
      self.autoselect_url = old_page['url']
      del old_page

      # no more page to go back, hide the view and return to main menu
      if len(self.pages) == 0:
         self.hide()
         # self.current_view.clear() # this fix the double click-in-back segfault :)
         mainmenu.show()
         return

      # switch to the previous page
      page_data = self.pages[-1]
      self._populate_page(page_data, is_back=True)

   def refresh(self, hard=False):
      if self.pages and self.current_view:
         if hard:
            # create the page
            page = self.pages[-1]
            self._populate_page(page, is_refresh=True)
         else:
            self.current_view.refresh()

   def change_style(self, style):
      # the current page is always the last one
      page = self.pages[-1]

      # check if the style is valid (unless not explicitly ignored)
      if ini.get_bool('general', 'ignore_views_restrictions') is False:
         if not style in page['styles']:
            DBG('Style %s not available for this page' % style)
            EmcDialog(style='info', title=_('View restriction'),
               text=_('<br><br>The requested view is not enabled for the current ' \
                      'page.<br><br><small><info>NOTE: You can ovveride this ' \
                      'restriction in the <i>Configuration → Views</i> ' \
                      'section.</info></small>'))
            return
      
      # change only if needed
      view = self._create_or_get_view(style)
      if view == self.current_view:
         return

      # remember the selected item
      self.autoselect_url = self.current_view.selected_url_get()

      # clear & hide the current view
      self.current_view.clear()
      self.current_view.hide()

      # set the new view in the current (always the last) page
      page['view'] = view

      # remember the user choice
      global _memorydb
      page_url = self.pages[-1]['url']
      _memorydb.set_data(page_url, style)

      # recreate the page
      self.refresh(hard=True)

   def clear(self):
      """ TODO Function doc """
      pass #TODO implement

   def show(self):
      """ TODO Function doc """
      gui.signal_emit('topbar,show')
      self.current_view.show()
      input_events.listener_add('browser-' + self.name, self._input_event_cb)

   def hide(self):
      """ TODO Function doc """
      gui.signal_emit('topbar,hide')
      input_events.listener_del('browser-' + self.name)
      self.current_view.hide()

   def item_bring_in(self, pos='top', animated=True):
      """ Move the view so that the currently selected item will go on 'pos'
      pos can be: 'in', ', top', 'mid'
      """
      self.current_view.item_bring_in(pos, animated)

   # private stuff
   def _populate_page(self, page, is_back=False, is_refresh=False):
      full = ' > '.join([p['title'] for p in self.pages])
      gui.text_set('topbar.title', full)

      view = page['view']
      if (view == self.current_view):
         # same style for the 2 pages, ask the view to perform the correct anim
         if is_refresh:
            view.page_show(page['title'], ANIM_NONE)
         elif is_back:
            view.page_show(page['title'], ANIM_BACK)
         elif len(self.pages) < 2:
            view.page_show(page['title'], ANIM_NONE)
         else:
            view.page_show(page['title'], ANIM_FORWARD)
      else:
         # different style...hide one view and show the other
         self.current_view.clear()
         self.current_view.hide()
         view.page_show(page['title'], ANIM_NONE)
         view.show()

      # update state
      self.current_view = view

      # back item (optional)
      if ini.get_bool('general', 'back_in_lists') == True:
         self.item_add(BackItemClass(), 'emc://back', self)
         view.items_count -= 1

      # use this for extra debug
      # print(self)

      # and finally populate the page
      url = page['url']
      cb = page['cb']
      args = page['args']
      kwargs = page['kwargs']
      cb(self, url, *args, **kwargs)

   def _input_event_cb(self, event):
      # topbar buttons
      if event == 'OK' and isinstance(gui.win.focused_object, EmcButton):
         _topbar_buttons_cb(gui.win.focused_object)
         return input_events.EVENT_BLOCK

      # pass the event to the view
      view_ret = self.current_view.input_event_cb(event)
      if view_ret == input_events.EVENT_BLOCK:
         return input_events.EVENT_BLOCK

      # always
      if event == 'BACK':
         self.back()
         return input_events.EVENT_BLOCK
      elif event == 'VIEW_LIST':
         self.change_style('List')
         return input_events.EVENT_BLOCK
      elif event == 'VIEW_POSTERGRID':
         self.change_style('PosterGrid')
         return input_events.EVENT_BLOCK
      elif event == 'VIEW_COVERGRID':
         self.change_style('CoverGrid')
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

   def _create_or_get_view(self, view_name):
      if view_name in _views:
         DBG('View exists: ' + view_name)
         return _views[view_name]
      # call the constructor of the given class style ex: ViewList()
      DBG('Create view: ' + view_name)
      _views[view_name] = eval('View' + view_name + '()')
      return _views[view_name]


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

   ### Mandatory methods, all the views must implement those functions
   def __init__(self):
      """
      This is the init founction for the view, it is called one time only
      when the view is needed for the first time. Here you must do your
      initialization stuff.
      """
      DBG('Init view: plain list')

      self._timer1 = self._timer2 = None
      self.items_count = 0;            # This is accessed from the browser

      # EXTERNAL Genlists
      self.gl1 = Genlist(gui.layout)
      gui.swallow_set('browser.list.genlist1', self.gl1)
      self.gl2 = Genlist(gui.layout)
      gui.swallow_set('browser.list.genlist2', self.gl2)
      self.current_list = self.gl1

      for gl in (self.gl1, self.gl2):
         gl.style = 'browser'
         gl.mode = ELM_LIST_COMPRESS
         gl.homogeneous = True
         gl.select_mode = ELM_OBJECT_SELECT_MODE_ALWAYS
         gl.focus_allow = False
         gl.callback_clicked_double_add(self._cb_item_selected)
         gl.callback_selected_add(self._cb_item_hilight)
         gl.callback_unselected_add(self._cb_item_unhilight)
         gl.callback_realized_add(self._cb_item_realized)

      # genlist item class
      self.itc = GenlistItemClass(item_style='default',
                                  text_get_func=self.__gl_text_get,
                                  content_get_func=self.__gl_content_get)

      # RemoteImage (poster)
      self._poster = EmcImage()
      gui.swallow_set('browser.list.poster', self._poster)

      # AutoScrolledEntry (info)
      self._ase = EmcScrolledEntry(autoscroll=True)
      gui.swallow_set('browser.list.info', self._ase)

   def page_show(self, title, anim):
      """
      This function is called everytime a new page need to be showed.
      The 'anim' param tell you direction of the browse:
         can be: ANIM_NONE, ANIM_BACK or ANIM_FORWARD
        -1 means we are going back (
         1 means forward
         0 means no previous page
      You can use the 'dir' param to perform the correct animation if needed
      """
      DBG('page show ' + str(anim))

      self.current_list.focus_allow = False

      if (anim != ANIM_NONE):
         if self.current_list == self.gl1:
            self.current_list = self.gl2
         else:
            self.current_list = self.gl1

      if anim == ANIM_FORWARD:
         gui.signal_emit('browser,list,flip_left')
      elif anim == ANIM_BACK:
         gui.signal_emit('browser,list,flip_right')

      self.current_list.clear()
      self.items_count = 0
      self.current_list.focus_allow = True

   def item_add(self, item_class, url, user_data, selected=False):
      """
      Here you must add the item to the current visible page.
      You can use the 'item_class' object to query more info about
      the item using: item_class.icon_get() .poster_get() etc..

      When an item will be selected you MUST call:
         item_class.item_selected(url, user_data)
      with the url and the data of the selected item.
      """
      DBG('item_add(%s)' % (url))
      item_data = (item_class, url, user_data)                                  # Master3 #
      it = self.current_list.item_append(self.itc, item_data)
      if selected or not self.current_list.selected_item_get():
         it.selected = True
         it.show()

      self.items_count += 1
      gui.text_set('browser.list.total',
         ngettext('%d item', '%d items', self.items_count) % (self.items_count))

   def show(self):
      """ Show the view """
      self._poster.url_set(None)
      gui.signal_emit('browser,list,show')

   def hide(self):
      """ Hide the view """
      self._clear_timers()
      gui.signal_emit('browser,list,hide')
      gui.signal_emit('browser,list,info,hide')
      self._ase.autoscroll = False
      self.gl1.focus = False
      self.gl2.focus = False
      self.gl1.focus_allow = False
      self.gl2.focus_allow = False

   def clear(self):
      """ Clear the view """
      self._clear_timers()
      self.gl1.clear()
      self.gl2.clear()
      self.items_count = 0

   def refresh(self):
      """ Refresh the view """
      # update visible items
      for item in self.current_list.realized_items_get():
         item.update()
      # also request new poster, info and backdrop
      item =  self.current_list.selected_item
      self._info_timer_cb(item.data_get())
      self._backdrop_timer_cb(item.data_get())

   def item_bring_in(self, pos='top', animated=True):
      try:
         item = self.current_list.selected_item
      except: return

      if   pos == 'top':    mode = ELM_GENLIST_ITEM_SCROLLTO_TOP
      elif pos == 'mid':    mode = ELM_GENLIST_ITEM_SCROLLTO_MIDDLE
      elif pos == 'in':     mode = ELM_GENLIST_ITEM_SCROLLTO_IN

      if animated:
         item.bring_in(mode)
      else:
         item.show(mode)

   def selected_url_get(self):
      """ return the url of the currently hilighted item """
      item = self.current_list.selected_item_get()
      if item:
         (item_class, url, user_data) = item.data_get()                         # 3 #
         return url

   def input_event_cb(self, event):
      """ Here you can manage input events for the view """
      if event == 'OK' and self.current_list.focus == True:
         item = self.current_list.selected_item
         (item_class, url, user_data) = item.data_get()                         # 3 #
         item_class.item_selected(url, user_data)
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

   ### GenList Item Class
   def __gl_text_get(self, obj, part, item_data):
      (item_class, url, user_data) = item_data                                  # 3 #
      # DBG('_text get({}, {})'.format(part, url))
      if part == 'elm.text.main':
         text = item_class.label_get(url, user_data)
      elif part == 'elm.text.end':
         text = item_class.label_end_get(url, user_data)
      else:
         text = None

      return text

   def __gl_content_get(self, obj, part, item_data):
      (item_class, url, user_data) = item_data                                  # 3 #
      if part == 'elm.swallow.icon':
         icon = item_class.icon_get(url, user_data)
         return EmcImage(icon) if icon else None
      if part == 'elm.swallow.end':
         icon = item_class.icon_end_get(url, user_data)
         return EmcImage(icon) if icon else None

   ### GenList Callbacks
   def _cb_item_realized(self, gl, item):
      # force show/hide of icons, otherwise the genlist cache mechanism will
      # remember icons from previus usage of the item
      # TODO: this is probably no more needed (fixed in elm)
      item.signal_emit('icon,show' if item.part_content_get('elm.swallow.icon') \
                       else 'icon,hide', 'emc')
      item.signal_emit('end,show' if item.part_content_get('elm.swallow.end') \
                       else 'end,hide', 'emc')
      # give focus if the item is selected
      if item.selected:
         item.focus = True

   def _cb_item_selected(self, gl, item):
      (item_class, url, user_data) = item.data_get()                            # 3 #
      item_class.item_selected(url, user_data)

   def _cb_item_hilight(self, gl, item):
      self._clear_timers()
      self._timer1 = ecore.timer_add(0.5, self._info_timer_cb, item.data_get())
      self._timer2 = ecore.timer_add(1.0, self._backdrop_timer_cb, item.data_get())

   def _cb_item_unhilight(self, gl, item):
      pass

   def _info_timer_cb(self, item_data):
      (item_class, url, user_data) = item_data                                  # 3 #

      # Fill the textblock with item info info
      text = item_class.info_get(url, user_data)
      if text:
         self._ase.text_set(text)
         self._ase.autoscroll = True
         gui.signal_emit('browser,list,info,show')
      else:
         self._ase.autoscroll = False
         gui.signal_emit('browser,list,info,hide')

      # Fill the big image with the poster (or cover if poster not available)
      if isinstance(item_class, (BackItemClass, FolderItemClass)):
         self._poster.url_set(None)
      else:
         image = item_class.poster_get(url, user_data) or \
                 item_class.cover_get(url, user_data)
         self._poster.url_set(image)

      self._timer1 = None
      return ecore.ECORE_CALLBACK_CANCEL

   def _backdrop_timer_cb(self, item_data):
      (item_class, url, user_data) = item_data                                  # 3 #

      # Ask for the item fanart
      fanart = item_class.fanart_get(url, user_data)
      if fanart: gui.background_set(fanart)

      self._timer2 = None
      return ecore.ECORE_CALLBACK_CANCEL

   def _clear_timers(self):
      if self._timer1:
         self._timer1.delete()
         self._timer1 = None
      if self._timer2:
         self._timer2.delete()
         self._timer2 = None


################################################################################
#### PosterGrid View ###########################################################
################################################################################
class ViewPosterGrid(object):
   def __init__(self):
      """ TODO Function doc """
      DBG('Init view: ' + type(self).__name__)
      self.items_count = 0
      self._timer1 = self._timer2 = None
      self.setup_theme_hooks()

      # Gengrid
      self.itc = GengridItemClass(item_style='default',
                                  content_get_func=self.gg_content_get)
      self.gg = Gengrid(gui.win, style='browser', focus_allow=False,
                        align=(0.5, 0.0),
                        size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
      self.gg.callback_selected_add(self.gg_higlight)
      self.gg.callback_clicked_double_add(self.gg_selected)
      self.gg.callback_realized_add(self._cb_item_realized)
      gui.swallow_set(self._grid_swallow, self.gg)

      # RemoteImage (cover)
      self._big_image = EmcImage()
      gui.swallow_set(self._image_swallow, self._big_image)

      # AutoScrolledEntry (info)
      self._ase = EmcScrolledEntry(autoscroll=True)
      gui.swallow_set(self._info_swallow, self._ase)

   def setup_theme_hooks(self):
      """ setup stuff that is different between Poster and Cover views """
      self._grid_swallow =     'browser.postergrid.gengrid'
      self._info_swallow =     'browser.postergrid.info'
      self._image_swallow =    'browser.postergrid.image'
      self._total_text =       'browser.postergrid.total'
      self._signal_show =      'browser,postergrid,show'
      self._signal_hide =      'browser,postergrid,hide'
      self._signal_info_show = 'browser,postergrid,info,show'
      self._signal_info_hide = 'browser,postergrid,info,hide'

   def page_show(self, title, anim):
      self.gg.clear()
      self.items_count = 0

   def item_add(self, item_class, url, user_data, selected=False):
      item_data = (item_class, url, user_data)                                  # 3 #
      it = self.gg.item_append(self.itc, item_data)
      if selected or not self.gg.selected_item_get():
         it.selected = True
         it.show()

      self.items_count += 1
      gui.text_set(self._total_text,
         ngettext('%d item', '%d items', self.items_count) % (self.items_count))

   def show(self):
      size = ini.get_int('general', 'view_postergrid_size')
      self.gg.item_size = size, int(size * 1.5)
      gui.signal_emit(self._signal_show)
      self.gg.focus_allow = True
      self.gg.focus = True

   def hide(self):
      self._clear_timers()
      gui.signal_emit(self._signal_hide)
      gui.signal_emit(self._signal_info_hide)
      self.gg.focus = False
      self.gg.focus_allow = False

   def clear(self):
      self._clear_timers()
      self.items_count = 0
      self.gg.clear()

   def refresh(self):
      self.gg.realized_items_update()
      # also request new info and backdrop
      item =  self.gg.selected_item
      self._info_timer_cb(item.data_get())
      self._backdrop_timer_cb(item.data_get())

   def item_bring_in(self, pos='top', animated=True):
      try:
         item = self.gg.selected_item
      except: return

      if   pos == 'top': mode = ELM_GENLIST_ITEM_SCROLLTO_TOP
      elif pos == 'mid': mode = ELM_GENLIST_ITEM_SCROLLTO_MIDDLE
      elif pos == 'in':  mode = ELM_GENLIST_ITEM_SCROLLTO_IN

      if animated:
         item.bring_in(mode)
      else:
         item.show(mode)

   def selected_url_get(self):
      """ return the url of the currently hilighted item """
      item = self.gg.selected_item_get()
      if item:
         (item_class, url, user_data) = item.data_get()                         # 3 #
         return url

   def input_event_cb(self, event):
      if event == 'OK' and self.gg.focus == True:
         item = self.gg.selected_item
         (item_class, url, user_data) = item.data_get()                         # 3 #
         item_class.item_selected(url, user_data)
         return input_events.EVENT_BLOCK

      return input_events.EVENT_CONTINUE

   # gengrid model
   def gg_content_get(self, obj, part, item_data):
      (item_class, url, user_data) = item_data                                  # 3 #
      if part == 'elm.swallow.icon':
         poster = item_class.poster_get(url, user_data)
         if poster:
            return EmcImage(poster, fill_outside=True, thumb=True)
         else:
            label = item_class.label_get(url, user_data)
            label2 = item_class.label_end_get(url, user_data)
            icon = item_class.icon_get(url, user_data)
            return EmcImage('special/icon/' + label, icon=icon, label2=label2)

      if part == 'elm.swallow.end':
         icon = item_class.icon_end_get(url, user_data)
         if icon:
            return EmcImage(icon)

   # gengrid callbacks
   def gg_higlight(self, gg, item, *args, **kwargs):
      self._clear_timers()
      self._timer1 = ecore.timer_add(0.5, self._info_timer_cb, item.data_get())
      self._timer2 = ecore.timer_add(1.0, self._backdrop_timer_cb, item.data_get())

   def gg_selected(self, gg, item, *args, **kwargs):
      (item_class, url, user_data) = item.data_get()                            # 3 #
      item_class.item_selected(url, user_data)

   def _cb_item_realized(self, gg, item):
      if item.selected:
         item.focus = True

   def _info_timer_cb(self, item_data):
      (item_class, url, user_data) = item_data                                  # 3 #

      # Fill the textblock with item info
      text = item_class.info_get(url, user_data)
      if text:
         self._ase.text_set(text)
         self._ase.autoscroll = True
         gui.signal_emit(self._signal_info_show)
      else:
         self._ase.autoscroll = False
         gui.signal_emit(self._signal_info_hide)

      # Fill the big image (different between Poster and Cover views)
      if isinstance(item_class, (BackItemClass, FolderItemClass)):
         self._big_image.url_set(None)
      else:
         poster = item_class.poster_get(url, user_data)
         cover = item_class.cover_get(url, user_data)
         self.fill_the_big_image(poster, cover)

      self._timer1 = None
      return ecore.ECORE_CALLBACK_CANCEL

   def fill_the_big_image(self, poster, cover):
      self._big_image.url_set(cover or poster)

   def _backdrop_timer_cb(self, item_data):
      (item_class, url, user_data) = item_data                                  # 3 #

      # Ask for the item fanart
      fanart = item_class.fanart_get(url, user_data)
      if fanart: gui.background_set(fanart)

      self._timer2 = None
      return ecore.ECORE_CALLBACK_CANCEL

   def _clear_timers(self):
      if self._timer1:
         self._timer1.delete()
         self._timer1 = None
      if self._timer2:
         self._timer2.delete()
         self._timer2 = None


################################################################################
#### CoverGrid View ############################################################
################################################################################
class ViewCoverGrid(ViewPosterGrid):
   def setup_theme_hooks(self):
      self._grid_swallow =     'browser.covergrid.gengrid'
      self._info_swallow =     'browser.covergrid.info'
      self._image_swallow =    'browser.covergrid.image'
      self._total_text =       'browser.covergrid.total'
      self._signal_show =      'browser,covergrid,show'
      self._signal_hide =      'browser,covergrid,hide'
      self._signal_info_show = 'browser,covergrid,info,show'
      self._signal_info_hide = 'browser,covergrid,info,hide'

   def show(self):
      size = ini.get_int('general', 'view_covergrid_size')
      self.gg.item_size = size, size
      gui.signal_emit(self._signal_show)
      self.gg.focus_allow = True
      self.gg.focus = True

   def fill_the_big_image(self, poster, cover):
      self._big_image.url_set(poster or cover)

   def gg_content_get(self, obj, part, item_data):
      (item_class, url, user_data) = item_data                                  # 3 #
      if part == 'elm.swallow.icon':
         cover = item_class.cover_get(url, user_data)
         if cover:
            return EmcImage(cover, fill_outside=True, thumb=True)
         else:
            label = item_class.label_get(url, user_data)
            label2 = item_class.label_end_get(url, user_data)
            icon = item_class.icon_get(url, user_data)
            return EmcImage('special/icon/' + label, icon=icon, label2=label2)

      if part == 'elm.swallow.end':
         icon = item_class.icon_end_get(url, user_data)
         if icon:
            return EmcImage(icon)
