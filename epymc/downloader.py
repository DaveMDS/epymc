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


"""

 WARNING: THIS FILE IS DEPRECATED, DONT USE THIS FILE !!!

   Use utils.download_url_async() instead

   The file is still here just for reference in case we will need
   to code something similar in the future.


"""

import os
import tempfile
import threading
from queue import Queue
from urllib.request import urlretrieve, urlopen

from efl import ecore


def DBG(msg):
    # print('DOWNLOADER: %s' % msg)
    pass


NUM_WORKER_THREADS = 3

_threads = list()
_timer: ecore.Timer
Q1 = Queue()
Q2 = Queue()


def init():
    global _threads
    global _timer

    # start the threads pool
    for i in range(NUM_WORKER_THREADS):
        DBG('Start job ' + str(i))
        t = threading.Thread(name='DwnlTrd-' + str(i), target=_download_worker)
        t.start()
        _threads.append(t)

    # add a timer to check the data returned by workers
    _timer = ecore.Timer(0.5, _check_q2)


def shutdown():
    global _threads
    global _timer

    print('Shutdown all downloader threads...')

    # tell all the threads to exit
    for i in range(NUM_WORKER_THREADS):
        Q1.put('exit')

    # wait until all the threads are done
    for t in _threads:
        t.join()
        del t
    print('done')

    # delete respond timer
    _timer.delete()


def download_url_async(url, dest='tmp',
                       complete_cb=None, progress_cb=None, min_size=0):
    """ Download the given url from a parallel thread.
        url must be a valid url to download
        If dest is set to a local file name then the download data will
          be written to that file (created and overwritten if necessary)
        If dest is omitted than the data will be written to a random new
          temp file
        If dest is set to None than the data will be passed as the dest param
          in the complete_cb
        complete_cb, if given, will be called when the download is done
           def complete_cb(url, dest, header):
        progress_cb will be called while the download proceed

        If min_size is set (and grater than 0) then downloaded data that
           is shorter than min_size will be discarted. (in byte)
    """

    # create dest dirs if necessary, or a random temp file
    if dest == 'tmp':
        dest = tempfile.mktemp()
    elif dest:
        path = os.path.dirname(dest)
        if not os.path.exists(path):
            os.makedirs(path)

    # put the request on the queue (a worker thread will take care of the job)
    Q1.put((url, dest, complete_cb, progress_cb, min_size))


def _download_worker():
    while True:
        # wait here until an item in the queue is present
        item = Q1.get()
        # print('worker ' + str(item))

        # quit the worker if requested
        if isinstance(item, str) and item == 'exit':
            return

        (url, dest, complete_cb, progress_cb, min_size) = item

        if dest:
            (filename, headers) = urlretrieve(url, dest)

            # check downloaded file size
            if os.path.getsize(filename) < min_size:
                # print('TOO SHORT ' + str(os.path.getsize(filename)))
                os.remove(filename)

        else:
            client = urlopen(url)
            filename = client.read()
            headers = ''
            client.close()

        # put the item in the second queue (_check_q2() will handle this, in the main thread)
        Q2.put((url, filename, headers, complete_cb))


def _check_q2():
    if not Q2.empty():
        item = Q2.get_nowait()
        (url, filename, headers, complete_cb) = item
        if complete_cb:
            complete_cb(url, filename, headers)
    return True
