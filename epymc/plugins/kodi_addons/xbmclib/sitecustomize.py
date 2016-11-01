# This Python file uses the following encoding: utf-8

import sys
import __builtin__


# internal utility for epymc <--> addon comunication  ##########################

def emc_function_call(func):
   """ Decorator to be used on functions """
   def func_wrapper(*args, **kargs):
      params = {'args': args, 'kargs': kargs}
      sys.stdout.write('_{} {}\n'.format(func.__name__, params))
      sys.stdout.flush()
      return func(*args, **kargs)
   return func_wrapper


def emc_method_call(meth):
   """ Decorator to be used on methods """
   def func_wrapper(self, *args, **kargs):
      params = {'args': (self._class_id,) + args, 'kargs': kargs}
      sys.stdout.write('_{}_{} {}\n'.format(self.__class__.__name__,
                                            meth.__name__, params))
      sys.stdout.flush()
      return meth(self, *args, **kargs)
   return func_wrapper


def emc_wait_replay():
   """ Wait for a replay from epymc and return the received data """
   return sys.stdin.readline().rstrip('\n')


def NOT_IMPLEMENTED(func):
   """ Decorator for not-yet-implemented funcs and methods """
   def func_wrapper(*args, **kargs):
      print('NOT IMPLEMENTED {} {} {}'.format(func.__name__, args, kargs))
      return func(*args, **kargs)
   return func_wrapper


__builtin__.emc_function_call = emc_function_call
__builtin__.emc_method_call = emc_method_call
__builtin__.emc_wait_replay = emc_wait_replay
__builtin__.NOT_IMPLEMENTED = NOT_IMPLEMENTED


#  remove first item from argv (command), and set global addon_id  #############
edit_done = False


def argv_setter_hook(path):
   global edit_done
   if edit_done:
      return

   if 'argv' in sys.__dict__:
      # remove first arg (in kodi it's not provided, because python is embedded)
      ex = sys.argv.pop(0)
      # inject global addon_id = "plugin.video.myplugin"
      __builtin__.addon_id = ex.split('/')[-2]
      edit_done = True

   raise ImportError  # let the real import machinery do its work

sys.path_hooks[:0] = [argv_setter_hook]


#  inject some more stuff in the addon main namespace  #########################
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs
__builtin__.xbmc = xbmc
__builtin__.xbmcaddon = xbmcaddon
__builtin__.xbmcgui = xbmcgui
__builtin__.xbmcplugin = xbmcplugin
__builtin__.xbmcvfs = xbmcvfs
__builtin__.sys = sys

