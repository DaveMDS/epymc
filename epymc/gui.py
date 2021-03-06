#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2018 Davide Andreoli <dave@gurumeditation.it>
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

from typing import Callable, Optional

import os
import random
from datetime import datetime

from efl import evas
from efl import ecore
from efl import ecore_input
from efl import edje
from efl import elementary as elm
from efl.elementary.theme import theme_overlay_add, theme_extension_add
from efl.elementary.configuration import scale_set as elm_scale_set
from efl.elementary.configuration import scale_get as elm_scale_get
from efl.elementary.configuration import Configuration as ElmConfig

from epymc import utils, ini, events, input_events, storage
from epymc.thumbnailer import emc_thumbnailer

win: Optional['EmcWindow'] = None
layout: Optional['EmcLayout'] = None
theme_file: Optional[str] = None

_backdrop_im1: Optional[elm.Image] = None
_backdrop_im2: Optional[elm.Image] = None
_backdrop_curr: Optional[elm.Image] = None

_volume_slider: Optional['EmcSlider'] = None
_volume_hide_timer: Optional[ecore.Timer] = None
_volume_persistent: bool = False
_clock_update_timer: Optional[ecore.Timer] = None
_clock_time_str: str = ''
_clock_date_str: str = ''

_theme_generation: str = '7'

EXPAND_BOTH = evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND
EXPAND_HORIZ = evas.EVAS_HINT_EXPAND, 0.0
FILL_BOTH = evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL
FILL_HORIZ = evas.EVAS_HINT_FILL, 0.5

MESSAGE_CLOCK_TIME = 12
MESSAGE_CLOCK_DATE = 13

keyboard_layouts = {
    'en_qwerty': [_('English QWERTY'), 'qwertyuiop()', 'asdfghjkl?-+', 'zxcvbnm.,@'],
    'en_abc': [_('English ABC'), 'abcdefghi ()', 'jklmnopqr -@', 'stuvwxyz  .,'],
    'it_qwerty': [_('Italian QWERTY'), 'qwertyuiopèì', 'asdfghjklòàù', 'zxcvbnm.,@[]'],
    'it_abc': [_('Italian ABC'), 'aàbcdeèfghiì', 'jklmnoòpqr()', 'stuùvwxyz.,@'],
    'ru_qwerty': [_('Russian QWERTY'), 'йцукенгшщзхъ', 'фывапролджэ@', 'ячсмитьбюё,.'],
    'ru_abc': [_('Russian ABC'), 'абвгдеёжзийк', 'лмнопрстуфх@', 'цчшщьыъэюя,.'],
    'fi_qwerty': [_('Finnish QWERTY'), 'qwertyuiopå@', 'asdfghjklöä+', 'zxcvbnm,.-()'],
    'fi_abc': [_('Finnish ABC'), 'abcdefghijkl', 'mnopqrstuvw@', 'xyzåäö,.-+()'],
    'symbols': [_('Symbols'), '.,:;?!@#$%&^', '+-*/=~°_\'"\\|', '<>()[]{}'],
}  # MOST IMPORTANT SYMBOLS ARE:  . , @ ( )


def LOG(msg):
    print('GUI: %s' % msg)


def DBG(msg):
    # print('GUI: %s' % msg)
    pass


def DBG_FOCUS(*args):
    # print('FOCUS:', *args)
    pass  # don't forget to comment the dump_focus_tree call !!


def init():
    """ return: False=failed True=ok """
    global win, layout, theme_file
    global _backdrop_im1, _backdrop_im2, _backdrop_curr
    global _clock_update_timer
    global _volume_slider

    # get config values, setting defaults if needed
    theme_name = ini.get('general', 'theme', default_value='default')
    # evas_engine = ini.get('general', 'evas_engine', default_value='software_x11')
    evas_accelerated = ini.get('general', 'evas_accelerated', default_value='True')
    fps = ini.get('general', 'fps', default_value=30)
    scale = ini.get('general', 'scale', default_value=1.0)
    fullscreen = ini.get('general', 'fullscreen', False)
    ini.get('general', 'hide_mouse', False)
    ini.get('general', 'time_format', '%H:%M')
    ini.get('general', 'date_format', '%A %d %B')
    ini.get('general', 'keyb_layouts', 'en_abc symbols')

    # connect ecore_input key event
    ecore_input.on_key_down_add(_on_key_down)

    # elementary configuration
    conf = ElmConfig()
    conf.window_auto_focus_enable = False
    conf.window_auto_focus_animate = False
    conf.focus_highlight_enabled = False
    conf.focus_highlight_animate = False
    conf.focus_autoscroll_mode = elm.ELM_FOCUS_AUTOSCROLL_MODE_NONE
    conf.item_select_on_focus_disabled = True
    conf.focus_highlight_clip_disabled = False
    if evas_accelerated == 'True':
        conf.accel_preference = 'accel'
        LOG('Request an hardware accelerated evas engine')

    # search the theme file, or use the default one
    if os.path.isabs(theme_name) and os.path.exists(theme_name):
        theme_file = theme_name
    else:
        if not theme_name.endswith('.edj'):
            theme_name += '.edj'
        theme_file = utils.get_resource_file('themes', theme_name, 'default.edj')
        if theme_file is None:
            LOG('cannot find a working theme file, exiting...')
            return False

    # check the theme generation
    gen = edje.file_data_get(theme_file, 'theme.generation')
    if gen != _theme_generation:
        LOG('Theme "{}" not in sync with actual code base.\n'
            'Needed generation: {} - theme: {} .. aborting'
            .format(theme_file, _theme_generation, gen))
        return False

    # custom elementary theme
    set_theme_file(theme_file)

    # create the emc window
    win = EmcWindow('epymc', elm.ELM_WIN_BASIC, title=_('Emotion Media Center'))
    win.callback_delete_request_add(lambda w: ask_to_exit())
    if fullscreen == 'True':
        win.fullscreen_set(1)

    # main layout (main theme)
    layout = EmcLayout(win, name='MainLayout',
                       file=(theme_file, 'emc/main/layout'),
                       size_hint_expand=EXPAND_BOTH)
    win.resize_object_add(layout)
    layout.show()

    layout.part_text_set('mainmenu.title', _('Emotion Media Center'))

    # clock update timer
    _clock_update_timer = ecore.Timer(1.0, clock_update)

    # right click for BACK
    layout.edje.signal_callback_add("mouse,up,3", "*",
                                    (lambda o, e, s: input_events.event_emit('BACK')))

    # two Image objects for the backdrop
    _backdrop_im1 = elm.Image(win, fill_outside=True)
    _backdrop_im2 = elm.Image(win, fill_outside=True)
    swallow_set('bg.swallow.backdrop1', _backdrop_im1)
    swallow_set('bg.swallow.backdrop2', _backdrop_im2)
    _backdrop_curr = _backdrop_im2

    # volume slider
    def _volume_slider_changed_cb(slider):
        # mediaplayer imported here to avoid recursive imports
        from epymc import mediaplayer as mp
        mp.volume_set(slider.value * 100)

    _volume_slider = EmcSlider(layout, name='VolumeSlider',
                               indicator_show=False, focus_allow=False)
    swallow_set('volume.slider', _volume_slider)
    _volume_slider.callback_changed_add(_volume_slider_changed_cb)

    # click the volume icon to toggle mute
    def _mute_toggle_signal_cb(a, s, d):
        # mediaplayer imported here to avoid recursive imports
        from epymc import mediaplayer as mp
        mp.volume_mute_toggle()

    signal_cb_add('emc,mute,toggle', '', _mute_toggle_signal_cb)

    # show the main window
    win.show()
    win.scale_set(float(scale))

    # listen to events and input_events
    input_events.listener_add('gui', _input_event_cb)
    events.listener_add('gui', _event_cb)

    # set efl frames per second
    fps_set(fps)

    # an invisible label used to hide the mouse cursor and block mouse events
    r = elm.Label(win, color=(0, 0, 0, 0), cursor='blank', name='mouse_blocker',
                  focus_allow=False, repeat_events=True,
                  size_hint_expand=EXPAND_BOTH)
    r.on_mouse_move_add(lambda o, e: mouse_show())
    win.resize_object_add(r)
    win.data['mouse_blocker'] = r
    if ini.get_bool('general', 'hide_mouse'):
        mouse_hide()

    return True


def shutdown():
    events.listener_del('gui')
    input_events.listener_del('gui')
    _clock_update_timer.delete()


# ## Various externally accessible functions ###

def get_theme_info(theme):
    return {
        'name': edje.file_data_get(theme, 'theme.name') or _('Unknown'),
        'version': edje.file_data_get(theme, 'theme.version') or '',
        'author': edje.file_data_get(theme, 'theme.author') or _('Unknown'),
        'info': edje.file_data_get(theme, 'theme.info') or _('Unknown')
    }


def set_theme_file(path):
    global theme_file

    LOG('Using theme: ' + path)
    theme_overlay_add(path)  # TODO REMOVE ME!!! it's here for buttons, and others
    theme_extension_add(path)
    theme_file = path
    utils.in_use_theme_file_set(theme_file)  # ... a bit hackish :(


def load_icon(icon: str):
    """
    @icon can be a full path (if start with a '/' or
          can be a theme icon (ex: icon/folder).
    see icons.edc for all the existing icon
    """
    if icon is None:
        return None
    if isinstance(icon, evas.Object):
        return icon
    ic = elm.Icon(win)
    if icon[0] == '/':
        try:
            ic.file_set(icon)
        except RuntimeError:
            pass
    else:
        try:
            ic.file_set(theme_file, icon)
        except RuntimeError:
            pass

    ic.size_hint_aspect_set(evas.EVAS_ASPECT_CONTROL_VERTICAL, 1, 1)
    return ic


def load_image(name, path=None):
    """
    @name include the ext but not the path (es 'my_image.png')
    @name can also be a full_path or a complete url
    @path is searched if the image is not found in the theme
    @return ElmImage
    @example: load_image('my_image.png', os.path.dirname(__file__))

    DEPRECATED: use EmcImage instead !!!

    """
    DBG('Requested image: ' + str(name))
    DBG('Extra path: ' + str(path))

    # remote urls
    if name.startswith(('http://', 'https://')):
        return EmcImage(name)

    im = elm.Image(win)

    # if it's a full path just load it
    if os.path.exists(name):
        DBG('Found image:' + name)
        im.file_set(name)
        return im

    # try in main theme file (as group: image/$name)
    if edje.file_group_exists(theme_file, 'image/' + name):
        DBG('Found image in theme group: image/' + name)
        im.file_set(theme_file, 'image/' + name)
        return im

    # try in main theme file (as group: $name) (thus you can load 'icon/*')
    if edje.file_group_exists(theme_file, name):
        DBG('Found image in theme group: ' + name)
        im.file_set(theme_file, name)
        return im

    # TODO search in some system dirs

    # try in caller path
    if path:
        full = os.path.join(path, name)
        if os.path.exists(full):
            DBG('Found image in extra path: image/' + name)
            im.file_set(full)
            return im

    LOG('Cannot load image: ' + str(name))
    return im


def ask_to_exit():
    text = '<center>' + credits.replace('\n', '<br>') + '</center>'
    d = EmcDialog(title=_('credits'), style='minimal', text=text)
    d.button_add(_('Cancel'), selected_cb=lambda b: d.delete())
    # d.button_add(_('Suspend'), selected_cb=None) # TODO
    # d.button_add(_('Shutdown'), selected_cb=None) # TODO
    d.button_add(_('Exit'), selected_cb=lambda b: exit_now())
    d.autoscroll_enable(3.0, 0.0)


def exit_now():
    elm.exit()


