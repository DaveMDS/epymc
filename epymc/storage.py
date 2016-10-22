#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2016 Davide Andreoli <dave@gurumeditation.it>
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

import os
from operator import attrgetter

import epymc.ini as ini
import epymc.utils as utils
import epymc.events as events


def DBG(*args):
   # print('STORAGE:', *args)
   pass

def LOG(*args):
   print('STORAGE:', *args)

def ERR(*args):
   print('STORAGE Error:', *args)


_devices = {} # key: uniq_id  val: EmcDevice instance
_udev_module = None # EmcDeviceManagerUdev instance


######## PUBLIC API ###########################################################

class EmcDevType:
   SYSTEM     = 1 # like home and root
   FAVORITE   = 2 # user favorite folders  (TOBEDONE)
   HARDDISK   = 3 # internal hard drives
   DVD        = 4 # dvd video discs
   AUDIOCD    = 5 # audio cd discs
   DATADISK   = 6 # cdrom disc
   THUMBDRIVE = 7 # usb thumbdrives
   NETSHARE   = 8 # networks shares (samba, ntfs) (TOBEDONE)


class EmcDevice(object):
   uniq_id = None      # str - unique device identifier (will vary on backends)
   type = None         # one of EmcDevType "enum"
   device = None       # ex: "/dev/sr0"
   mount_point = None  # ex: "/media/disk" or None if not mounted
   label = None        # ex: "DVDVOLUME"
   icon = None         # ex: "icon/dvd"
   size = 0            # partition size in bytes
   audio_tracks = 0    # number of tracks for EmcDevType.AUDIOCD
   sort_key = 100      # additional value for further ordering

   def __init__(self, **kargs):
      self.__dict__.update(kargs)

   def __repr__(self):
      return '<EmcDevice {0.uniq_id}\n' \
             '  type: {0.type}\n' \
             '  device: {0.device}\n' \
             '  mount_point: {0.mount_point}\n' \
             '  label: {0.label}\n' \
             '  icon: {0.icon}\n' \
             '  size: {0.size}\n' \
             '  audio_tracks: {0.audio_tracks}\n' \
             '>'.format(self)

   @property
   def is_mounted(self):
      return self.mount_point != None

   @property
   def require_eject(self):
      pass

   def eject(self):
      pass

   # def mount(self): pass
   # def umount(self): pass


def init():
   global _udev_module
   DBG('init')

   ini.add_section('storage')
   if not ini.has_option('storage', 'show_home'):
      ini.set('storage', 'show_home', True)
   if not ini.has_option('storage', 'show_root'):
      ini.set('storage', 'show_root', False)

   device_added(EmcDevice(uniq_id='user_home', type=EmcDevType.SYSTEM,
                          sort_key=10, mount_point=os.getenv('HOME'),
                          label=_('User home'), icon='icon/home'))
   _udev_module = EmcDeviceManagerUdev()

def shutdown():
   DBG('shutdown')
   _udev_module.__shutdown__()

def list_devices(filter_type=None):
   """ List all know devices.
   Args:
      filter_type: a single (or a tuple of) EmcDevType
   Returns:
      A filtered and sorted list of EmcDevice instances
   """
   l = []
   for key, device in _devices.items():
      if isinstance(filter_type, int):
         if device.type != filter_type:
            continue
      elif isinstance(filter_type, tuple):
         if device.type not in filter_type:
            continue
      if device.type == EmcDevType.SYSTEM:
         if device.mount_point == '/' and not ini.get_bool('storage', 'show_root'):
            continue
         if device.mount_point == os.getenv('HOME') and not ini.get_bool('storage', 'show_home'):
            continue
      l.append(device)
   l.sort(key=attrgetter('type', 'sort_key', 'label'))
   return l

def device_added(device):
   """ Called by a manager when a new device is discovered """
   _devices[device.uniq_id] = device
   events.event_emit('STORAGE_CHANGED')
   # TODO more accurate notification system

def device_removed(uniq_id):
   """ Called by a manager when a device is removed """
   if uniq_id in _devices:
      del _devices[uniq_id]
      events.event_emit('STORAGE_CHANGED')
      # TODO more accurate notification system

def partition_hum_size(bytes):
   """ Get the human readable size like reported by UDisk2 """
   bytes = float(bytes)
   if bytes > 1000000000000:
      size = bytes / 1000000000000
      unit = 'TB'
   elif bytes > 1000000000:
      size = bytes / 1000000000
      unit = 'GB'
   elif bytes > 1000000:
      size = bytes / 1000000
      unit = 'MB'
   else:
      size = bytes / 1000
      unit = 'KB'

   if size < 10:
      return '%.1f %s' % (size, unit)
   else:
      return '%.0f %s' % (size, unit)


