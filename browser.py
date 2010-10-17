#!/usr/bin/env python

import evas
import elementary

import gui
import mainmenu
import input


_views = {}  # key = view_name  value = view class instance
_style_memory = {}  # key = page url  value = style name

def DBG(msg):
   print ('BROWSER: ' + msg)
   pass

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
                  icon_get_cb = None, info_get_cb = None,
                  poster_get_cb = None, fanart_get_cb = None):

      DBG('EmcBrowser __init__')
      self.name = name
      self.default_style = default_style

      self.item_selected_cb = item_selected_cb
      self.icon_get_cb = icon_get_cb
      self.info_get_cb = info_get_cb
      self.poster_get_cb = poster_get_cb
      self.fanart_get_cb = fanart_get_cb
      
      self.pages = []
      self.current_view = None
      self.is_back = False
      self.is_refresh = False

   def page_add(self, url, title, style = None):
      """
      When you create a page you need to give at least the url and the title
      """

      # create a new page data (if not a refresh operation)
      if self.is_refresh:
         view = self.pages[-1]['view']
      else:
         # choose the style/view of the new page
         if _style_memory.has_key(url):
            style = _style_memory[url]
         # TODO search also in parent pages
         elif not style:
            style = self.default_style
         view = self._create_or_get_view(style)
         
         # record the new page info in the pages list
         self.pages.append( {'view': view, 'url': url, 'title': title} )

      # first time, we don't have a current_view, set it
      if not self.current_view:
         self.current_view = view

      # set topbar title
      full = ''.join([page['title'] + ' > ' for page in self.pages])
      full = full[0:-3]
      gui.text_set("topbar/title", full)

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

      # just for debug
      self._dump_all()

   def item_add(self, url, label):
      """
      Use this method to add an item in the current (last added) page
      Url should be (but its not mandatory) a full correct url in the form:
      file:///home/user/some/dir

      The browser object understand some special url starting with emc://
      emc://back - If you use this url the item will automatically make the
                  browser go back when selected, and no item_selected_cb
                  will be called


      """
      self.current_view.item_add(url, label, self)

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
      page_url = self.pages[-1]['url']
      _style_memory[page_url] = style

      # ask to recreate the page
      self.is_refresh = True
      parent_url = self.pages[-2]['url'] if len(self.pages) > 1 else None
      func = self.item_selected_cb
      if func: func(parent_url, page_url)

   def clear(self):
      """ TODO Function doc """
      pass #TODO implement

   def show(self):
      """ TODO Function doc """
      gui.signal_emit("topbar,show")
      self.current_view.show()
      input.listener_add('browser-' + self.name, self._input_event_cb)

   def hide(self):
      """ TODO Function doc """
      gui.signal_emit("topbar,hide")
      input.listener_del('browser-' + self.name)
      self.current_view.hide()

   def _input_event_cb(self, event):

      if event == "BACK":
         self.back()
      elif event == 'VIEW_LIST':
         self.change_style("List")
      elif event == 'VIEW_GRID':
         self.change_style("Grid")
      elif event == 'VIEW_CUBE':
         self.change_style("ListCube")
      else:
         return self.current_view.input_event_cb(event)

      return input.EVENT_BLOCK

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
      for s in _style_memory:
         DBG('style mem: %s  style: %s' % (s, _style_memory[s]));
      DBG('*' * 70)

   # Stuff for Views
   def _item_selected(self, url):
      """ TODO Function doc """
      if url.startswith("emc://"):
         if url.endswith("//back"):
            self.back()
      else:
         func = self.item_selected_cb
         if func: func(self.pages[-1]["url"], url)

   def _icon_get(self, url):
      """ TODO Function doc """
      if url.startswith('emc://'):
         if url.endswith('/back'):
            return gui.load_icon('icon/back')
        
      func = self.icon_get_cb
      if not func: return None
      icon = func(self.pages[-1]["url"], url)
      if not icon: return None
      return gui.load_icon(icon)

   def _poster_get(self, url):
      """ TODO Function doc """
      func = self.poster_get_cb
      return func(self.pages[-1]["url"], url) if func else None

   def _info_get(self, url):
      """ TODO Function doc """
      func = self.info_get_cb
      return func(self.pages[-1]["url"], url) if func else None