def volume_show(hidein=0, persistent=False):
    global _volume_hide_timer, _volume_persistent

    if persistent is True:
        _volume_persistent = True
        if _volume_hide_timer:
            _volume_hide_timer.delete()
            _volume_hide_timer = None

    signal_emit('volume,show')
    _volume_slider.focus_allow = True

    if hidein > 0 and not _volume_persistent:
        if _volume_hide_timer:
            _volume_hide_timer.delete()
        _volume_hide_timer = ecore.Timer(hidein, volume_hide)


def volume_hide():
    global _volume_hide_timer, _volume_persistent
    signal_emit('volume,hide')
    _volume_hide_timer = None
    _volume_persistent = False
    _volume_slider.focus = False
    _volume_slider.focus_allow = False


def volume_set(value):
    _volume_slider.value = value


def scale_set(scale):
    elm_scale_set(scale)


def scale_get():
    return elm_scale_get()


def scale_bigger():
    scale_set(scale_get() + 0.1)


def scale_smaller():
    scale_set(scale_get() - 0.1)


def scale_reset():
    scale_set(1.0)


def background_set(image):
    global _backdrop_curr

    if image == _backdrop_curr.file[0]:
        return

    if _backdrop_curr == _backdrop_im1:
        _backdrop_curr = _backdrop_im2
        signal = 'backdrop,show,2'
    else:
        _backdrop_curr = _backdrop_im1
        signal = 'backdrop,show,1'

    try:
        _backdrop_curr.file_set(image)
        signal_emit(signal)
    except:
        pass


def fps_set(fps):
    ecore.animator_frametime_set(1.0 / float(fps))


def fullscreen_get():
    return win.fullscreen


def fullscreen_set(full):
    win.fullscreen = full


def fullscreen_toggle():
    win.fullscreen = not win.fullscreen


def win_raise():
    win.iconified = False
    win.raise_()
    win.activate()


def clock_update():
    global _clock_time_str, _clock_date_str

    dt = datetime.now()
    time_str = dt.strftime(ini.get('general', 'time_format'))
    date_str = dt.strftime(ini.get('general', 'date_format'))

    if time_str != _clock_time_str:
        layout.edje.message_send(MESSAGE_CLOCK_TIME, time_str)
        _clock_time_str = time_str

    if date_str != _clock_date_str:
        layout.edje.message_send(MESSAGE_CLOCK_DATE, date_str)
        _clock_date_str = date_str

    return ecore.ECORE_CALLBACK_RENEW


def mouse_show():
    if win.data['mouse_blocker'].visible:
        DBG("Mouse pointer show")
        win.data['mouse_blocker'].hide()


def mouse_hide():
    if ini.get_bool('general', 'hide_mouse') and \
            not win.data['mouse_blocker'].visible:
        DBG("Mouse pointer hide")
        win.data['mouse_blocker'].show()


# ## Simple edje abstraction ###

def part_get(name):
    return layout.edje_get().part_external_object_get(name)


def signal_emit(sig, src='emc'):
    layout.signal_emit(sig, src)


def signal_cb_add(emission, source, cb):
    layout.signal_callback_add(emission, source, cb)


def signal_cb_del(emission, source, cb):
    layout.signal_callback_del(emission, source, cb)


def text_set(part, text):
    layout.text_set(part, text)


def swallow_set(part, obj, delete_old=True):
    if delete_old is True:
        layout.content_set(part, obj)
        return None
    else:
        ret = layout.content_unset(part)
        layout.content_set(part, obj)
        return ret


def box_append(part, obj):
    layout.box_append(part, obj)


def box_prepend(part, obj):
    layout.box_prepend(part, obj)


def box_remove(part, obj):
    layout.box_remove(part, obj)


def box_remove_all(part, clear=True):
    layout.box_remove_all(part, clear)


# ## Internal functions ###

# This is a bit hackish, will be used by the keyb module.
# The reason is that the ecore_input event must be connected BEFORE the
# win is created, and at that point the keyb module is not yet loaded.
# So we need to connect here and pass the event to the key_down_func (that
# is setted by the keyb module)
key_down_func = None  # type: Optional[Callable]


def _on_key_down(event):
    # This is a second HACK to let the VirtualKeyboard be usable with the keyboard
    if isinstance(win.focused_object, EmcTextEntry) and event.key not in ('Up', 'Down'):
        return ecore.ECORE_CALLBACK_PASS_ON
    # hack2 end
    if key_down_func:
        return key_down_func(event)
    return ecore.ECORE_CALLBACK_DONE


# hack end

def focus_move(direction):
    DBG_FOCUS('==== FOCUS MOVE ===========================================')
    focused = win.focused_object
    DBG_FOCUS('FOCUSED:', focused)
    # win.dump_focus_tree()  # NOTE: Do not commit !!!

    # try to move all the focus managers (starting from nested one)
    manager = focused if focused.is_focus_manager else focused.parent_manager
    while manager:
        DBG_FOCUS('Try moving focus in manager:', manager)
        if manager.focus_move_internal(direction):
            return
        manager = manager.parent_manager


def _input_event_cb(event):
    focused = win.focused_object
    if event in ('UP', 'DOWN', 'LEFT', 'RIGHT'):
        focus_move(event)
    elif event == 'OK' and isinstance(focused, EmcButton):
        focused.activate()
    elif event == 'TOGGLE_FULLSCREEN':
        fullscreen_toggle()
    elif event == 'SCALE_BIGGER':
        scale_bigger()
    elif event == 'SCALE_SMALLER':
        scale_smaller()
    elif event == 'SCALE_RESET':
        scale_reset()
    else:
        return input_events.EVENT_CONTINUE

    return input_events.EVENT_BLOCK


def _event_cb(event):
    if event == 'VOLUME_CHANGED':
        # mediaplayer imported here to avoid recursive imports
        from epymc import mediaplayer as MP

        _volume_slider.step = MP.volume_step_get() / 100.0
        volume_set(MP.volume_get() / 100.0)
        signal_emit('volume,mute,' + ('on' if MP.volume_mute_get() else 'off'))
        volume_show(hidein=3)

    elif event == 'KEEP_ALIVE':
        mouse_hide()


################################################################################
class _EmcFocusable(object):
    """ Base class to be used for all focusable widgets """

    _focused_object = None
    _focus_history = []

    def __init__(self, parent, focus_allow=True, is_focus_manager=False,
                 focus_history_allow=True):
        if not isinstance(self, evas.Object):
            raise TypeError('Focusable object must be evas.Object subclass')
        if not parent and not isinstance(self, EmcWindow):
            raise TypeError('Focusable parent must be given')
        if parent and not isinstance(parent, _EmcFocusable):
            raise TypeError('Parent must be a focusable object')
        if is_focus_manager and not hasattr(self, 'focus_move_internal'):
            raise NotImplementedError('A focus manager must implement ' \
                                      'focus_move_internal()')

        self._focus_allow = focus_allow
        self._is_focus_manager = is_focus_manager
        self._history_allow = focus_history_allow

        self._focusable_children = []
        self._cbs_focused = None
        self._cbs_unfocused = None

        # fully disable elm focus handling for this object
        elm.Object.focus_allow_set(self, False)

        # build the focusable tree hierarchy
        if parent:
            parent._focusable_children.append(self)
            self.on_del_add(self._delete_cb)

    def __repr__(self):
        return '<{0} ({1}) focus_allow={2} is_manager={3}{4}{5}>'.format(
            self.__class__.__name__, self.name,
            self.focus_allow, self.is_focus_manager,
            ' NO-HISTORY' if not self._history_allow else '',
            ' FOCUSED' if self.focus else '')

    def _delete_cb(self, obj):
        self.focus = False
        self.parent._focusable_children.remove(self)
        self.focus_history_remove()

    def callback_focused_add(self, cb, *args, **kargs):
        """ Add a callback to be called on focus """
        if self._cbs_focused is None:
            self._cbs_focused = []
        self._cbs_focused.append((cb, args, kargs))

    def callback_unfocused_add(self, cb, *args, **kargs):
        """ Add a callback to be called on unfocus """
        if self._cbs_unfocused is None:
            self._cbs_unfocused = []
        self._cbs_unfocused.append((cb, args, kargs))

    def _callbacks_call(self, cb_list):
        if cb_list:
            for cb, args, kargs in cb_list:
                cb(self, *args, **kargs)

    @staticmethod
    def _get_children_recursive(obj, focusable_only, L):
        for child in obj._focusable_children:
            if not focusable_only or (child.focus_allow and not child.disabled):
                L.append(child)
            _EmcFocusable._get_children_recursive(child, focusable_only, L)
        return L

    @property
    def focusable_children(self):
        """ Flat list of all focusable children in obj tree (recursive) """
        return _EmcFocusable._get_children_recursive(self, True, [])

    @property
    def children(self):
        """ Flat list of all children in obj tree (recursive) """
        return _EmcFocusable._get_children_recursive(self, False, [])

    @property
    def focus_allow(self):
        """ Get if the object can receive the focus (bool) """
        return self._focus_allow

    @focus_allow.setter
    def focus_allow(self, allow):
        """ Set if the obj can receive the focus (bool) """
        self._focus_allow = allow
        if not allow:
            self.focus = False

    @property
    def focus_history_allow(self):
        """ Get if the object should go in focus history (bool) """
        return self._history_allow

    @focus_history_allow.setter
    def focus_history_allow(self, allow):
        """ Set if the object should go in the focus history (bool) """
        self._history_allow = allow
        if not allow:
            self.focus_history_remove()

    def focus_history_remove(self):
        """ Remove all the occurence of this object from focus history """
        while self in _EmcFocusable._focus_history:
            _EmcFocusable._focus_history.remove(self)

    @property
    def tree_focus_allow(self):
        """ Whenever at least one child is focusable (bool) """
        return len(self.focusable_children) > 0

    @tree_focus_allow.setter
    def tree_focus_allow(self, allow):
        """ Set/Unset focus_allow on the whole children tree (bool) """
        children = self.children
        for child in children:
            child._focus_allow = allow
        if not allow and self.focused_object in children:
            self.focused_object.focus = False

    @property
    def focus(self):
        """ Is this the currently focused object? (bool) """
        return _EmcFocusable._focused_object == self

    @focus.setter
    def focus(self, focus):
        """ Set/Unset the focus to this obj (bool) """
        # do nothing if not changed
        if focus == self.focus:
            return

        # cannot focus a not focusable object
        if focus and not self.focus_allow:
            raise RuntimeError('Cannot focus a non-focusable object: %s' % self)

        # un-focus currently focused object
        if focus and _EmcFocusable._focused_object:
            _EmcFocusable._focused_object.focus = False

        # focus self
        if focus is True:
            DBG_FOCUS("FOCUS SET", self)
            _EmcFocusable._focused_object = self
            self.signal_emit('emc,action,focus', 'emc')
            self._callbacks_call(self._cbs_focused)

            # TODO limit this list in some way ??????
            if self._history_allow:
                _EmcFocusable._focus_history.append(self)

        # un-focus self
        else:
            DBG_FOCUS("FOCUS UNSET", self)
            self.signal_emit('emc,action,unfocus', 'emc')
            self._callbacks_call(self._cbs_unfocused)

            # nothing is focused now, which is bad. Check again in the next loop
            _EmcFocusable._focused_object = None
            ecore.Timer(0.0, self._delayed_history_pop)

    @staticmethod
    def _delayed_history_pop():
        if _EmcFocusable._focused_object is None:
            DBG_FOCUS("FOCUS HISTORY POP !!!!!!!!!!!!!!!!!!!!!!!!!!")
            while True and _EmcFocusable._focus_history:
                obj = _EmcFocusable._focus_history.pop()
                if obj.focus_allow:
                    obj.focus = True
                    break
        return ecore.ECORE_CALLBACK_CANCEL

    @property
    def focused_object(self):
        """ The currently focused object (in the whole tree) """
        return _EmcFocusable._focused_object

    @property
    def focused_child(self):
        """ The currently focused object (only in this object tree) """
        if self.focused_object in self.focusable_children:
            return _EmcFocusable._focused_object

    @property
    def is_focus_manager(self):
        """ True If the object is a focus manager """
        return self._is_focus_manager

    @property
    def parent_manager(self):
        """ Get the first parent focus-manager object """
        obj = self
        while True:
            if isinstance(obj, EmcWindow):
                return obj
            parent = obj.parent
            if parent.is_focus_manager:
                return parent
            obj = parent

    def dump_focus_tree(self, level=0):
        """ Only used for debug purpose """
        if level == 0:
            print("\n===== FOCUS TREE FOR: %s =====" % self.__class__.__name__)

        print(("  " * level) + str(self))
        for child in self._focusable_children:
            child.dump_focus_tree(level + 1)

        if level == 0:
            print("===== TREE END ==================\n")

    @property
    def focused_geometry(self):
        """ can be overriden to provide accurate geometry (fe: items in list) """
        return self.geometry

    def focus_move(self, direction):
        """ Move the focus in the given direction (only between obj children) """

        DBG_FOCUS('==== FOCUS MOVE 2 ===========================================')
        focused = self if self.focus else self.focused_child
        manager = focused.parent_manager
        DBG_FOCUS('FOCUSED:', focused)
        DBG_FOCUS('MANAGER:', manager)

        # Search the nearest widget in the given direction
        DBG_FOCUS('Search the nearest widget in direction: %s ...' % direction)
        x, y, w, h = focused.focused_geometry
        if direction == 'LEFT':
            focus_point = (x, y + h / 2)  # left-center
        elif direction == 'RIGHT':
            focus_point = (x + w, y + h / 2)  # right-center
        elif direction == 'UP':
            focus_point = (x + w / 2, y)  # top-center
        elif direction == 'DOWN':
            focus_point = (x + w / 2, y + h)  # bottom-center
        else:
            raise RuntimeError('Unknown direction: %s' % direction)

        # those are used later to check linearity
        x1, x2 = x, x + w
        y1, y2 = y, y + h

        nearest = nearest_linear = None
        distance = distance_linear = 9999999

        for obj in manager.focusable_children:
            # ignore the current focused obj
            if obj == focused:
                continue

            # ignore objects in the wrong direction
            ox, oy = obj.center
            if direction == 'LEFT' and ox >= focus_point[0]:
                continue
            elif direction == 'RIGHT' and ox <= focus_point[0]:
                continue
            elif direction == 'UP' and oy >= focus_point[1]:
                continue
            elif direction == 'DOWN' and oy <= focus_point[1]:
                continue

            # calc the distance between the focus point and the nearest obj side
            if direction == 'LEFT':
                segment_p1, segment_p2 = obj.top_right, obj.bottom_right
            elif direction == 'RIGHT':
                segment_p1, segment_p2 = obj.top_left, obj.bottom_left
            elif direction == 'UP':
                segment_p1, segment_p2 = obj.bottom_left, obj.bottom_right
            elif direction == 'DOWN':
                segment_p1, segment_p2 = obj.top_left, obj.top_right
            else:
                raise RuntimeError('Unknown direction: %s' % direction)

            dis = utils.distance_between_point_and_segment(focus_point,
                                                           segment_p1, segment_p2)

            # remember the nearest object
            if nearest is None or dis < distance:
                distance = dis
                nearest = obj

            # also remember the "linear nearest", that have higher priority
            # (only counting obj perfectly aligned in the given direction)
            if nearest_linear is None or dis < distance_linear:
                if direction in ('UP', 'DOWN'):
                    a1, a2, b1, b2 = x1, x2, obj.left_center[0], obj.right_center[0]
                else:
                    a1, a2, b1, b2 = y1, y2, obj.top_center[1], obj.bottom_center[1]

                if (a1 <= b1 < a2 or a1 < b2 <= a2) or (b1 <= a1 and b2 >= a2):
                    distance_linear = dis
                    nearest_linear = obj

        # focus the new object if found, otherwise do nothing
        if nearest_linear is not None:
            DBG_FOCUS(r'FOUND LINEAR \o/', nearest_linear)
            nearest_linear.focus = True
            return True
        elif nearest is not None:
            DBG_FOCUS(r'FOUND \o/', nearest)
            nearest.focus = True
            return True
        else:
            DBG_FOCUS('Nothing to focus!')
            return False