######## MOUNT HELPERS ########################################################

import subprocess

def check_mount(device_node):
   cmd = ['findmnt','-n','--raw','--output=target','-f','--source',device_node]
   try:
      mount_point = subprocess.check_output(cmd, universal_newlines=True)
   except subprocess.CalledProcessError:
      mount_point = None

   if mount_point:
      mount_point = mount_point.strip()
   DBG('Mount point for {} is {}'.format(device_node, mount_point))

   return mount_point or None


def try_mount(device, mount_cb):
   # cmd = 'udevil mount ' + device.device
   cmd = 'udisksctl mount --no-user-interaction -b %s' % device.device
   utils.EmcExec(cmd, done_cb=lambda out,d: mount_cb(d), d=device)



######## UDEV MODULE ##########################################################

from efl import ecore

import pyudev
import queue

class EmcDeviceManagerUdev():

   managed_subsystems = ('block')

   def __init__(self):
      DBG('Using pyudev {} and udev {}'.format(
           pyudev.__version__, pyudev.udev_version()))

      # create the udev context
      self.udev = pyudev.Context()

      # queue + timer to syncronize the udev thread
      self.queue = queue.Queue() # items: (action, device)
      self.qtimer = ecore.Timer(3.0, self.queue_timer_cb)

      # start monitoring udev for events
      monitor = pyudev.Monitor.from_netlink(self.udev)
      monitor.filter_by(self.managed_subsystems)
      self.observer = pyudev.MonitorObserver(monitor, self.udev_device_filter)
      self.observer.start()

      # search for existing devices
      for udevice in self.udev.list_devices(subsystem=self.managed_subsystems):
         self.udev_device_filter('add', udevice)
      self.queue_timer_cb()

   def __shutdown__(self):
      self.qtimer.delete()
      monitor = self.observer.monitor
      self.observer.stop()
      del self.observer
      del monitor
      del self.udev

   def queue_timer_cb(self):
      if self.queue.empty():
         return ecore.ECORE_CALLBACK_RENEW

      while not self.queue.empty():
         action, device = self.queue.get_nowait()

         if action == 'add': # device is EmcDevice instance
            if device.is_mounted or device.type in (EmcDevType.AUDIOCD,
                                                    EmcDevType.DVD):
               device_added(device)
            else: # TODO make this configurable
               try_mount(device, self.device_mounted_cb)

         elif action == 'remove': # device is uniq_id
            device_removed(device)

      return ecore.ECORE_CALLBACK_RENEW

   def device_mounted_cb(self, device):
      device.mount_point = check_mount(device.device)
      if device.mount_point is None:
         LOG('Cannot mount ' + device.device)
      device_added(device)


   def udev_device_filter(self, action, udevice, thread=True):
      """ WARNING: This is called (also) from the udev thread !!! """
      if not udevice.is_initialized or udevice.subsystem != 'block':
         DBG("IGNORING DEVICE", udevice)
         return

      if udevice.device_type == 'disk':
         # self.dump_udevice(udevice) # for debug

         if action == 'change' and not udevice.get('ID_CDROM_MEDIA'):
            self.udev_device_manage('remove', udevice)
            return
         else:
            action = 'add' # sure??
         
         if udevice.get('ID_CDROM_MEDIA_DVD') == '1' and udevice.get('ID_FS_TYPE') == 'udf':
            self.udev_device_manage(action, udevice, EmcDevType.DVD)
            return

         if udevice.get('ID_CDROM_MEDIA_CD') == '1' and udevice.get('ID_CDROM_MEDIA_TRACK_COUNT_AUDIO') != None:
            self.udev_device_manage(action, udevice, EmcDevType.AUDIOCD)
            return

         if udevice.get('ID_FS_USAGE') == 'filesystem':
            self.udev_device_manage(action, udevice, EmcDevType.DATADISK)
            return

         DBG("IGNORING DISK", udevice)
         return

      elif udevice.device_type == 'partition':
         
         if udevice.get('ID_FS_USAGE') != 'filesystem':
            DBG("IGNORING PARTITION", udevice)
            return
            
         if udevice.get('ID_USB_DRIVER') == 'usb-storage':
            self.udev_device_manage(action, udevice, EmcDevType.THUMBDRIVE)
            return
         else:
            self.udev_device_manage(action, udevice, EmcDevType.HARDDISK)
            return

      DBG("IGNORING DEVICE", udevice)
      return

   def udev_device_manage(self, action, udevice, emc_type=None):
      """ WARNING: This is called (also) from the udev thread !!! """
      if action == 'add':
         # self.dump_udevice(udevice) # for debug

         # partition size (in bytes)
         size = int(udevice.get('ID_PART_ENTRY_SIZE', '0')) * 512

         # is already mounted?
         mount_point = check_mount(udevice.device_node)

         # the root filesystem is special
         if mount_point == '/':
            emc_type = EmcDevType.SYSTEM
         
         # choose label
         if emc_type == EmcDevType.AUDIOCD:
            label = _('Audio CD')
         elif emc_type == EmcDevType.DVD:
            label = _('DVD Disk')
         elif mount_point == '/':
            label = _('Root filesystem')
         else:
            fs_label = udevice.get('ID_FS_LABEL_ENC') or udevice.get('ID_FS_LABEL')
            vendor = udevice.get('ID_VENDOR_ENC') or udevice.get('ID_VENDOR')
            model = udevice.get('ID_MODEL_ENC') or udevice.get('ID_MODEL')

            # I really cannot understand the pyudev encoding... :/
            if fs_label: fs_label = fs_label.replace('\\x20',' ').strip()
            if vendor: vendor = vendor.replace('\\x20',' ').strip()
            if model: model = model.replace('\\x20',' ').strip()

            if fs_label:
               label = fs_label
            elif size > 0:
               if emc_type == EmcDevType.HARDDISK:
                  label = _('{} Hard disk').format(partition_hum_size(size))
               elif emc_type == EmcDevType.THUMBDRIVE:
                  label = _('{} Thumb drive').format(partition_hum_size(size))
               else:
                  label = _('{} Volume').format(partition_hum_size(size))
            elif vendor and model:
               label = '{} {}'.format(vendor, model)
            elif model or vendor:
               label = model or vendor
            else:
               label = _('Volume')

         # choose icon
         if mount_point == '/':
            icon = 'icon/folder' # TODO better icon
         elif emc_type in (EmcDevType.AUDIOCD, EmcDevType.DVD, EmcDevType.DATADISK):
            icon = 'icon/optical'
         elif emc_type == EmcDevType.HARDDISK:
            icon = 'icon/harddisk'
         elif emc_type == EmcDevType.THUMBDRIVE:
            icon = 'icon/thumbdrive'
         elif emc_type == EmcDevType.NETSHARE:
            icon = 'icon/netshare'

         # number of audio tracks for AudioCD
         if emc_type == EmcDevType.AUDIOCD:
            audio_tracks = int(udevice.get('ID_CDROM_MEDIA_TRACK_COUNT_AUDIO', 0))
         else:
            audio_tracks = 0

         # create the EmcDevice instance
         d = EmcDevice(uniq_id=udevice.device_path, type=emc_type, size=size,
                       device=udevice.device_node, mount_point=mount_point,
                       label=label, icon=icon, audio_tracks=audio_tracks)
         self.queue.put((action, d))
         # self.dump_udevice(udevice)

      elif action == 'remove':
         self.queue.put((action, udevice.device_path))

      else:
         ERR("Unknow ACTION", action)

   def dump_udevice(self, udevice):
      print("="*40)
      print(udevice)
      print("subsystem", udevice.subsystem)
      print("device_type", udevice.device_type)
      print("device_node", udevice.device_node)
      print("is_initialized", udevice. is_initialized)
      print("Properties:")
      for p in udevice:
         print("  ", p, repr(udevice[p]))


"""
######## SAMBA MODULE #########################################################

import smbc
import socket


class EmcDeviceManagerSamba(object):

   def __init__(self):
      # DBG('Using pyudev {} and udev {}'.format(
           # pyudev.__version__, pyudev.udev_version()))
      DBG("Samba init")
      self.scan_network()
      self.scan_host('192.168.1.5')

   def scan_network(self):
      self.checkSMB('192.168.1.5')
      self.checkSMB('192.168.1.1')

   def checkSMB(self, ip):
      " looks for running samba server "
      # check if the server is running a smb server
      sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      # This may need to get changed on high-latency links...
      sd.settimeout(1)
      try:
         sd.connect((ip, 445))
         sd.close()
         print('FOUND smb at ip '+ip),
      except:
         print('no samba'),
      
      
   def scan_host(self, host_ip):
      # ctx = smbc.Context(auth_fn=my_auth_callback_fn)
      ctx = smbc.Context()
      entries = ctx.opendir('smb://' + host_ip).getdents()
      for entry in entries:
         print(entry)
"""



















