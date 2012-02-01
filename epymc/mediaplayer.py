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
import edje
import elementary
import emotion

import gui
import input_events


def DBG(msg):
   print ('MEDIAPLAYER: ' + msg)
   pass


_emotion = None
_controls_visible = False
_buttons = list()
_current_button_num = 3


def play_video(url):
   DBG('Play ' + url)  # TODO handle real url

   if not _emotion:
      _init_emotion()

   _emotion.file_set(url)

   ## TEST VARIOUS INFO
   DBG("RATIO: " + str(_emotion.ratio_get()))
   DBG("VIDEO CHNS: " + str(_emotion.video_channel_count()))
   DBG("AUDIO CHNS: " + str(_emotion.audio_channel_count()))
   DBG(str(_emotion.video_channel_get()))
   DBG(str(_emotion.audio_channel_get()))
   DBG(str(_emotion.meta_info_dict_get()))
   DBG(str(_emotion.size))
   DBG(str(_emotion.image_size))
   DBG(str(_emotion.ratio))
   ##

   # set aspect according to video size
   (w, h) = _emotion.image_size
   edje.extern_object_aspect_set(_emotion, edje.EDJE_ASPECT_CONTROL_BOTH, w, h)

   _emotion.play = True
   video_player_show()

def stop():
   _emotion.play = False

def volume_set(vol):
   _emotion.audio_volume_set(vol / 100)
   gui.part_get('volume/slider').value = vol

def volume_get():
   return int(_emotion.audio_volume_get() * 100)

def forward():
   DBG("Forward cb" + str(_emotion.position))
   _emotion.position += 10 #TODO make this configurable

def backward():
   DBG("Backward cb" + str(_emotion.position))
   _emotion.position -= 10 #TODO make this configurable

def fforward():
   DBG("FastForward cb" + str(_emotion.position))
   _emotion.position += 60 #TODO make this configurable

def fbackward():
   DBG("FastBackward cb" + str(_emotion.position))
   _emotion.position -= 60 #TODO make this configurable



def video_player_show():
   gui.signal_emit('videoplayer,show')
   input_events.listener_add("videoplayer", input_event_cb)

def video_player_hide():
   video_controls_hide()
   input_events.listener_del("videoplayer")
   gui.signal_emit('videoplayer,hide')

def video_controls_show():
   global _controls_visible
   gui.signal_emit('videoplayer,controls,show')
   gui.signal_emit('volume,show')
   _controls_visible = True
   # update volume slider
   DBG("Volume: " + volume_get())
   volume_set(volume_get())

def video_controls_hide():
   global _controls_visible
   gui.signal_emit('videoplayer,controls,hide')
   gui.signal_emit('volume,hide')
   _controls_visible = False

def video_controls_toggle():
   if _controls_visible:
      video_controls_hide()
   else:
      video_controls_show()




