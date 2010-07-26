#!/usr/bin/env python

import emotion

import gui

_vid = None

def play_url(url):
    global _vid
    
    print 'Play ' + url
    # TODO handle real url

    if not _vid:
        _init_vid()


    _vid.file_set(url)

    ## TEST VARIOUS INFO
    print "RATIO: " + str(_vid.ratio_get())
    print "VIDEO CHNS: " + str(_vid.video_channel_count())
    print "AUDIO CHNS: " + str(_vid.audio_channel_count())
    print _vid.video_channel_get()
    print _vid.audio_channel_get()
    print _vid.meta_info_dict_get()
    ##

    _vid.play = True
    gui.signal_emit('videoplayer,show')


def _init_vid():
    global _vid

    _vid = emotion.Emotion(gui._win.evas_get(), module_filename='gstreamer')
    gui.swallow_set('videoplayer/video', _vid)
    _vid.smooth_scale = True # TODO Needed? make it configurable?

