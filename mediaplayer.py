#!/usr/bin/env python

import edje
import emotion

import gui
import input

_emotion = None
_controls_visible = False
_buttons = list()
_current_button_num = 3

def play_video(url):
    global _emotion

    print 'Play ' + url
    # TODO handle real url

    if not _emotion:
        _init_emotion()


    _emotion.file_set(url)

    ## TEST VARIOUS INFO
    print "RATIO: " + str(_emotion.ratio_get())
    print "VIDEO CHNS: " + str(_emotion.video_channel_count())
    print "AUDIO CHNS: " + str(_emotion.audio_channel_count())
    print _emotion.video_channel_get()
    print _emotion.audio_channel_get()
    print _emotion.meta_info_dict_get()
    print _emotion.size
    print _emotion.image_size
    print _emotion.ratio
    ##

    # set aspect according to video size
    (w, h) = _emotion.image_size
    edje.extern_object_aspect_set(_emotion, edje.EDJE_ASPECT_CONTROL_BOTH, w, h)

    _emotion.play = True
    video_player_show()

def video_player_show():
    gui.signal_emit('videoplayer,show')
    input.listener_add("videoplayer", input_event_cb)
    #~ video_player_show()

def video_player_hide():
    hide_video_controls()
    input.listener_del("videoplayer")
    gui.signal_emit('videoplayer,hide')

def stop_video():
    global _emotion
    _emotion.play = False
    video_player_hide()


def show_video_controls():
    global _controls_visible
    gui.signal_emit('videoplayer,controls,show')
    gui.signal_emit('volume,show')
    _controls_visible = True
    # update volume slider
    volume_set(volume_get())

def hide_video_controls():
    global _controls_visible
    gui.signal_emit('videoplayer,controls,hide')
    gui.signal_emit('volume,hide')
    _controls_visible = False

def toggle_video_controls():
    global _controls_visible
    if _controls_visible:
        hide_video_controls()
    else:
        show_video_controls()

def volume_set(vol):
    global _emotion
    _emotion.audio_volume_set(vol / 100)
    gui.part_get('volume/slider').value = vol

def volume_get():
    global _emotion
    return int(_emotion.audio_volume_get() * 100)


def _init_emotion():
    global _emotion
    global _buttons

    _emotion = emotion.Emotion(gui._win.evas_get(), module_filename='gstreamer')
    gui.swallow_set('videoplayer/video', _emotion)
    _emotion.smooth_scale = True # TODO Needed? make it configurable?

    #~ _emotion.on_key_down_add(_cb)
    _emotion.on_mouse_down_add(_cb_video_mouse_down)
    _emotion.on_frame_decode_add(_cb_frame_decode)
    #~ _emotion.on_audio_level_change_add(_cb_volume_change)


    #~ gui.part_get('videoplayer/controls/slider').min_max_set(0.0, 1.0)

    # connect controls callbacks & fill buttons list
    _buttons.append(gui.part_get('videoplayer/controls/btn_fbackward'))
    _buttons[-1].callback_clicked_add(_cb_btn_fbackward)
    _buttons[-1].data['cb'] = _cb_btn_fbackward
    _buttons[-1].on_mouse_in_add(_cb_btns_mouse_in)
    _buttons[-1].disabled_set(1)

    _buttons.append(gui.part_get('videoplayer/controls/btn_backward'))
    _buttons[-1].callback_clicked_add(_cb_btn_backward)
    _buttons[-1].data['cb'] = _cb_btn_backward
    _buttons[-1].on_mouse_in_add(_cb_btns_mouse_in)
    _buttons[-1].disabled_set(1)

    _buttons.append(gui.part_get('videoplayer/controls/btn_stop'))
    _buttons[-1].callback_clicked_add(_cb_btn_stop)
    _buttons[-1].data['cb'] =_cb_btn_stop
    _buttons[-1].on_mouse_in_add(_cb_btns_mouse_in)
    _buttons[-1].disabled_set(1)

    _buttons.append(gui.part_get('videoplayer/controls/btn_play'))
    _buttons[-1].callback_clicked_add(_cb_btn_play)
    _buttons[-1].data['cb'] =_cb_btn_play
    _buttons[-1].on_mouse_in_add(_cb_btns_mouse_in)
    _buttons[-1].label_set('Pause')
    _buttons[-1].disabled_set(0)

    _buttons.append(gui.part_get('videoplayer/controls/btn_forward'))
    _buttons[-1].callback_clicked_add(_cb_btn_forward)
    _buttons[-1].data['cb'] =_cb_btn_forward
    _buttons[-1].on_mouse_in_add(_cb_btns_mouse_in)
    _buttons[-1].disabled_set(1)

    _buttons.append(gui.part_get('videoplayer/controls/btn_fforward'))
    _buttons[-1].callback_clicked_add(_cb_btn_fforward)
    _buttons[-1].data['cb'] =_cb_btn_fforward
    _buttons[-1].on_mouse_in_add(_cb_btns_mouse_in)
    _buttons[-1].disabled_set(1)


    gui.part_get('videoplayer/controls/slider').callback_changed_add(_cb_slider_changed)
    #~ gui.part_get('videoplayer/controls/slider').callback_delay_changed_add(_cb_slider_changed)

    gui.part_get('videoplayer/controls/btn_play').label_set('Pause')

    # TODO Shutdown all emotion stuff & the buttons list