def _init_emotion():
   global _emotion

   _emotion = emotion.Emotion(gui.win.evas_get(), module_filename='gstreamer')
   gui.swallow_set('videoplayer/video', _emotion)
   _emotion.smooth_scale = True # TODO Needed? make it configurable?

   #~ _emotion.on_key_down_add(_cb)
   _emotion.on_mouse_down_add(_cb_video_mouse_down)
   _emotion.on_frame_decode_add(_cb_frame_decode) # TODO too often?
   #~ _emotion.on_audio_level_change_add(_cb_volume_change)


   # buttons box
   box = elementary.Box(gui.win)
   box.horizontal_set(1)
   gui.swallow_set("videoplayer/controls/btn_swallow", box)
   
   #  <<  fast backward
   bt = elementary.Button(gui.win);
   bt.icon_set(gui.load_icon("icon/fbwd"))
   bt.callback_clicked_add(_cb_btn_fbackward)
   bt.data['cb'] = _cb_btn_fbackward
   bt.on_mouse_in_add(_cb_btns_mouse_in)
   bt.disabled_set(1)
   bt.show()
   box.pack_end(bt)
   _buttons.append(bt)

   #  <   backward
   bt = elementary.Button(gui.win);
   bt.icon_set(gui.load_icon("icon/bwd"))
   bt.callback_clicked_add(_cb_btn_backward)
   bt.data['cb'] = _cb_btn_backward
   bt.on_mouse_in_add(_cb_btns_mouse_in)
   bt.disabled_set(1)
   bt.show()
   box.pack_end(bt)
   _buttons.append(bt)

   #  stop
   bt = elementary.Button(gui.win);
   bt.icon_set(gui.load_icon("icon/stop"))
   bt.callback_clicked_add(_cb_btn_stop)
   bt.data['cb'] = _cb_btn_stop
   bt.on_mouse_in_add(_cb_btns_mouse_in)
   bt.label_set("Stop")
   bt.disabled_set(1)
   bt.show()
   box.pack_end(bt)
   _buttons.append(bt)

   #  play/pause
   bt = elementary.Button(gui.win);
   bt.icon_set(gui.load_icon("icon/play"))
   bt.callback_clicked_add(_cb_btn_play)
   bt.data['cb'] = _cb_btn_play
   bt.on_mouse_in_add(_cb_btns_mouse_in)
   bt.label_set("Pause")
   bt.disabled_set(0)
   bt.show()
   box.pack_end(bt)
   _buttons.append(bt)

   #  >   forward
   bt = elementary.Button(gui.win);
   bt.icon_set(gui.load_icon("icon/fwd"))
   bt.callback_clicked_add(_cb_btn_forward)
   bt.data['cb'] = _cb_btn_forward
   bt.on_mouse_in_add(_cb_btns_mouse_in)
   bt.disabled_set(1)
   bt.show()
   box.pack_end(bt)
   _buttons.append(bt)
   
   #  >>  fast forward
   bt = elementary.Button(gui.win);
   bt.icon_set(gui.load_icon("icon/ffwd"))
   bt.callback_clicked_add(_cb_btn_fforward)
   bt.data['cb'] = _cb_btn_fforward
   bt.on_mouse_in_add(_cb_btns_mouse_in)
   bt.disabled_set(1)
   bt.show()
   box.pack_end(bt)
   _buttons.append(bt)


   gui.part_get('videoplayer/controls/slider').callback_changed_add(_cb_slider_changed)
   gui.part_get('videoplayer/controls/slider').focus_allow_set(False)
   gui.part_get('volume/slider').focus_allow_set(False)
   #~ gui.part_get('videoplayer/controls/slider').callback_delay_changed_add(_cb_slider_changed)
   
   # TODO Shutdown all emotion stuff & the buttons list

def _cb_video_mouse_down(vid, ev):
   video_controls_toggle()

def _cb_frame_decode(vid):
   _update_slider()

def _cb_btns_mouse_in(button, event):
   if button != _buttons[_current_button_num]:
      _buttons[_current_button_num].disabled_set(1)
      _current_button_num = _buttons.index(button)
      _buttons[_current_button_num].disabled_set(0)

def _cb_btn_play(btn):
   DBG("Play cb")
   if _emotion.play:
      _emotion.play = False
      btn.label_set('Play')
   else:
      _emotion.play = True
      btn.label_set('Pause')

def _cb_btn_stop(btn):
   stop()
   video_player_hide()

def _cb_btn_forward(btn):
   forward()

def _cb_btn_backward(btn):
   backward()

def _cb_btn_fforward(btn):
   fforward()

def _cb_btn_fbackward(btn):
   fbackward()


def _cb_slider_changed(slider):
   _emotion.position_set(_emotion.play_length * slider.value)

def _update_slider():
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
   global _current_button_num

   if _controls_visible:
      if event == 'BACK':
         video_controls_hide()
      if event == 'OK':
         button = _buttons[_current_button_num]
         cb = button.data['cb']
         cb(button)
         # TODO TRY THIS INSTEAD:
         # evas_object_smart_callback_call(obj, "sig", NULL);
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
         stop()
         video_player_hide()
      elif event == 'OK':
         video_controls_show()
      elif event == 'RIGHT':
         forward()
      elif event == 'LEFT':
         backward()

   if event == 'TOGGLE_PAUSE':
      _cb_btn_play(_buttons[3])

   return input_events.EVENT_BLOCK