class _EmcFocusableWithItems(_EmcFocusable):
    """ Common base class for EmcList, EmcGenlist and EmcGengrid """

    def __init__(self, parent,
                 select_on_focus=True,
                 focus_on_select=True,
                 **kargs):

        _EmcFocusable.__init__(self, parent, is_focus_manager=True, **kargs)
        self._select_on_focus = select_on_focus
        self._focus_on_select = focus_on_select
        self._focused_item = None

        self.callback_focused_add(self._focused_cb)
        self.callback_unfocused_add(self._unfocused_cb)
        if isinstance(self, elm.List):
            self.callback_highlighted_add(self._item_selected_cb)
        else:  # Genlist, Gengrid
            self.callback_selected_add(self._item_selected_cb)
            self.callback_realized_add(self._item_realized_cb)

    @property
    def focused_item(self):
        return self._focused_item

    @focused_item.setter
    def focused_item(self, item):
        if self._focused_item and self._focused_item != item:
            self._focused_item.signal_emit('emc,action,unfocus', 'emc')

        self._focused_item = item
        item.signal_emit('emc,action,focus', 'emc')

        if self._select_on_focus and not item.selected:
            item.selected = True

    @property
    def focused_geometry(self):
        item = self.focused_item
        if item:
            geometry = item.track_object.geometry
            item.untrack()
            return geometry
        else:
            return self.geometry

    def clear(self):
        self._focused_item = None
        super().clear()

    def _focused_cb(self, obj):
        item = self.focused_item or self.selected_item or self.first_item
        if item:
            self.focused_item = item

    def _unfocused_cb(self, obj):
        if self.focused_item:
            self.focused_item.signal_emit('emc,action,unfocus', 'emc')

    def _item_selected_cb(self, obj, item):
        if self.focus_allow and self._focus_on_select:
            if self.focused_item != item:
                self.focused_item = item
                self.focus = True

    def _item_realized_cb(self, obj, item):
        if item == self.focused_item and self.focus == True:
            item.signal_emit('emc,action,focus', 'emc')
        else:
            item.signal_emit('emc,action,unfocus', 'emc')


################################################################################
class EmcWindow(_EmcFocusable, elm.Window):
    def __init__(self, *args, **kargs):
        elm.Window.__init__(self, *args, **kargs)
        _EmcFocusable.__init__(self, parent=None, is_focus_manager=True,
                               focus_allow=False, focus_history_allow=False)

    def focus_move_internal(self, direction):
        self.focus_move(direction)
        return True


################################################################################
class EmcLayout(_EmcFocusable, elm.Layout):
    def __init__(self, parent, focus_allow=False, is_focus_manager=False,
                 focus_history_allow=True, **kargs):
        elm.Layout.__init__(self, parent, **kargs)
        _EmcFocusable.__init__(self, parent, focus_allow=focus_allow,
                               is_focus_manager=is_focus_manager,
                               focus_history_allow=focus_history_allow)

    def focus_move_internal(self, direction):
        """ Default implementation for focus managers """
        return self.focus_move(direction)


################################################################################
class EmcList(_EmcFocusableWithItems, elm.List, elm.Scrollable):
    def __init__(self, parent,
                 focus_allow=True,
                 select_on_focus=True,
                 focus_on_select=True,
                 **kargs):
        elm.List.__init__(self, parent, **kargs)
        _EmcFocusableWithItems.__init__(self, parent,
                                        focus_allow=focus_allow,
                                        select_on_focus=select_on_focus,
                                        focus_on_select=focus_on_select)

    def focus_move_internal(self, direction):
        item = self.focused_item or self.selected_item or self.first_item
        if not item:
            return False

        to_item = None
        horiz = self.horizontal
        if (horiz and direction == 'RIGHT') or (not horiz and direction == 'DOWN'):
            to_item = item.next
            while to_item and to_item.disabled:
                to_item = to_item.next
        elif (horiz and direction == 'LEFT') or (not horiz and direction == 'UP'):
            to_item = item.prev
            while to_item and to_item.disabled:
                to_item = to_item.prev
        if to_item:
            self.focused_item = to_item
            to_item.bring_in()
            return True


################################################################################
class EmcGenlist(_EmcFocusableWithItems, elm.Genlist):
    def __init__(self, parent,
                 focus_allow=True,
                 select_on_focus=True,
                 focus_on_select=True,
                 **kargs):
        elm.Genlist.__init__(self, parent, **kargs)
        _EmcFocusableWithItems.__init__(self, parent,
                                        focus_allow=focus_allow,
                                        focus_on_select=focus_on_select,
                                        select_on_focus=select_on_focus)

    def focus_move_internal(self, direction):
        item = self.focused_item or self.selected_item or self.first_item
        to_item = None

        if direction == 'DOWN':
            to_item = item.next
            while to_item and to_item.type == elm.ELM_GENLIST_ITEM_GROUP:
                to_item = to_item.next

        elif direction == 'UP':
            to_item = item.prev
            while to_item and to_item.type == elm.ELM_GENLIST_ITEM_GROUP:
                to_item = to_item.prev

        if to_item:
            self.focused_item = to_item
            to_item.bring_in(elm.ELM_GENLIST_ITEM_SCROLLTO_MIDDLE)
            return True

        return False


################################################################################
class EmcGengrid(_EmcFocusableWithItems, elm.Gengrid):
    def __init__(self, parent,
                 focus_allow=True,
                 select_on_focus=True,
                 focus_on_select=True,
                 **kargs):
        elm.Gengrid.__init__(self, parent, **kargs)
        _EmcFocusableWithItems.__init__(self, parent,
                                        focus_allow=focus_allow,
                                        select_on_focus=select_on_focus,
                                        focus_on_select=focus_on_select)

    def focus_move_internal(self, direction):
        item = self.focused_item or self.selected_item or self.first_item
        x1, y1 = item.pos
        to_item = None

        if direction in ('LEFT', 'RIGHT'):
            to_item = item.next if direction == 'RIGHT' else item.prev
            if to_item:
                x2, y2 = to_item.pos
                if y1 != y2:
                    to_item = None

        elif direction == 'DOWN':
            to_item = item
            try:
                while True:
                    to_item = to_item.next
                    x2, y2 = to_item.pos
                    # skip items on the same row of the start one
                    if y2 == y1:
                        continue
                    # skip group items
                    if to_item.disabled:
                        continue
                    # search the first item on the same col (or on the left)
                    if x2 == x1 or to_item.next.pos[1] > y2:
                        break
            except:
                if to_item != self.last_item:
                    to_item = None

        else:  # UP
            to_item = item
            try:
                while True:
                    to_item = to_item.prev
                    x2, y2 = to_item.pos
                    # skip items on the same row of the start one
                    if y2 == y1:
                        continue
                    # skip group items
                    if to_item.disabled:
                        continue
                    # search the first item on the same col (or on the left)
                    if x2 <= x1:
                        break
            except:
                to_item = None

        if to_item:
            self.focused_item = to_item
            to_item.bring_in(elm.ELM_GENLIST_ITEM_SCROLLTO_MIDDLE)
            return True

        return False