################################################################################
#### List View      ############################################################
################################################################################
class ViewList(object):
   """
   This is the basic view, it use a genlist to show items and have a
   poster and a short info on the right. No animation is done when
   changing page.
   This view is the reference one with all the documentation, can be
   used as a starting base for new views.
   """

   ### Mandatory methods, all the views must implement this functions
   def __init__(self):
      """
      This is the init founction for the view, it is called one time only
      when the view is needed for the first time.
      """
      DBG('Init view: plain list')

      # EXTERNAL Genlist
      self.__list = gui.part_get('browser/list/genlist')
      self.__list.style_set("browser")
      self.__list.callback_clicked_add(self._cb_item_selected)
      self.__list.callback_selected_add(self._cb_item_hilight)

      # genlist item class
      self.__itc = elementary.GenlistItemClass(item_style="default",
                                 label_get_func = self.__genlist_label_get,
                                 icon_get_func = self.__genlist_icon_get,
                                 state_get_func = self.__genlist_state_get)

      # RemoteImage (poster)
      self.__im = gui.EmcRemoteImage(gui._win)
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
      self.clear()

   def item_add(self, url, label, parent_browser):
      """
      Here you must add the item to the current visible page
      You can use the 'parent_browser' object to query more info about
      the item using: parent_browser._icon_get() _poster_get() ect..

      When an item will be selected you should call:
      parent_browser._item_selected(url) with the url of the selected item
      """
      item_data = (url, label, parent_browser)
      it = self.__list.item_append(self.__itc, item_data)
      if not self.__list.selected_item_get():
         it.selected_set(1)

   def show(self):
      """ Show the view """
      gui.signal_emit("browser,list,show")

   def hide(self):
      """ Hide the view """
      gui.signal_emit("browser,list,hide")

   def clear(self):
      """ Clear the view """
      self.__list.clear()

   def input_event_cb(self, event):
      """ Here you can manage input events for the view """

      item = self.__list.selected_item_get()
      (url, label, parent_browser) = item.data_get()

      if event == "DOWN":
         next = item.next_get()
         if next:
            next.selected_set(1)
            next.middle_bring_in()
            return input.EVENT_BLOCK

      elif event == "UP":
         prev = item.prev_get()
         if prev:
            prev.selected_set(1)
            prev.middle_bring_in()
            return input.EVENT_BLOCK

      elif event == "OK":
         parent_browser._item_selected(url)
         return input.EVENT_BLOCK

      return input.EVENT_CONTINUE

   ### GenList Item Class
   def __genlist_label_get(self, obj, part, item_data):
      (url, label, parent_browser) = item_data
      return label

   def __genlist_icon_get(self, obj, part, data):
      if part == 'elm.swallow.icon':
         (url, label, parent_browser) = data
         return parent_browser._icon_get(url)
      return None

   def __genlist_state_get(self, obj, part, item_data):
      return False

   ### GenList Callbacks
   def _cb_item_selected(self, list, item):
      (url, label, parent_browser) = item.data_get()
      parent_browser._item_selected(url)

   def _cb_item_hilight(self, list, item):
      (url, label, parent_browser) = item.data_get()

      # Ask for the item poster and show (or download) it
      poster = parent_browser._poster_get(url)
      if poster and poster.startswith("http://"):
         if poster.find(';') != -1:
            (url, dest) = poster.split(';')
            self.__im.url_set(url, dest)
         else:
            self.__im.url_set(poster)
      else:
         self.__im.file_set(poster if poster else "")

      # Fill the anchorblock with item info info 
      info = parent_browser._info_get(url)
      anchorblock = gui.part_get('browser/list/info')
      anchorblock.text_set(info if info else "")


