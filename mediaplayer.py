#!/usr/bin/env python

import edje
import emotion

import gui

_emotion = None
_controls_visible = False

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
    gui.signal_emit('videoplayer,show')

def stop_video():
    global _emotion
    _emotion.play = False
    hide_video_controls()
    gui.signal_emit('videoplayer,hide')
   

def show_video_controls():
    global _controls_visible
    gui.signal_emit('videoplayer,controls,show')
    _controls_visible = True

def hide_video_controls():
    global _controls_visible
    gui.signal_emit('videoplayer,controls,hide')
    _controls_visible = False

def toggle_video_controls():
    global _controls_visible
    if _controls_visible:
        hide_video_controls()
    else:
        show_video_controls()

def _init_emotion():
    global _emotion

    _emotion = emotion.Emotion(gui._win.evas_get(), module_filename='gstreamer')
    gui.swallow_set('videoplayer/video', _emotion)
    _emotion.smooth_scale = True # TODO Needed? make it configurable?

    #~ _emotion.on_key_down_add(_cb)
    _emotion.on_mouse_down_add(_cb_video_mouse_down)

    # connect controls buttons callbacks
    gui.part_get('videoplayer/controls/btn_play').callback_clicked_add(_cb_btn_play)
    gui.part_get('videoplayer/controls/btn_stop').callback_clicked_add(_cb_btn_stop)
    gui.part_get('videoplayer/controls/btn_play').label_set('Pause')

    # TODO Shutdown all emotion stuff
    
def _cb_video_mouse_down(obj, ev):
    toggle_video_controls()
    

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
