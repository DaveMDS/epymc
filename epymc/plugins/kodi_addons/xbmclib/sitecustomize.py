# This Python file uses the following encoding: utf-8


# inject xbmc in the addon main namespace
import __builtin__
import xbmc
__builtin__.xbmc = xbmc



# remove first item from argv (command), and set global addon_id
import sys

edit_done = False

def argv_setter_hook(path):
   global edit_done
   if edit_done:
      return

   if 'argv' in sys.__dict__:
      ex = sys.argv.pop(0)
      __builtin__.addon_id = ex.split('/')[-2] # global addon_id = "plugin.video.myplugin"
      edit_done = True

   raise ImportError # let the real import machinery do its work

sys.path_hooks[:0] = [argv_setter_hook]