################################################################################
class EmcButton(_EmcFocusable, elm.Button):
    """ A simple wrapper around the elm Button class """

    def __init__(self, parent, label=None, icon=None, cb=None, cb_data=None,
                 toggle=False, focus_allow=True, **kargs):

        elm.Button.__init__(self, parent, style='emc', **kargs)
        _EmcFocusable.__init__(self, parent, focus_allow=focus_allow)

        self._cb = cb
        self._cb_data = cb_data
        self._is_toggle = toggle
        self._toggled = False

        self.callback_clicked_add(self.activate)
        if label: self.text_set(label)
        if icon: self.icon_set(icon)
        self.show()

    def icon_set(self, icon):
        self.content_set(load_icon(icon))

    @property
    def toggled(self):
        return self._toggled

    @toggled.setter
    def toggled(self, toggled):
        self._toggled = toggled
        if toggled:
            self.signal_emit('emc,state,toggled', 'emc')
        else:
            self.signal_emit('emc,state,untoggled', 'emc')

    def activate(self, obj=None):
        self.focus = True

        if self._is_toggle:
            self.toggled = not self._toggled
        elif obj is None:
            self.signal_emit("elm,anim,activate", "elm")

        if callable(self._cb):
            if self._cb_data is not None:
                self._cb(self, self._cb_data)
            else:
                self._cb(self)


################################################################################
class EmcSlider(_EmcFocusable, elm.Slider):
    """ Simple wrapper around the elm Slider class """

    def __init__(self, parent, focus_allow=True, **kargs):
        elm.Slider.__init__(self, parent, style='emc', **kargs)
        _EmcFocusable.__init__(self, parent, focus_allow=focus_allow,
                               is_focus_manager=True)
        self.show()

    def focus_move_internal(self, direction):
        if direction == 'RIGHT':  # TODO support vertical
            self.value += self.step
            self.callback_call('changed')
            return True

        elif direction == 'LEFT':
            self.value -= self.step
            self.callback_call('changed')
            return True

        return False


################################################################################
class EmcTextEntry(_EmcFocusable, elm.Entry):
    """ direct keyboard input works for an hack in the _on_key_down func """

    def __init__(self, parent, focus_allow=True, **kargs):
        elm.Entry.__init__(self, parent, **kargs)
        _EmcFocusable.__init__(self, parent, focus_allow=focus_allow)
        self.callback_focused_add(self._focused_cb)
        self.callback_unfocused_add(self._unfocused_cb)

    def _focused_cb(self, obj):
        elm.Object.focus_allow_set(self, True)
        elm.Object.focus_set(self, True)

    def _unfocused_cb(self, obj):
        elm.Object.focus_set(self, False)
        elm.Object.focus_allow_set(self, False)


################################################################################
class EmcMenu(_EmcFocusable, elm.Ctxpopup):
    """ Dont forget to call show() AFTER all items added """

    def __init__(self, relto=None, dismiss_on_select=True):
        self.dismiss_on_select = dismiss_on_select

        # base popup class
        elm.Ctxpopup.__init__(self, layout, style='emc_menu', direction_priority=(
            elm.ELM_CTXPOPUP_DIRECTION_DOWN, elm.ELM_CTXPOPUP_DIRECTION_UP,
            elm.ELM_CTXPOPUP_DIRECTION_RIGHT, elm.ELM_CTXPOPUP_DIRECTION_LEFT)
                              )
        _EmcFocusable.__init__(self, layout, is_focus_manager=True,
                               focus_allow=False)
        self.callback_dismissed_add(self._dismissed_cb)

        # Scrollable list as content
        self.li = EmcList(self, style='emc_menu', name='MenuList',
                          mode=elm.ELM_LIST_EXPAND)
        self.li.content_min_limit(True, False)
        self.li.callback_activated_add(self._item_activated_cb)
        self.li.on_mouse_move_add(self._mouse_move_cb)
        self.li.on_mouse_down_add(self._mouse_click_cb)
        self.content = self.li

        # adjust popup position
        if relto:
            x, y = relto.center
            self.move(x, y)

        input_events.listener_add('EmcMenu', self._input_event_cb)

    def show(self):
        # adjust list size
        win_w, win_h = win.size
        self.li.size_hint_max = (-1, win_h / 1.5)
        self.li.go()

        # show the popup
        elm.Ctxpopup.show(self)

        # auto select first (not disabled or separator) item
        if self.li.selected_item is None:
            item = self.li.first_item
            while item and item.disabled:
                item = item.next
            if item:
                item.selected = True

        # give focus to the inner list
        self.li.focus = True

    def close(self):
        self.li.focus_allow = False
        self.dismiss()

    def item_add(self, label=None, icon=None, end=None, callback=None, *args, **kargs):
        item = self.li.item_append(label, load_icon(icon), load_icon(end))
        item.data['_user_cb_data_'] = (callback, args, kargs)
        return item

    def item_separator_add(self):
        item = self.li.item_append()
        item.separator = True
        item.disabled = True
        return item

    @staticmethod
    def item_icon_set(item, icon):
        item.content_set(load_icon(icon))

    @staticmethod
    def item_icon_end_set(item, icon):
        item.part_content_set('end', load_icon(icon))

    def _dismissed_cb(self, obj):
        input_events.listener_del('EmcMenu')
        self.delete()
        del self

    def _item_activated_cb(self, obj, item):
        cb, args, kwargs = item.data['_user_cb_data_']
        if callable(cb):
            cb(self, item, *args, **kwargs)
        if self.dismiss_on_select:
            self.close()

    def _mouse_move_cb(self, obj, event):
        item, pos = self.li.at_xy_item_get(*event.position.canvas)
        if item and not item.disabled:
            item.selected = True

    def _mouse_click_cb(self, obj, event):
        self._item_activated_cb(self.li, self.li.selected_item)

    def focus_move_internal(self, direction):
        if direction in ('LEFT', 'RIGHT'):
            return True
        d = self.direction
        if (d == elm.ELM_CTXPOPUP_DIRECTION_DOWN and direction == 'UP') or \
                (d == elm.ELM_CTXPOPUP_DIRECTION_UP and direction == 'DOWN'):
            self.close()
        return True

    def _input_event_cb(self, event):
        if event == 'OK':
            self._item_activated_cb(self.li, self.li.selected_item)
            return input_events.EVENT_BLOCK
        elif event in ('BACK', 'EXIT'):
            self.close()
            return input_events.EVENT_BLOCK
        return input_events.EVENT_CONTINUE


################################################################################
class EmcImage(elm.Image):
    """ An image object with support for remote url, with optional
        saving of the downloaded image to a local destination and a simple
        cache-to-file mechanism to avoid re-downloading the image again.

       Params:
          url: The url to load the image from, can be one of:
                * a local file fullpath
                * a real remote url
                * a tuple containing (url, dest) (deprecated method ??)
                * 'icon/*' to load an icon (aspect 1:1) from the theme
                * 'image/*' to load an image from the theme
                * 'special/style/text' to create a "special" image, supported
                  styles are: 'folder', 'bd', 'cd', 'icon'
                  The text will be inserted in the image.
                * 'special/vthumb/video_url' to create a thumb of a video file
                * None to "unset" the image
          dest: Local path to save the image to. If the dest path already exists
                the image will not be downloaded, but directly loaded from dest.
                If dest is None the downloaded file will be saved in cache.
          icon: For the special style 'icon', you can here specify the icon
                to swallow inside the special image.
          label2: For the special style 'icon', you can here specify the
                  secondary label text.
    """
    _in_progress_downloads = {}  # key:url  val:[instance1, instance2, ...]

    def __init__(self, url=None, dest=None, icon=None, label2=None,
                 aspect_fixed=True, fill_outside=False, thumb=False):
        self._icon_obj = None
        self._thumb_request_id = None
        elm.Image.__init__(self, layout, aspect_fixed=aspect_fixed,
                           fill_outside=fill_outside, size_hint_expand=EXPAND_BOTH,
                           size_hint_fill=FILL_BOTH)
        self.on_del_add(self._del_cb)
        if url is not None:
            self.url_set(url, dest, icon, label2, thumb)

    def url_set(self, url, dest=None, icon=None, label2=None, thumb=False):
        # None to "unset" the image
        if url is None:
            self.file_set(theme_file, 'emc/image/null')
            return

        # url can also include dest
        if isinstance(url, tuple):
            url, dest = url

        # cancel in progress thumb
        if self._thumb_request_id is not None:
            emc_thumbnailer.cancel_request(self._thumb_request_id)
            self._thumb_request_id = None

        # a remote url ?
        if url.startswith(('http://', 'https://')):
            if dest is None:
                dest = self.cache_path_get(url)
            if os.path.exists(dest):
                self.file_set(dest)
            else:
                self._start_download(url, dest)
            return

        # do we want to use/generate a thumbnail?
        if thumb and not url.startswith(('special/', 'icon/', 'image/')):
            ret = emc_thumbnailer.generate(url, self._thumb_complete_cb)
            if isinstance(ret, str):  # thumb already exists (ret is thumb path)
                self.file_set(ret)
            elif isinstance(ret, int):  # generation started (ret is req_id)
                self._thumb_request_id = ret
                self.file_set(theme_file, 'emc/image/thumbnailing')
            else:  # failed ... this cannot really happend atm
                self.file_set(theme_file, 'emc/image/error')
            return

        # an icon from the theme ?
        if url.startswith(('icon/', 'image/')):
            self.file_set(theme_file, url)
            return

        # a video thumbnail ?
        if url.startswith('special/vthumb/'):
            ret = emc_thumbnailer.generate(url[15:], self._thumb_complete_cb,
                                           frame='vthumb')
            if isinstance(ret, str):  # thumb already exists (ret is thumb path)
                self.file_set(ret)
            elif isinstance(ret, int):  # generation started (ret is req_id)
                self._thumb_request_id = ret
                self.file_set(theme_file, 'emc/image/thumbnailing')
            else:  # failed ... this cannot really happend atm
                self.file_set(theme_file, 'emc/image/error')
            return

        # a special image ?
        if url.startswith('special/'):
            _, style, text = url.split('/', maxsplit=2)
            self.file_set(theme_file, 'emc/image/' + style)
            obj = self.object
            obj.part_text_set('emc.text', text)
            if icon:
                self._icon_obj = EmcImage(icon)
                obj.part_swallow('emc.icon', self._icon_obj)
            if label2:
                obj.part_text_set('emc.text2', label2)
            return

        # a local path ?
        if os.path.exists(url):
            self.file_set(url)
            if self.animated_available:
                self.animated = True
                self.animated_play = True
            return

    def cache_path_get(self, url):
        fname = utils.md5(url) + '.jpg'  # TODO fix extension !
        return os.path.join(utils.user_cache_dir, 'remotes', fname[:2], fname)

    def _thumb_complete_cb(self, status, file, thumb):
        self._thumb_request_id = None
        if self.is_deleted():
            return
        if status is True:
            self.file_set(thumb)
        else:
            self.file_set(theme_file, 'emc/image/error')

    def _start_download(self, url, dest):
        # already downloading the same url ?
        if dest in EmcImage._in_progress_downloads:
            # append ourself in the list of in-progress for this url
            EmcImage._in_progress_downloads[dest].append(self)
            self.file_set(theme_file, 'emc/image/downloading')
            return

        # or start a real download
        dest_tmp = '{}.temp{}'.format(dest, random.randint(100000, 999999))
        try:
            utils.download_url_async(url, dest_tmp, urlencode=False,
                                     complete_cb=self._download_complete_cb)
        except:
            self.file_set(theme_file, 'emc/image/error')
        else:
            # create a new list of in-progress for this url
            EmcImage._in_progress_downloads[dest] = [self, ]
            self.file_set(theme_file, 'emc/image/downloading')

    @staticmethod
    def _download_complete_cb(dest_tmp, status):
        dest = dest_tmp[:-11]  # strip '.tempXXXXXX'
        if status == 200:
            os.rename(dest_tmp, dest)

        if dest in EmcImage._in_progress_downloads:
            for instance in EmcImage._in_progress_downloads[dest]:
                if instance.is_deleted():
                    continue
                if status == 200:
                    instance.file_set(dest)
                else:
                    instance.file_set(theme_file, 'emc/image/error')

            # remove the whole in-progress list for this url
            del EmcImage._in_progress_downloads[dest]

    def _del_cb(self, obj):
        if self._icon_obj:
            self._icon_obj.delete()
            self._icon_obj = None

        if self._thumb_request_id is not None:
            emc_thumbnailer.cancel_request(self._thumb_request_id)
            self._thumb_request_id = None


