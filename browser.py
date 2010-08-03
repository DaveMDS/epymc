#!/usr/bin/env python

#~ import evas
import elementary


import gui
import mainmenu
import input

## 'just for test' keyboard support 
import ecore #TODO REMOVEME
import ecore.x #TODO REMOVEME

def _cb_keyboard(event):

    it = _pages[-1].selected_item_get()
    if not it: return True
    
    if event.key == 'Up':
        prev = it.prev_get()
        if prev:
            prev.selected_set(1)
            prev.middle_bring_in()

    elif event.key == 'Down':
        next = it.next_get()
        if next:
            next.selected_set(1)
            next.middle_bring_in()

    elif event.key in ['Return', 'space']:
        _pages[-1]._cb_item_selected(_pages[-1], it)

    elif event.key == 'BackSpace':
        back()

    return True

####   ecore.x.on_key_down_add(_cb_keyboard)
####



_views = {}  # key = view_name  value = view class instance


class EmcBrowser(object):
    """
    This is the browser object, it is used to show various page conaining
    a list. Usually you need a single instance of this class for all your needs.
    In order you have to create an instance, add a page using the page_add()
    method and add items using item_add(). Later you can create new pages or
    use the back(), clear(), show(), hide() methods.

    TODO doc default_style and style in general
    """

    def __init__ (self, default_style = 'List'):
        print 'EmcBrowser __init__'
        self.__default_style = default_style
        self.__pages = []
        self.__is_back = False
    
    def page_add(self, url, title, style = 'List', item_selected_cb = None,
                 icon_get_cb = None, poster_get_cb = None, info_get_cb = None,
                 fanart_get_cb = None):
        """
        When you create a page you need to give at least the url and the title,
        but you should (if needed) also attach callbacks to the page.

        You can attach the following callback to a page:
        * item_selected_cb(url):
            Called when an item is selected
        * icon_get_cb(url):
            Called when a view need to show the icon of your item,
            must return the icon to use for the given url
        * poster_get_cb(url):
            Called when a view need to show the poster/cover/big_image of your
            item, must return the full path of a valid image file.
            You can also return a valid url (http://) to automatically
            download the image to a random temp file. In addition you can also
            set the destinatioon path for the give url, just use ';'.
            ex: 'http://my.url/of/the/image;/my/local/dest/path'
        * info_get_cb(url):
            Called when a view need to show the info of your item,
            must return a string with the murkupped text that describe the item
        * fanart_get_cb(url):
            Called when a view need to show the fanart of your item,
            must return the full path of a valid image file
        """
        print "Browser(%d): page add '%s' '%s'" % (len(self.__pages), title, url)
        if not style: style = self.__default_style

        if not _views.has_key(style):
            print "CREATE VIEW"
            view = ViewList() # TODO eval here
            _views[style] = view
        else:
            print 'VIEW EXISTS'
            view = _views[style]

        self.__pages.append({'view': view, 'url': url, 'title': title,
                             'item_selected_cb': item_selected_cb,
                             'icon_get_cb': icon_get_cb,
                             'poster_get_cb': poster_get_cb,
                             'info_get_cb': info_get_cb,
                             'fanart_get_cb': fanart_get_cb})


        full = ''.join([page['title'] + ' > ' for page in self.__pages])
        full = full[0:-3]

        if self.__is_back:
            view.page_show(full, -1)
            self.__is_back = False
        elif len(self.__pages) < 2:
            view.page_show(full, 0)
        else:
            view.page_show(full, 1)

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
        view = self.__pages[-1]['view']
        view.item_add(url, label, self)

    def back(self):
        """ TODO Function doc """
        self.__is_back = True
        
        if len(self.__pages) == 1:
            self.hide()
            mainmenu.show()
            return
        
        page_data = self.__pages.pop()
        print page_data

        page_data2 = self.__pages.pop()
        print page_data2

        func = page_data2['item_selected_cb']
        if func: func(page_data2['url'])

    def clear(self):
        """ TODO Function doc """
        pass #TODO implement

    def show(self):
        """ TODO Function doc """
        self.__pages[-1]['view'].show()
        input.listener_add('browser-NAME', self._input_event_cb) # TODO fix -NAME if more that one browser will be show at the same time

    def hide(self):
        """ TODO Function doc """
        input.listener_del('browser-NAME')
        self.__pages[-1]['view'].hide()

    def _input_event_cb(self, event):

        if event == "BACK":
            self.back()
            return input.EVENT_BLOCK
        
        return self.__pages[-1]['view'].input_event_cb(event)

    # Stuff for Views
    def _item_selected(self, url):
        """ TODO Function doc """
        if url.startswith("emc://"):
            if url.endswith("//back"):
                self.back()
        else:
            func = self.__pages[-1]['item_selected_cb']
            if func: func(url)

    def _poster_get(self, url):
        """ TODO Function doc """
        func = self.__pages[-1]['poster_get_cb']
        return func(url) if func else None

    def _info_get(self, url):
        """ TODO Function doc """
        func = self.__pages[-1]['info_get_cb']
        return func(url) if func else None


################################################################################
#### Cube List View #################################################################
################################################################################
class ViewList(object):

    # View Init
    def __init__(self):
        """ TODO Function doc """
        print 'BrowserList __init__'

        # flip object
        self.__flip = gui.part_get('browser/list/flip')
        self.__flip.callback_animate_done_add(self.__cb_animate_done)

        # front list
        fl = elementary.Genlist(gui._win)
        fl.callback_clicked_add(self._cb_item_selected)
        fl.callback_selected_add(self._cb_item_hilight)
        self.__flip.content_front_set(fl)
        self.__fl = fl
        self.__visible_list = fl

        # back list
        bl = elementary.Genlist(gui._win) ## TODO parent is still not clear to me.... this should be the flip object  :/
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
        gui.swallow_set('browser/list/poster', self.__im)


    # Mandatory methods
    def page_show(self, title, dir):
        """ TODO Function doc """
        gui.text_set("browser/list/page_title", title)

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
        gui.signal_emit("browser,list,show")
        self.__fl.show() #TODO why clip doesn't work??
        self.__bl.show()

    def hide(self):
        """ TODO Function doc """
        gui.signal_emit("browser,list,hide")
        self.__fl.hide() #TODO why clip doesn't work??
        self.__bl.hide()

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
        #~ ic = elementary.Icon(obj)
        #~ ic.file_set("images/logo_small.png")
        #~ ic.size_hint_aspect_set(evas.EVAS_ASPECT_CONTROL_VERTICAL, 1, 1)
        #~ return ic
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
        anchorblock = gui.part_get('browser/list/info')
        anchorblock.text_set(info if info else "")

    def __cb_animate_done(self, flip):
        if self.__visible_list == self.__fl:
            self.__bl.clear()
        else:
            self.__fl.clear()