################################################################################
#### Cube List View ############################################################
################################################################################
class ViewListCube(object):

   # View Init
   def __init__(self):
      """ TODO Function doc """
      DBG('Init view: cube list')

      # flip object
      self.__flip = gui.part_get('browser/cubelist/flip')
      self.__flip.callback_animate_done_add(self.__cb_animate_done)

      # front list
      fl = elementary.Genlist(gui._win)
      #~ fl.style_set("browser") TODO uncomment
      fl.callback_clicked_add(self._cb_item_selected)
      fl.callback_selected_add(self._cb_item_hilight)
      self.__flip.content_front_set(fl)
      self.__fl = fl
      self.__visible_list = fl

      # back list
      bl = elementary.Genlist(gui._win)
      #~ bl.style_set("browser") TODO uncomment
      bl.callback_clicked_add(self._cb_item_selected)
      bl.callback_selected_add(self._cb_item_hilight)
      self.__flip.content_back_set(bl)
      self.__bl = bl

      # genlist item class
      self.__itc = elementary.GenlistItemClass(item_style="default",
                                      label_get_func=self.__genlist_label_get,
                                      icon_get_func=self.__genlist_icon_get,
                                      state_get_func=self.__genlist_state_get)

      # RemoteImage (poster)
      self.__im = gui.EmcRemoteImage(gui._win)
      gui.swallow_set('browser/cubelist/poster', self.__im)


   # Mandatory methods
   def page_show(self, title, dir):
      """ TODO Function doc """
      DBG('page show ' + str(dir))

      if dir == 1:
         self.__flip.go(elementary.ELM_FLIP_CUBE_LEFT)
      elif dir == -1:
         self.__flip.go(elementary.ELM_FLIP_CUBE_RIGHT)
      elif dir == 0:
         pass

      if dir != 0:
         if  self.__visible_list == self.__fl:
            self.__visible_list = self.__bl
         else:
            self.__visible_list = self.__fl


   def item_add(self, url, label, parent_browser):
      """ TODO Function doc """
      list = self.__visible_list
      it = list.item_append(self.__itc, (url, label, parent_browser))
      if not list.selected_item_get():
         it.selected_set(1)

   def show(self):
      """ TODO Function doc """
      gui.signal_emit("browser,cubelist,show")
      self.__fl.show() #TODO why clip doesn't work??
      self.__bl.show()

   def hide(self):
      """ TODO Function doc """
      gui.signal_emit("browser,cubelist,hide")
      self.__fl.hide() #TODO why clip doesn't work??
      self.__bl.hide()

   def clear(self):
      """ TODO Function doc """
      self.__bl.clear()
      self.__fl.clear()


   def input_event_cb(self, event):
      """ TODO Function doc """

      item = self.__visible_list.selected_item_get()
      (url, label, parent_browser) = item.data_get()

      if event == "DOWN":
         next = item.next_get()
         if next:
            next.selected_set(1)
            next.middle_bring_in()
            return input.EVENT_BLOCK

      elif event == "UP":
         prev = item.prev_get()
         if prev:
            prev.selected_set(1)
            prev.middle_bring_in()
            return input.EVENT_BLOCK

      elif event == "OK":
         parent_browser._item_selected(url)
         return input.EVENT_BLOCK

      return input.EVENT_CONTINUE

   ### GenList Item Class
   def __genlist_label_get(self, obj, part, item_data):
      (url, label, parent_browser) = item_data
      return label

   def __genlist_icon_get(self, obj, part, data):
      if part == 'elm.swallow.icon':
         (url, label, parent_browser) = data
         return parent_browser._icon_get(url)
      return None

   def __genlist_state_get(self, obj, part, item_data):
      return False

   ### GenList Callbacks
   def _cb_item_selected(self, list, item):
      (url, label, parent_browser) = item.data_get()
      parent_browser._item_selected(url)

   def _cb_item_hilight(self, list, item):
      (url, label, parent_browser) = item.data_get()
      poster = parent_browser._poster_get(url)
      if poster and poster.startswith("http://"):
         if poster.find(';') != -1:
            (url, dest) = poster.split(';')
            self.__im.url_set(url, dest)
         else:
            self.__im.url_set(poster)
      else:
         self.__im.file_set(poster if poster else "")

      info = parent_browser._info_get(url)
      anchorblock = gui.part_get('browser/cubelist/info')
      anchorblock.text_set(info if info else "")

   def __cb_animate_done(self, flip):
      DBG('Animation DONE')
      if self.__visible_list == self.__fl:
         self.__bl.clear()
      else:
         self.__fl.clear()


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
      gg = elementary.Gengrid(gui._win)
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

   def item_add(self, url, label, parent_browser):
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
            return input.EVENT_BLOCK

      elif event == "LEFT":
         prev = item.prev_get()
         if prev:
            prev.selected_set(1)
            prev.bring_in()
            return input.EVENT_BLOCK

      elif event == "UP":
         (x, y) = item.pos_get()
         # TODO
         return input.EVENT_BLOCK

      elif event == "DOWN":
         (x, y) = item.pos_get()
         # TODO
         return input.EVENT_BLOCK

      elif event == "OK":
         parent_browser._item_selected(url)
         return input.EVENT_BLOCK

      return input.EVENT_CONTINUE

   # gengrid model
   def gg_label_get(self, obj, part, item_data):
      (url, label, parent_browser) = item_data
      return label

   def gg_icon_get(self, obj, part, data):
      if part == 'elm.swallow.icon':
         (url, label, parent_browser) = data
         return parent_browser._icon_get(url)
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