################################################################################
class EmcDialog(EmcLayout):
    """ TODO doc this
    style can be 'panel' or 'minimal'

    you can also apply special style that perform specific task:
       'info', 'error', 'warning', 'yesno', 'cancel', 'progress',
       'list', 'image_list_horiz', 'image_list_vert',
       'buffering'
    """

    minimal_styles = ['info', 'error', 'warning', 'yesno', 'cancel', 'progress']
    dialogs_counter = 0

    def __init__(self, title=None, text=None, content=None, spinner=False,
                 style='panel', done_cb=None, canc_cb=None, user_data=None):

        # load the right edje object
        if style in EmcDialog.minimal_styles or style == 'minimal':
            group = 'emc/dialog/minimal'
        elif style == 'buffering':
            group = 'emc/dialog/buffering'
        else:
            group = 'emc/dialog/panel'
        EmcLayout.__init__(self, layout, file=(theme_file, group),
                           focus_allow=True, is_focus_manager=True,
                           size_hint_align=FILL_BOTH,
                           size_hint_weight=EXPAND_BOTH)
        self.signal_callback_add('emc,dialog,close', '', self._close_pressed)
        self.signal_callback_add('emc,dialog,hide,done', '',
                                 (lambda a, s, d: self._delete_real()))
        self.signal_callback_add('emc,dialog,show,done', '',
                                 (lambda a, s, d: None))

        # put the dialog in the dialogs box of the main edje obj,
        # this way we only manage one edje and don't have stacking problems.
        # otherwise dialogs will stole the mouse events.
        box_append('dialogs.box.stack', self)

        EmcDialog.dialogs_counter += 1
        self._name = 'Dialog-' + str(EmcDialog.dialogs_counter)
        self._content = content
        self._done_cb = done_cb
        self._canc_cb = canc_cb
        self._user_data = user_data
        self._list = None
        self._textentry = None
        self._buttons = []

        # give focus to the dialog itself (for dialogs without any focusable)
        if style != 'buffering':
            self.focus = True

        # title
        if title is None:
            self.signal_emit('emc,dialog,title,hide', 'emc')
        else:
            self.part_text_set('emc.text.title', title)
            self.signal_emit('emc,dialog,title,show', 'emc')

        # vbox
        if style != 'buffering':
            self._vbox = elm.Box(self, horizontal=False, size_hint_align=FILL_HORIZ,
                                 size_hint_weight=EXPAND_HORIZ)
            self._vbox.show()
            self.content_set('emc.swallow.content', self._vbox)

        # if both text and content given then put them side by side
        if text and content:
            hbox = elm.Box(self, horizontal=True, size_hint_align=FILL_BOTH,
                           size_hint_weight=EXPAND_BOTH)
            hbox.show()
            self._vbox.pack_end(hbox)

        # text entry
        if text is not None:
            self._textentry = EmcScrolledEntry(parent=self, text=text,
                                               size_hint_weight=EXPAND_BOTH,
                                               size_hint_align=FILL_BOTH)
            self._textentry.show()

            if content:
                hbox.pack_end(self._textentry)
            else:
                self._vbox.pack_end(self._textentry)

        # user content
        if content is not None:
            frame = elm.Frame(self, style='pad_small', size_hint_align=FILL_BOTH,
                              size_hint_weight=EXPAND_BOTH, content=content)
            frame.show()
            if text is not None:
                hbox.pack_start(frame)
            else:
                self._vbox.pack_end(frame)

        # automatic list
        if style in ['list', 'image_list_horiz', 'image_list_vert']:
            self._list = EmcList(self, focus_allow=False,
                                 size_hint_align=FILL_BOTH, size_hint_weight=EXPAND_BOTH,
                                 horizontal=True if style == 'image_list_horiz' else False,
                                 style='dialog' if style == 'list' else 'image_list')
            self._list.callback_activated_add(self._list_item_activated_cb)
            self._list.show()
            self._vbox.pack_end(self._list)

        # spinner
        if spinner:
            self._spinner = elm.Progressbar(self, style='wheel', pulse_mode=True)
            self._spinner.pulse(True)
            self._spinner.show()
            self._vbox.pack_end(self._spinner)

        # set minimal styles + automatic title
        if style in EmcDialog.minimal_styles:
            self.signal_emit('emc,dialog,%s,set' % style, 'emc')
            if title is None:
                self.part_text_set('emc.text.title', style)
                self.signal_emit('emc,dialog,title,show', 'emc')

        # buttons
        if style in ('info', 'error', 'warning'):
            self.button_add(_('Ok'), lambda btn: self.delete())

        if style == 'yesno':
            if self._canc_cb:
                self.button_add(_('No'), lambda btn: self._canc_cb(self))
            else:
                self.button_add(_('No'), lambda btn: self.delete())

            if self._done_cb:
                self.button_add(_('Yes'), lambda btn: self._done_cb(self))
            else:
                self.button_add(_('Yes'), lambda btn: self.delete())

        if style == 'cancel':
            if canc_cb:
                self.button_add(_('Cancel'), lambda btn: self._canc_cb(self))
            else:
                self.button_add(_('Cancel'), lambda btn: self.delete())

        # listen for input events (not for the buffering dialog)
        if style != 'buffering':
            input_events.listener_add(self._name, self._input_event_cb)

        # show
        self.show()
        self.signal_emit('emc,dialog,show', 'emc')

    @staticmethod
    def activate():
        print('DEPRECATED EmcDialog.activate()')

    def delete(self):
        input_events.listener_del(self._name)
        self.signal_emit('emc,dialog,hide', 'emc')
        self.tree_focus_allow = False
        self.focus_allow = False
        for b in self._buttons:
            b.disabled = True

    def _delete_real(self):
        if self._textentry:
            self._textentry.delete()
        for b in self._buttons:
            b.delete()
        content = self.content_unset('emc.swallow.content')
        if content:
            content.delete()
        box_remove('dialogs.box.stack', self)
        elm.Layout.delete(self)
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

    def button_add(self, label, selected_cb=None, cb_data=None, icon=None, default=False):
        b = EmcButton(self, label, icon, selected_cb, cb_data)
        self.box_prepend('emc.box.buttons', b)
        self._buttons.append(b)
        if len(self._buttons) == 1:
            self.signal_emit('emc,dialog,buttons,show', 'emc')
            b.focus = True
        if default is True:
            b.focus = True
        return b

    def buttons_clear(self):
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
        if self._textentry:
            self._textentry.text_set(text)

    def text_get(self):
        return self._textentry.text_get()

    def text_append(self, text):
        self._textentry.text_set(self._textentry.text_get() + text)

    def list_item_append(self, label, icon=None, end=None, *args, **kwargs):
        if self._list:
            if isinstance(end, str) and end.startswith('text/'):
                end = elm.Label(self, style='dia_list', text=end[5:])
            it = self._list.item_append(label, load_icon(icon), load_icon(end), None)
            it.data['_user_item_data_'] = (args, kwargs)
            if not self._list.selected_item_get():
                it.selected = True
            return it

    def list_go(self):
        self._list.go()

    def list_clear(self):
        self._list.clear()

    def list_item_selected_get(self):
        if self._list:
            return self._list.selected_item_get()

    @staticmethod
    def list_item_icon_set(it, icon, end=False):
        it.part_content_set('end' if end else 'icon', load_icon(icon))

    def _list_item_activated_cb(self, li, it):
        if self._done_cb:
            args, kwargs = it.data['_user_item_data_']
            self._done_cb(self, *args, **kwargs)
        else:
            self.delete()

    def spinner_start(self):
        self._spinner.show()
        self._spinner.pulse(True)

    def spinner_stop(self):
        self._spinner.pulse(False)
        self._spinner.hide()

    def progress_set(self, val):
        self.edje.part_external_object_get('emc.dialog.progress').value_set(val)

    def autoscroll_enable(self, speed_scale=1.0, start_delay=3.0):
        self._textentry.autoscroll_start_delay = start_delay
        self._textentry.autoscroll_speed_scale = speed_scale
        self._textentry.autoscroll = True

    def focus_move_internal(self, direction):
        # try to move between list items
        if self._list or isinstance(self._content, (EmcList, EmcGenlist)):
            li = self._list or self._content
            if li.focus_move_internal(direction):
                return True

        # try to scroll the text entry
        if self._textentry:
            if direction == 'UP':
                self._textentry.scroll_by(0, -100)
            if direction == 'DOWN':
                self._textentry.scroll_by(0, +100)

        # try to move between dialog widgets
        self.focus_move(direction)

        # never let the focus goes out of the dialog
        return True

    def _input_event_cb(self, event):

        if not self.visible:
            return input_events.EVENT_CONTINUE

        if event in ['BACK', 'EXIT']:
            if self._canc_cb:
                self._canc_cb(self)
            else:
                self.delete()
            return input_events.EVENT_BLOCK

        if event == 'OK':
            if isinstance(self.focused_object, EmcButton):
                self.focused_object.activate()

            elif self._done_cb:
                if self._list:
                    it = self._list.selected_item
                    self._list_item_activated_cb(self._list, it)
                else:
                    self._done_cb(self)

            else:
                self.delete()

            return input_events.EVENT_BLOCK

        return input_events.EVENT_CONTINUE


################################################################################
class EmcNotify(edje.Edje):
    """ TODO doc this"""

    def __init__(self, text, icon='icon/star', hidein=5.0, close_cb=None):
        self.timer = None
        self.close_cb = close_cb

        edje.Edje.__init__(self, layout.evas, file=theme_file,
                           group='emc/notify/default')
        self.part_text_set('emc.text.caption', text)
        self._icon = load_image(icon)
        self.part_swallow('emc.swallow.icon', self._icon)
        box_append('notify.box.stack', self)

        if hidein > 0.0:
            self.hidein(hidein)

        self.show()

    def hidein(self, hidein):
        if self.timer:
            self.timer.delete()
        self.timer = ecore.Timer(hidein, self._hide_timer_cb)

    def _hide_timer_cb(self):
        box_remove('notify.box.stack', self)
        self._icon.delete()
        self.delete()
        if callable(self.close_cb):
            self.close_cb()
        return ecore.ECORE_CALLBACK_CANCEL

    def close(self):
        if self.timer:
            self.timer.delete()
        self._hide_timer_cb()

    def text_set(self, text):
        self.part_text_set('emc.text.caption', text)


