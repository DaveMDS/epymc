#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2014 Davide Andreoli <dave@gurumeditation.it>
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

import dbus
import dbus.service

# Why this ?
#  https://www.libreoffice.org/bugzilla/show_bug.cgi?id=26903


INTROSPECT_DOCTYPE = \
'<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN" ' \
'"http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">\n'


def dbus_property(dbus_interface, signature, access='read'):
   """ TODO doc """
   def decorator(func):
      func._dbus_is_property = True
      func._dbus_interface = dbus_interface
      func._dbus_type = signature
      func._dbus_access = access
      return func

   return decorator


class DBusServiceObjectWithProps(dbus.service.Object):
   """ TODO doc """

   def __init__(self, *args, **kargs):
      dbus.service.Object.__init__(self, *args, **kargs)

   def reflect_on_property(self, func):
      return '    <property name="%s" type="%s" access="%s"/>\n' % \
             (func.__name__, func._dbus_type, func._dbus_access)

   def Introspect(self, object_path, connection):
      """Return a string of XML encoding this object's supported interfaces,
      methods, signals AND PROPERTIES.
      """
      reflection_data = INTROSPECT_DOCTYPE
      reflection_data += '<node name="%s">\n' % object_path

      interfaces = self._dbus_class_table[self.__class__.__module__ + '.' +
                                          self.__class__.__name__]
      for (name, funcs) in interfaces.items():
         reflection_data += '  <interface name="%s">\n' % (name)

         for func in funcs.values():
            if getattr(func, '_dbus_is_method', False):
               reflection_data += self.__class__._reflect_on_method(func)
            elif getattr(func, '_dbus_is_signal', False):
               reflection_data += self.__class__._reflect_on_signal(func)
            elif getattr(func, '_dbus_is_property', False):
               reflection_data += self.reflect_on_property(func)

         reflection_data += '  </interface>\n'

      for name in connection.list_exported_child_objects(object_path):
         reflection_data += '  <node name="%s"/>\n' % name

      reflection_data += '</node>\n'

      return reflection_data


   @dbus.service.method(dbus.PROPERTIES_IFACE,
                        in_signature='ss', out_signature='v')
   def Get(self, interface_name, property_name):
      func = getattr(self, property_name)
      if callable(func):
         return func()
      else:
         raise dbus.exceptions.DBusException(
            'interface_name',
            'The object does not implement the %s property' % property_name)

   @dbus.service.method(dbus.PROPERTIES_IFACE,
                        in_signature='s', out_signature='a{sv}')
   def GetAll(self, interface_name):
      DBG("GetAll")
      try:
         funcs = self._dbus_class_table[self.__class__.__module__ + '.' +
                                        self.__class__.__name__][interface_name]
      except:
         raise dbus.exceptions.DBusException(
            interface_name, 'The object does not implement this interface')

      props = {}
      for (name, func) in funcs.items():
         if getattr(func, '_dbus_is_property', False):
            props[func.__name__] = func(self)

      return props

   @dbus.service.method(dbus.PROPERTIES_IFACE,
                        in_signature='ssv')
   def Set(self, interface_name, property_name, new_value):
      pass

   @dbus.service.signal(dbus.PROPERTIES_IFACE,
                        signature='sa{sv}as')
   def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
      pass
