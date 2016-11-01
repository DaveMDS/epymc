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

# Kodi references:
#  http://kodi.wiki/view/JSON-RPC_API/v6

from __future__ import absolute_import, print_function

import sys
import json
import pprint

import epymc.browser


thismodule = sys.modules[__name__]


def DBG(*args):
   print('JSON-RPC:', *args)
   pass


# JSON-RPC 2.0 error-codes
PARSE_ERROR = (-32700, 'Parse error')
INVALID_REQUEST = (-32600, 'Invalid Request')
METHOD_NOT_FOUND = (-32601, 'Method not found')
INVALID_PARAMS = (-32602, 'Invalid params')
INTERNAL_ERROR = (-32603, 'Internal error')


def _build_success_response(result, req_id=None):
   response = {'jsonrpc': '2.0',
               'id': req_id,
               'result': result}

   # DBG('--- RESPONSE (SUCCESS) ---\n', pprint.pformat(response), '\n')
   return json.dumps(response)


def _build_error_response(error, req_id=None):
   response = {'jsonrpc': '2.0',
               'id': req_id,
               'error': {'code': error[0],  # 'data': additiona error data
                         'message': error[1]}}

   DBG('--- RESPONSE (ERROR) ---\n', pprint.pformat(response), '\n')
   return json.dumps(response)


def execute(json_request):

   # parse the json string
   try:
      request = json.loads(json_request)
   except ValueError:
      return _build_error_response(PARSE_ERROR)

   # DBG('--- REQUEST ---\n', pprint.pformat(request), '\n')

   # basic validity checks
   if request.get('jsonrpc') != '2.0':
      return _build_error_response(INVALID_REQUEST)

   meth_name = request.get('method')
   if not meth_name:
      return _build_error_response(INVALID_REQUEST)

   # resolve the meth_name to the real method
   try:  # ex: Application.GetProperties
      cls_name, meth_name = meth_name.split('.')
   except ValueError:
      return _build_error_response(METHOD_NOT_FOUND)

   try:
      cls = getattr(thismodule, cls_name)
      meth = getattr(cls, meth_name)
   except AttributeError:
      return _build_error_response(METHOD_NOT_FOUND)

   # execute the class method
   try:
      result = meth(**request.get('params'))
   except TypeError:
      return _build_error_response(INVALID_PARAMS)
   except Exception:
      return _build_error_response(INTERNAL_ERROR)

   # return the result json string
   return _build_success_response(result)


class Application():

   @staticmethod
   def GetProperties(properties):
      ret = dict()

      for prop in properties:
         if prop == 'name':
            val = 'Kodi'
         elif prop == 'version':
            val = {'major': 17, 'minor': 0, 'tag': 'stable'}
         elif prop == 'volume':  # TODO IMPLEMENT
            val = 50
         elif prop == 'muted':  # TODO IMPLEMENT
            val = False
         else:
            continue  # TODO report error

         ret[prop] = val

      return ret


class XBMC():

   @staticmethod
   def GetInfoLabels(labels):
      """ http://kodi.wiki/view/InfoLabels """
      ret = dict()

      for label in labels:
         ctx, key = label.split('.', 1)
         ret[label] = ''

         if ctx == 'ListItem':
            browser = epymc.browser.current_browser_get()
            if not browser:
               continue

            listitem = browser.selected_item_data_get()
            if listitem.__class__.__name__ != 'ListItem':
               continue

            ret[label] = listitem['infoLabels'].get(key.lower(), '')

         else:
            # TODO more InfoLabel support
            print("NOT SUPPORTED InfoLabel: {}".format(label))

      return ret