################################################################################
class EmcSlideshow(elm.Slideshow):
    """ Fullscreen slideshow widget, with controls.

    Params:
       url: The folder to show. If it is a file than all the files in the
            parent folder will be show, starting from the given file.
    """

    def __init__(self, url, delay=4, show_controls=False, on_del=None):
        # private stuff
        self._itc = elm.SlideshowItemClass(self._item_get_func, self._item_del_func)
        self._timeout = delay
        self._on_del = on_del
        self._first_file = None
        self._controls_visible = False
        self._show_controls_on_start = show_controls
        self._num_images = 0
        self._folder = utils.url2path(url)
        if not os.path.isdir(self._folder):
            self._folder, self._first_file = os.path.split(self._folder)

        # swallow our layout in the main layout
        self._ly = EmcLayout(layout, file=(theme_file, 'emc/slideshow/default'))
        swallow_set('slideshow.swallow', self._ly)

        # swallow the slideshow widget in our layout
        elm.Slideshow.__init__(self, self._ly, loop=True, transition='fade',
                               focus_allow=False)
        self.callback_changed_add(self._photo_changed_cb)
        self._ly.content_set('slideshow.swallow', self)
        self._ly.signal_callback_add('emc,show,done', '', self._show_done_signal_cb)
        self._ly.signal_callback_add('emc,hide,done', '', self._hide_done_signal_cb)
        self._ly.signal_callback_add('mouse,down,1', 'slideshow.swallow', self._click_signal_cb)
        self._ly.signal_emit('show', 'emc')

        # fill the controls bar with buttons
        bt = EmcButton(self._ly, icon='icon/prev',
                       cb=lambda b: self.previous())
        self._ly.box_append('controls.btn_box', bt)

        bt = EmcButton(self._ly, icon='icon/pause',
                       cb=lambda b: self.pause_toggle())
        self._ly.box_append('controls.btn_box', bt)
        self._pause_btn = bt

        bt = EmcButton(self._ly, icon='icon/next',
                       cb=lambda b: self.next())
        self._ly.box_append('controls.btn_box', bt)

        # fill the slideshow widget
        self._populate()

        # listen to emc input events
        input_events.listener_add('EmcSlideShow', self._input_event_cb)

        # steal the focus
        self._pause_btn.focus = True

    def delete(self):
        self.pause()
        input_events.listener_del('EmcSlideShow')
        self._ly.signal_emit('hide', 'emc')
        self._ly.signal_emit('controls,hide', 'emc')
        if callable(self._on_del):
            self._on_del()

    def _delete_real(self):
        elm.Slideshow.delete(self)
        self._ly.delete()

    def pause(self):
        self.timeout = 0
        self._pause_btn.icon_set('icon/play')

    def unpause(self):
        self.timeout = self._timeout
        self._pause_btn.icon_set('icon/pause')

    def pause_toggle(self):
        self.unpause() if self.timeout == 0 else self.pause()

    def controls_show(self):
        self._ly.signal_emit('controls,show', 'emc')
        self._controls_visible = True

    def controls_hide(self):
        self._ly.signal_emit('controls,hide', 'emc')
        self._controls_visible = False

    def controls_toggle(self):
        self.controls_hide() if self._controls_visible else self.controls_show()

    # edje signal callbacks
    def _click_signal_cb(self, obj, signal, src):
        self.controls_toggle()

    def _show_done_signal_cb(self, obj, signal, src):
        self.unpause()
        if self._show_controls_on_start:
            self.controls_show()

    def _hide_done_signal_cb(self, obj, signal, src):
        self._delete_real()

    # slideshow widget smart callbacks
    def _photo_changed_cb(self, obj, item):
        num, fname = item.data
        self._ly.text_set('controls.text',
                          _('Image {0} of {1}').format(num, self._num_images))

    # internals
    def _populate(self):
        num = 1
        items = []
        for fname in utils.natural_sort(os.listdir(self._folder)):
            name, ext = os.path.splitext(fname)
            if fname[0] != '.' and ext.lower() in utils.supported_images:
                item_data = (num, fname)
                items.append(item_data)
                num += 1
        self._num_images = num

        for item_data in items:
            it = self.item_add(self._itc, item_data)
            if item_data[1] == self._first_file:
                it.show()

    # slideshow items class
    def _item_get_func(self, obj, item_data):
        num, fname = item_data
        fullpath = os.path.join(self._folder, fname)
        img = elm.Image(self, file=fullpath)
        return img

    @staticmethod
    def _item_del_func(obj, item_data):
        obj.delete()

    # emc events
    def _input_event_cb(self, event):

        if self._controls_visible:
            if event == 'BACK':
                self.controls_hide()
                return input_events.EVENT_BLOCK

        else:
            if event == 'RIGHT':
                self.next()
                return input_events.EVENT_BLOCK

            elif event == 'LEFT':
                self.previous()
                return input_events.EVENT_BLOCK

            elif event == 'OK':
                self.controls_show()
                return input_events.EVENT_BLOCK

            elif event == 'BACK':
                self.delete()
                return input_events.EVENT_BLOCK

        if event == 'EXIT':
            self.delete()
            return input_events.EVENT_BLOCK

        elif event == 'TOGGLE_PAUSE':
            self.pause_toggle()
            return input_events.EVENT_BLOCK

        return input_events.EVENT_CONTINUE


################################################################################
class EmcFolderSelector(EmcDialog):
    """
    Open a dialog that allow the user to choose a path on the filesystem.

    Args:
       title:
          The (optional) dialog title.
       done_cb:
          The (mandatory) function to call when the selection is done.
          Signature: func(path, **kargs)
       **kargs:
          Any other keyword arguments will be passed back in the done_cd func
    """

    def __init__(self, title=_('Source Selector'), done_cb=None, **kargs):
        self._user_cb = done_cb
        self._user_kargs = kargs

        EmcDialog.__init__(self, title, style='list', done_cb=self._btn_browse_cb)
        self.button_add(_('Select'), self._btn_select_cb)
        self.button_add(_('Browse'), self._btn_browse_cb, default=True)

        self.populate_devices()

    def populate_devices(self):
        self.list_clear()

        # other storage devices
        for dev in storage.list_devices():
            if dev.is_mounted:
                it = self.list_item_append(dev.label, dev.icon)
                it.data['root'] = it.data['path'] = dev.mount_point

        self.list_go()

    def populate_folder(self, root, folder):
        if folder == '':  # back in '/'
            self.populate_devices()
            return

        try:
            folders = os.listdir(folder)
        except PermissionError:
            EmcDialog(style='error', text=_('Permission denied'))
            return

        self.list_clear()

        # back item
        parent = os.path.normpath(os.path.join(folder, '..'))
        it = self.list_item_append(_('Back'), 'icon/back')
        it.data['root'] = root
        it.data['path'] = parent if parent != folder else ''  # back in '/'

        # folders
        for fname in utils.natural_sort(folders):
            fullpath = os.path.join(folder, fname)
            if fname[0] != '.' and os.path.isdir(fullpath):
                it = self.list_item_append(fname, 'icon/folder')
                it.data['root'] = root
                it.data['path'] = fullpath

        self.list_go()

    def _btn_browse_cb(self, btn):
        it = self.list_item_selected_get()
        if len(it.data['path']) < len(it.data['root']):
            self.populate_devices()
        else:
            self.populate_folder(it.data['root'], it.data['path'])

    def _btn_select_cb(self, btn):
        path = self.list_item_selected_get().data['path']
        if path and callable(self._user_cb):
            self._user_cb('file://' + path, **self._user_kargs)
        self.delete()


################################################################################
class EmcSourcesManager(EmcDialog):
    """ Open a dialog that allow the user to manage (add/remove) source
    folders. The manager automatically get the folders list from config file,
    using the group passed in the contructor and the 'folders' config item.
    The config item is also automatically updated when finished.

    Args:
       conf_group:
          The name of the config section to read the folders list from.
       title:
          Optional title for the dialog.
       done_cb:
          Function called when the user press the 'done' button.
          Signature: cb(new_folders_list)
    """

    def __init__(self, conf_group, title=_('Sources Manager'), done_cb=None):
        EmcDialog.__init__(self, title, style='list')
        self.button_add(_('Done'), icon='icon/ok',
                        selected_cb=self._cb_btn_done)
        self.button_add(_('Add'), icon='icon/plus',
                        selected_cb=self._cb_btn_add)
        self.button_add(_('Remove'), icon='icon/minus',
                        selected_cb=self._cb_btn_remove)
        self._sources = ini.get_string_list(conf_group, 'folders', ';')
        self._conf_group = conf_group
        self._done_cb = done_cb
        self._populate()

    def _populate(self):
        self.list_clear()
        for src in self._sources:
            self.list_item_append(src, 'icon/folder')
        self.list_go()

    def _cb_btn_add(self, btn):
        EmcFolderSelector(title=_('Choose a new source'), done_cb=self._cb_selected)

    def _cb_btn_remove(self, btn):
        it = self.list_item_selected_get()
        if it and it.text in self._sources:
            self._sources.remove(it.text)
            self._populate()

    def _cb_selected(self, path):
        if path not in self._sources:
            self._sources.append(path)
            self._populate()

    def _cb_btn_done(self, btn):
        ini.set_string_list(self._conf_group, 'folders', self._sources, ';')
        if callable(self._done_cb):
            self._done_cb(self._sources)
        self.delete()


################################################################################
class EmcTagsManager(EmcDialog):
    def __init__(self, tags_db, done_cb=None):
        EmcDialog.__init__(self, _('Tags manager'), style='list',
                           done_cb=self._btn_rename_cb, canc_cb=self._close_cb)
        self.button_add(_('Done'), icon='icon/ok',
                        selected_cb=self._close_cb)
        self.button_add(_('Add'), icon='icon/plus',
                        selected_cb=self._btn_add_cb)
        self.button_add(_('Remove'), icon='icon/minus',
                        selected_cb=self._btn_remove_cb)
        self.button_add(_('Rename'), icon=None,  # TODO find a decent icon
                        selected_cb=self._btn_rename_cb)
        self._tags_db = tags_db
        self._tags_done_cb = done_cb
        self._populate()

    def _populate(self):
        self.list_clear()
        for tag in sorted(self._tags_db.keys()):
            count = len(self._tags_db.get_data(tag))
            txt = ngettext('{} item', '{} items', count).format(count)
            self.list_item_append(tag, 'icon/tag', 'text/' + txt)
        self.list_go()

    def _close_cb(self, *args):
        if callable(self._tags_done_cb):
            self._tags_done_cb()
        self.delete()

    def _btn_add_cb(self, btn):
        EmcVKeyboard(title=_('Type a name for the new tag'),
                     accept_cb=self._add_vkeyb_cb)

    def _add_vkeyb_cb(self, vkeyb, text):
        if not text or '/' in text:
            EmcDialog(style='error', text=_('Invalid tag name'))
            return False  # do not close the keyb

        if not text or text in self._tags_db.keys():
            EmcDialog(style='error', text=_('Tag already exists'))
            return False  # do not close the keyb
        self._tags_db.set_data(text, [])
        self._populate()

    def _btn_remove_cb(self, btn):
        try:
            tag_name = self.list_item_selected_get().text
        except AttributeError:  # no item selected
            return
        txt = _('Are you sure you want to delete the tag?')
        txt += '<br><b>{}</b>'.format(tag_name)
        EmcDialog(style='yesno', title=_('Warning'), text=txt,
                  done_cb=self._remove_confirmed_cb)

    def _remove_confirmed_cb(self, dia):
        tag_name = self.list_item_selected_get().text
        self._tags_db.del_data(tag_name)
        self._populate()
        dia.delete()

    def _btn_rename_cb(self, obj):
        try:
            tag_name = self.list_item_selected_get().text
        except AttributeError:  # no item selected
            return
        EmcVKeyboard(title=_('Type the new name for the tag'), text=tag_name,
                     accept_cb=self._rename_vkeyb_cb)

    def _rename_vkeyb_cb(self, vkeyb, text):
        if not text or '/' in text:
            EmcDialog(style='error', text=_('Invalid tag name'))
            return False  # do not close the keyb

        tag_name = self.list_item_selected_get().text
        if tag_name == text:
            return True  # close the keyb

        if text in self._tags_db.keys():
            EmcDialog(style='error', text=_('Tag already exists'))
            return False  # do not close the keyb

        # create a new tag with the data of the old name and delete the old tag
        data = self._tags_db.get_data(tag_name)
        self._tags_db.set_data(text, data)
        self._tags_db.del_data(tag_name)

        self._populate()