def _cb_video_mouse_down(vid, ev):
    toggle_video_controls()

def _cb_frame_decode(vid):
    _update_slider()

def _cb_btns_mouse_in(button, event):
    global _buttons
    global _current_button_num

    if button != _buttons[_current_button_num]:
        _buttons[_current_button_num].disabled_set(1)
        _current_button_num = _buttons.index(button)
        _buttons[_current_button_num].disabled_set(0)

def _cb_btn_play(btn):
    global _emotion

    if _emotion.play:
        _emotion.play = False
        btn.label_set('Play')
    else:
        _emotion.play = True
        btn.label_set('Pause')


def _cb_btn_stop(btn):
    stop_video()

def _cb_btn_forward(btn):
    global _emotion
    _emotion.position_set(_emotion.position + 10) #TODO make this configurable

def _cb_btn_backward(btn):
    global _emotion
    _emotion.position_set(_emotion.position - 10) #TODO make this configurable

def _cb_btn_fforward(btn):
    global _emotion
    _emotion.position_set(_emotion.position + 60) #TODO make this configurable

def _cb_btn_fbackward(btn):
    global _emotion
    _emotion.position_set(_emotion.position - 60) #TODO make this configurable


def _cb_slider_changed(slider):
    global _emotion
    _emotion.position_set(_emotion.play_length * slider.value)

def _update_slider():
    global _emotion
    global _controls_visible

    if _controls_visible:
        pos = _emotion.position
        len = _emotion.play_length

        lh = int(len / 3600)
        lm = int((len / 60) - (lh * 60))
        ls = int(len - (lm * 60) - (lh * 3600))

        ph = int(pos / 3600)
        pm = int((pos / 60) - (ph * 60))
        ps = int(pos - (pm * 60) - (ph * 3600))

        gui.part_get('videoplayer/controls/slider').value = pos / len
        gui.text_set('videoplayer/controls/position', '%i:%02i:%02i' % (ph,pm,ps))
        gui.text_set('videoplayer/controls/length', '%i:%02i:%02i' % (lh,lm,ls))


def input_event_cb(event):
    global _emotion
    global _controls_visible
    global _buttons
    global _current_button_num

    if _controls_visible:
        if event == 'BACK':
            hide_video_controls()
        if event == 'OK':
            button = _buttons[_current_button_num]
            cb = button.data['cb']
            cb(button)
        elif event == 'RIGHT':
            if _current_button_num < len(_buttons) - 1:
                _buttons[_current_button_num].disabled_set(1)
                _current_button_num += 1
                _buttons[_current_button_num].disabled_set(0)
        elif event == 'LEFT':
            if _current_button_num > 0:
                _buttons[_current_button_num].disabled_set(1)
                _current_button_num -= 1
                _buttons[_current_button_num].disabled_set(0)
    else:
        if event == 'BACK':
            stop_video()
        elif event == 'OK':
            show_video_controls()
        elif event == 'TOGGLE_PAUSE':
            _emotion.play = not _emotion.play
        elif event == 'RIGHT':
            _emotion.position_set(_emotion.position + 10) #TODO make this configurable
        elif event == 'LEFT':
            _emotion.position_set(_emotion.position - 10) #TODO make this configurable

    return input.EVENT_BLOCK