################################################################################
class EmcVKeyboard(EmcDialog):
    """ TODOC """

    def __init__(self, accept_cb=None, dismiss_cb=None,
                 title=None, text=None, user_data=None):
        """ TODOC """

        self.accept_cb = accept_cb
        self.dismiss_cb = dismiss_cb
        self.user_data = user_data
        self.buttons = list()

        # choose the correct layout
        self._available_layouts = ini.get_string_list('general', 'keyb_layouts')
        self._current_layout = self._available_layouts[0]  # TODO remember the last one used

        # table
        tb = elm.Table(layout, homogeneous=True)
        tb.show()
        self._table = tb

        # init the parent EmcDialog class
        EmcDialog.__init__(self, title=title, style='minimal', content=tb)

        # set dialog title
        self.part_text_set('emc.text.title', title or _('Insert text'))

        # entry
        self.entry = EmcTextEntry(self, style='vkeyboard', scrollable=True,
                                  single_line=True, editable=True,
                                  context_menu_disabled=True, focus_allow=True,
                                  size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.entry.callback_activated_add(self._accept_cb)
        self.entry.callback_aborted_add(self._dismiss_cb)
        if text: self.text_set(text)
        tb.pack(self.entry, 0, 0, 12, 1)
        self.entry.show()

        # numbers + backspace
        for i, c in enumerate('1234567890'):
            self._pack_btn(i, 1, 1, 1, c, cb=self._default_btn_cb)
        self._pack_btn(10, 1, 2, 1, _('ERASE'), cb=self._erase_cb)

        # characters
        self._apply_layout(self._current_layout)

        # last 2 rows
        self._pack_btn(0, 5, 4, 1, keyboard_layouts[self._current_layout][0],
                       cb=self._change_layout_cb)
        self._pack_btn(4, 5, 4, 1, _('SPACE'), cb=self._space_cb)
        self._pack_btn(8, 5, 4, 1, _('UPPERCASE'), cb=self._uppercase_cb)

        self._pack_btn(0, 6, 5, 1, _('Dismiss'), 'icon/cancel', self._dismiss_cb)
        self._pack_btn(5, 6, 1, 1, None, 'icon/arrowL',
                       lambda b: self.entry.cursor_prev())
        self._pack_btn(6, 6, 1, 1, None, 'icon/arrowR',
                       lambda b: self.entry.cursor_next())
        self._pack_btn(7, 6, 5, 1, _('Accept'), 'icon/ok', self._accept_cb)

        # catch input events
        input_events.listener_add('vkbd', self.input_event_cb)
        self.entry.focus = True

    def _pack_btn(self, x, y, w, h, label, icon=None, cb=None):
        b = EmcButton(self, label, icon, cb=cb, size_hint_align=FILL_HORIZ)
        self._table.pack(b, x, y, w, h)
        self.buttons.append(b)
        return b

    def delete(self):
        input_events.listener_del('vkbd')
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
            if self.user_data is not None:
                ret = self.accept_cb(self, self.entry.entry_get(), self.user_data)
            else:
                ret = self.accept_cb(self, self.entry.entry_get())
            if ret is False:
                return
        self.delete()

    def _default_btn_cb(self, button):
        self.entry.entry_insert(button.text)

    def _erase_cb(self, button):
        pos = self.entry.cursor_pos_get()
        if pos > 0:
            text = self.entry.text
            self.entry.text = text[:pos - 1] + text[pos:]
            self.entry.cursor_pos_set(pos - 1)

    def _space_cb(self, button):
        self.entry.entry_insert(' ')

    def _uppercase_cb(self, button):
        if self._current_layout == 'symbols':
            return

        for btn in self.buttons:
            c = btn.text_get()
            if c and len(c) == 1 and c.isalpha():
                if c.islower():
                    btn.text = c.upper()
                    button.text = _('LOWERCASE')
                else:
                    btn.text = c.lower()
                    button.text = _('UPPERCASE')
            elif c and len(c) == 1:
                if c == '(':
                    btn.text = '['
                elif c == ')':
                    btn.text = ']'
                elif c == '[':
                    btn.text = '('
                elif c == ']':
                    btn.text = ')'
                elif c == '.':
                    btn.text = ':'
                elif c == ':':
                    btn.text = '.'
                elif c == ',':
                    btn.text = ';'
                elif c == ';':
                    btn.text = ','
                elif c == '-':
                    btn.text = '_'
                elif c == '_':
                    btn.text = '-'
                elif c == '?':
                    btn.text = '!'
                elif c == '!':
                    btn.text = '?'
                elif c == '+':
                    btn.text = '*'
                elif c == '*':
                    btn.text = '+'
                elif c == '@':
                    btn.text = '/'
                elif c == '/':
                    btn.text = '@'

    def _apply_layout(self, layout):
        for j in range(2, 5):
            for i in range(12):
                old = self._table.child_get(i, j)
                if old:
                    old.delete()

        self._current_layout = layout
        for j in range(3):
            for i, c in enumerate(keyboard_layouts[self._current_layout][j + 1]):
                if c != ' ':
                    self._pack_btn(i, j + 2, 1, 1, c, cb=self._default_btn_cb)

    def _change_layout_cb(self, button):
        new_idx = self._available_layouts.index(self._current_layout) + 1
        if new_idx >= len(self._available_layouts):
            new_idx = 0
        self._apply_layout(self._available_layouts[new_idx])
        button.text = keyboard_layouts[self._current_layout][0]

    def input_event_cb(self, event):
        if event == 'EXIT':
            self._dismiss_cb(None)
            return input_events.EVENT_BLOCK

        return input_events.EVENT_CONTINUE


################################################################################
class EmcScrolledEntry(elm.Entry, elm.Scrollable):
    """ A non editable, multiline text entry, with autoscroll ability. """

    def __init__(self, parent=None, autoscroll=False, **kargs):
        self._animator = None
        self._timer = None
        self._autoscroll_amount = 0.0
        self._autoscroll_speed_scale = 1.0
        self._autoscroll_start_delay = 3.0
        self._autoscroll = autoscroll
        elm.Entry.__init__(self, parent or layout, style='scrolledentry',
                           editable=False, scrollable=True, focus_allow=False, **kargs)

    @property
    def autoscroll(self):
        return self._autoscroll

    @autoscroll.setter
    def autoscroll(self, value):
        if value != self._autoscroll:
            self._autoscroll = value
            if value is True:
                self._autoscroll_start()
            else:
                self._autoscroll_stop()

    @property
    def autoscroll_speed_scale(self):
        return self._autoscroll_speed_scale

    @autoscroll_speed_scale.setter
    def autoscroll_speed_scale(self, value):
        self._autoscroll_speed_scale = value

    @property
    def autoscroll_start_delay(self):
        return self._autoscroll_start_delay

    @autoscroll_start_delay.setter
    def autoscroll_start_delay(self, value):
        self._autoscroll_start_delay = value

    def text_set(self, text):
        elm.Entry.text_set(self, text)
        if self._autoscroll:
            self._autoscroll_stop()
            self._autoscroll_start()

    def scroll_by(self, sx=0, sy=0, animated=True):
        x, y, w, h = self.region
        if animated:
            self.region_bring_in(x + sx, y + sy, w, h)
        else:
            self.region_show(x + sx, y + sy, w, h)

    def delete(self):
        self._autoscroll_stop()
        elm.Entry.delete(self)

    def _autoscroll_start(self):
        if self._animator is None:
            self.region_show(0, 0, 10, 10)
            self._timer = ecore.Timer(self._autoscroll_start_delay,
                                      self._delayed_start)

    def _autoscroll_stop(self):
        if self._animator is not None:
            self._animator.delete()
            self._animator = None
        if self._timer is not None:
            self._timer.delete()
            self._timer = None

    def _delayed_start(self):
        self._animator = ecore.Animator(self._animator_cb)

    def _animator_cb(self):
        self._autoscroll_amount += ecore.animator_frametime_get() * 15 * \
                                   self._autoscroll_speed_scale

        # at least one pixel to scroll ?
        if self._autoscroll_amount >= 1.0:
            x, y, w, h = old_region = self.region
            # print("Animator  ", old_region, self._autoscroll_amount)

            self.region_show(0, y + int(self._autoscroll_amount), w, h)
            self._autoscroll_amount = 0.0

            # bottom reached ?
            if old_region == self.region:
                self._timer = ecore.Timer(3.0, self._autoscroll_start)
                self._animator = None
                return ecore.ECORE_CALLBACK_CANCEL

        return ecore.ECORE_CALLBACK_RENEW


################################################################################
DMAN_QUEUED = 0
DMAN_RUNNING = 1
DMAN_COMPLETED = 2
DMAN_ABORTED = 3
DMAN_PAUSED = 4


class DManItem(object):
    def __init__(self, manager, url, dest):
        self.url = url
        self.dest = dest
        self.folder, self.fname = os.path.split(dest)
        self.status = DMAN_QUEUED
        self.handler = None  # ecore.FileDownload instance
        self.manager = manager
        self.total_size = 0
        self.done_size = 0

    def start(self):
        if self.handler is not None:
            return

        DBG('************  DOWNLOAD START  ****************')
        DBG('URL: ' + self.url)
        DBG('PAT: ' + self.dest)
        self.handler = utils.download_url_async(self.url, dest=self.dest + '.part',
                                                urlencode=False,
                                                complete_cb=self._complete_cb,
                                                progress_cb=self._progress_cb)
        self.status = DMAN_RUNNING
        # notify
        txt = '<title>{}</title><br>{}'.format(_('Download started'), self.fname)
        EmcNotify(txt, icon='icon/download')

    def abort(self):
        if self.handler:
            self.status = DMAN_ABORTED
            self.handler.abort()
            self.handler = None

    def _progress_cb(self, dest, dltotal, dlnow):
        self.total_size = dltotal
        self.done_size = dlnow

    def _complete_cb(self, dest, status):
        if self.status == DMAN_ABORTED:
            return

        self.handler = None
        self.status = DMAN_COMPLETED

        # download failed ?
        if status != 200:
            txt = '<b>{}:</b><br>{}<br><br><failure>{}: {} ({})</failure>'.format(
                _('Cannot download file'), self.fname,
                _('Failure code'), status, utils.http_error_code_to_str(status))
            EmcDialog(style='error', title=_('Download failed'), text=txt)
            return

        # remove the .part suffix
        os.rename(dest, self.dest)

        # notify
        txt = '<title>{}</title><br>{}'.format(_('Download completed'), self.fname)
        EmcNotify(txt, icon='icon/download')

        # see if other (in queue) download should be started now
        self.manager._process_queue()


class DownloadManager(utils.Singleton):
    """ Manage a queue of urls to download.

    The only function you need is queue_download, the class is a singleton so
    you must use as:
    DownloadManager().queue_download(url, ...)

    """

    def __init__(self):
        if not hasattr(self, 'queue'):
            self.queue = []  # list of DManItem instances

    def queue_download(self, url, dest_name=None, dest_ext=None, dest_folder=None):
        """ Put a new url in the download queue.

        Asking the user to confirm the operation, and giving the ability to
        change destination folder and destination name.

        Args:
           url: a valid url to download.
           dest_name: suggested name for the file, without extension.
           dest_ext: extension for the file, if None it is extracted from the url.
           dest_folder: where to put the downloaded file.

        """
        # destination folder
        if dest_folder is None:
            dest_folder = ini.get('general', 'download_folder')

        # destination file extension
        if dest_ext is None:
            try:
                # try to get the file extension from the url
                if '?' in url:
                    dest_ext = url.split('?')[0].split('.')[-1]
                else:
                    dest_ext = url.split('.')[-1]
                assert 6 > len(dest_ext) > 1
            except:
                dest_ext = 'mp4'  # :/

        # destination file name
        fname = '.'.join((dest_name or 'epymc_download', dest_ext))

        # confirm dialog
        dia = EmcDialog(_('Download Manager'), text='')
        dia.data['url'] = url
        dia.data['dst_folder'] = dest_folder
        dia.data['dst_name'] = fname
        dia.button_add(_('Start download'), self._start_cb, dia)
        dia.button_add(_('Rename'), self._change_name_cb, dia)
        dia.button_add(_('Change folder'), self._change_folder_cb, dia)
        self._update_dialog_text(dia)

    # confirmation dialog stuff
    @staticmethod
    def _update_dialog_text(dia):
        text = _('File will be downloaded in the folder:<br> <b>{}</b><br>'
                 '<br>File will be named as:<br> <b>{}</b><br>'
                 '<br>You can rename the file using the <i>Rename</i> button or '
                 'change the destination folder from the main configuration.') \
            .format(dia.data['dst_folder'], dia.data['dst_name'])
        dia.text_set(text)

    def _change_name_cb(self, bt, dia):
        EmcVKeyboard(title=_('Rename download'), text=dia.data['dst_name'],
                     accept_cb=self._change_name_done_cb, user_data=dia)

    def _change_name_done_cb(self, vkeyb, text, dia):
        dia.data['dst_name'] = text
        self._update_dialog_text(dia)

    def _change_folder_cb(self, bt, dia):
        EmcFolderSelector(title=_('Change destination folder'),
                          done_cb=self._change_folder_done_cb, dia=dia)

    def _change_folder_done_cb(self, folder, dia):
        dia.data['dst_folder'] = folder.replace('file://', '')
        self._update_dialog_text(dia)

    def _start_cb(self, bt, dia):
        url = dia.data['url']
        fullpath = os.path.join(dia.data['dst_folder'], dia.data['dst_name'])
        fullpath = utils.ensure_file_not_exists(fullpath)

        # check if the given url is already in queue
        if len([i for i in self.queue if i.url == url]) > 0:
            text = _('The file %s is in the download queue yet') % dia.data['dst_name']
            EmcDialog(style='error', text=text)
            dia.delete()
            return

        # close the dialog
        dia.delete()

        # queue the download
        self.queue.append(DManItem(self, url, fullpath))
        self._process_queue()

    # process queue
    def _process_queue(self):
        # no items in queue, nothing to do
        if len(self.queue) < 1:
            return

        # respect the max_concurrent_download option
        slots = ini.get_int('general', 'max_concurrent_download')
        for item in self.queue:
            if item.status == DMAN_RUNNING:
                slots -= 1
                if slots <= 0:
                    return

        # start queued items (always respecting max_concurrent_download)
        for item in self.queue:
            if item.status == DMAN_QUEUED:
                item.start()
                slots -= 1
                if slots <= 0:
                    return

    # in progress dialog stuff
    def in_progress_show(self):
        """ Show a dialog with the operation in progress """

        if len(self.queue) < 1:
            EmcDialog(title=_('Download manager'), style='info',
                      text='No download currently in progress')
            return

        itc = elm.GenlistItemClass(item_style='default',
                                   text_get_func=self._gl_text_get)
        gl = elm.Genlist(layout, style='dman', focus_allow=False,
                         homogeneous=True, mode=elm.ELM_LIST_COMPRESS)

        self.dia = EmcDialog(title=_('Download manager'), content=gl,
                             canc_cb=self.in_progress_hide)
        self.dia.button_add(_('Close'), selected_cb=self.in_progress_hide)
        self.dia.button_add(_('Start'), selected_cb=self._dia_start_cb)
        self.dia.button_add(_('Clear completed'), selected_cb=self._dia_clear_cb)
        self.dia.button_add(_('Cancel'), selected_cb=self._dia_cancel_cb)

        for item in self.queue:
            gl.item_append(itc, item)
        gl.first_item.selected = True

        # start a timer to continuosly update the list
        self.dia_timer = ecore.Timer(1.0, self._dia_update_timer_cb, gl)

    def in_progress_hide(self, *args):
        """ dismiss the progress dialog """
        if self.dia_timer:
            self.dia_timer.delete()
            self.dia_timer = None
        if self.dia:
            self.dia.delete()
            self.dia = None

    @staticmethod
    def _gl_text_get(obj, part, item):
        if part == 'elm.text.fname':
            return item.fname
        if part == 'elm.text.folder':
            return item.folder
        if part == 'elm.text.progress':
            if item.total_size > 0:
                percent = int((item.done_size / item.total_size) * 100)
                return _('{0}% of {1}').format(percent, utils.hum_size(item.total_size))
            else:
                return _('Unknown size')
        if part == 'elm.text.status':
            if item.status == DMAN_QUEUED:
                return _('queued')
            elif item.status == DMAN_RUNNING:
                return _('running')
            elif item.status == DMAN_COMPLETED:
                return _('completed')
            elif item.status == DMAN_PAUSED:
                return _('paused')

    @staticmethod
    def _dia_update_timer_cb(gl):
        gl.realized_items_update()
        return ecore.ECORE_CALLBACK_RENEW

    def _dia_start_cb(self, btn):
        gl_item = self.dia.content_get().selected_item
        if gl_item is not None:
            gl_item.data.start()

    def _dia_cancel_cb(self, btn):
        gl_item = self.dia.content_get().selected_item
        if gl_item is None:
            return

        item = gl_item.data
        txt = '<b>{}</b><br>'.format(item.fname)
        txt += _('Are you sure you want to abort the download of the file?')
        EmcDialog(style='yesno', title=_('Delete download'), text=txt,
                  done_cb=self._dia_cancel_confirmed_cb, user_data=gl_item)

    def _dia_cancel_confirmed_cb(self, dia):
        gl_item = dia.data_get()
        item = gl_item.data
        dia.delete()

        item.abort()
        self.queue.remove(item)
        del item

        to_sel = gl_item.next or gl_item.prev
        if to_sel:
            to_sel.selected = True
        gl_item.delete()

        self._process_queue()

    def _dia_clear_cb(self, btn):
        gl = self.dia.content_get()
        for gl_item in gl:
            item = gl_item.data
            if item.status == DMAN_COMPLETED:
                gl_item.delete()
                self.queue.remove(item)
                del item
        if gl.selected_item is None and gl.first_item:
            gl.first_item.selected = True


################################################################################
credits = """







<info>code</>
DAVIDE ANDREOLI

<info>design</>
DAVIDE ANDREOLI

<info>i18n</>
Wolfgang Morawetz - DE
Kai Huuhko - FI
Davide Andreoli - IT
Niko2040 - RU

<info>python efl team</>
BORIS FAURE
BRUNO DILLY
DAVIDE ANDREOLI
FABIANO FIDÊNCIO
GUSTAVO SVERZUT BARBIERI
JOOST ALBERS
KAI HUUHKO
SIMON BUSCH
TIAGO FALCÃO

<info>online sources</>
themoviedb.org
musicbrainz.org
opensubtitles.org
progettoemma.net
freeroms.com
southpark.cc.com
youtube.com
vimeo.com
zapiks.com

<info>efl team</>
ADAM SIMPKINS
AHARON HILLEL
ALBIN TONNERRE
ALEXANDRE BECOULET
ALEXEY YAKOVENKO
ANDRE DIEB
ANDREW ELCOCK
ARNAUD DE TURCKHEIM
BERNHARD NEMEC
BORIS FAURE
BLUEZERY
BRETT NASH
BRIAN MATTERN
BRUNO DILLY
CARSTEN HAITZLER
CEDRIC BAIL
CHIDAMBAR ZINNOURY
CHRIS ROSS
CHRISTOPHE DUMEZ
CHRISTOPHER MICHAEL
CHRISTOPHE SADOINE
CHUNEON PARK
COREY DONOHOE
DAN SINCLAIR
DANIEL JUYUNG SEO
DANIEL STENBERG
DANIEL WILLMANN
DANIEL ZAOUI
DAN SINCLAIR
DAVIDE ANDREOLI
DAVID GOODLAD
DAVID SEIKEL
DOYOUN KANG
EDUARDO LIMA
FABIANO FIDÊNCIO
FLAVIO CEOLIN
GOVINDARAJU SM
GUILHERME SILVEIRA
GUILLAUME FRILOUX
GUSTAVO CHAVES
GUSTAVO LIMA CHAVES
GUSTAVO SVERZUT BARBIERI
GWANGLIM LEE
HAIFENG DENG
HISHAM MARDAM BEY
HOWELL TAM
HUGO CAMBOULIVE
HYOYOUNG CHANG
IBUKUN OLUMUYIWA
IGOR MURZOV
IVÁN BRIANO
JAEHWAN KIM
JÉRÉMY ZURCHER
JÉRÔME PINOT
JIHOON KIM
JIM KUKUNAS
JIYOUN PARK
JONAS M. GASTAL
JORGE LUIS ZAPATA
JOSE O GONZALEZ
JOSÉ ROBERTO DE SOUZA
KEITH MARSHALL
KIM SHINWOO
KIM WOELDERS
KIM YUNHAN
LANCE FETTERS
LARS MUNCH
LEANDRO DORILEO
LEANDRO PEREIRA
LEANDRO SANTIAGO
LEIF MIDDELSCHULTE
LIONEL ORRY
LUCAS DE MARCHI
LUIS FELIPE STRANO MORAES
MATHIEU TAILLEFUMIER
MATT BARCLAY
MICHAEL BOUCHAUD
MICHAEL LAUER
MICHAL PAKULA VEL RUTKA
MIKAEL SANS
MIKE BLUMENKRANTZ
MIKE MCCORMACK
MYOUNGWOON ROY KIM
MYUNGJAE LEE
NATHAN INGERSOLL
NATHAN INGERSOLL
NICHOLAS CURRAN
NICHOLAS HUGHART
NICOLAS AGUIRRE
PATRYK KACZMAREK
PAUL VIXIE
PETER WEHRFRITZ
PIERRE LE MAGOUROU
PRINCE KUMAR DUBEY
RAFAEL ANTOGNOLLI
RAFAL KRYPA
RAJEEV RANJAN
RAPHAEL KUBO DA COSTA
RICARDO DE ALMEIDA GONZAGA
ROBERT DAVID
RUI MIGUEL SILVA SEABRA
SANGHO PARK
SEBASTIAN DRANSFELD
SEONG-HO CHO
SEUNGSOO WOO
SHILPA SINGH
SIMON POOLE
SOHYUN KIM
STEFAN SCHMIDT
STEPHEN HOUSTON
STEVE IRELAND
SUNG W. PARK
THIERRY EL BORGI
TIAGO FALCÃO
TILL ADAM
TILMAN SAUERBECK
TIM HORTON
TOM GILBERT
TOM HACOHEN
TOR LILLQVIST
VIKRAM NARAYANAN
VINCENT TORRI
VINCENT RICHOMME
WILLEM MONSUWE
WOOHYUN JUNG
YAKOV GOLDBERG
YOUNESS ALAOUI
YURI HUDOBIN
ZBIGNIEW KOSINSKI
ZIGSMCKENZIE


<info>author special thanks</>
SARA
TEODORO
MONOPOLIO DI STATO


<info>license</>
Copyright © 2010-2016 Davide Andreoli
dave@gurumeditation.it

EpyMC is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

EpyMC is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with EpyMC. If not, see http://www.gnu.org/licenses/
"""
