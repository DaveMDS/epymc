#!/usr/bin/env python

import os
import urllib
import tempfile
import threading
import Queue

import ecore

NUM_WORKER_THREADS = 3

_threads = list()
_timer = None
Q1 = Queue.Queue()
Q2 = Queue.Queue()

def init():
    global _threads
    global _timer

    # start the threads pool
    for i in range(NUM_WORKER_THREADS):
        print "Start job " + str(i)
        t = threading.Thread(name='DwnlTrd-'+str(i), target=_download_worker)
        t.start()
        _threads.append(t)

    # add a timer to check the data returned by workers
    _timer = ecore.Timer(0.5, _check_q2)

def shutdown():
    global _threads
    global _timer

    print "Shutdown all downloader threads"

    # tell all the threads to exit
    for i in range(NUM_WORKER_THREADS):
        Q1.put("exit")

    # wait until all the threads are done
    for t in _threads:
        t.join()
        del t

    # delete respond timer
    _timer.delete()

def download_url_async(url, dest = 'tmp',
                       complete_cb = None, progress_cb = None, min_size = 0):
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
        if min_size is set the downloaded data that is shorter than min_size
           will be discarted
    """

    # create dest dirs if necessary, or a random temp file
    if dest == 'tmp':
        dest = tempfile.mktemp()
    elif dest:
        dir = os.path.dirname(dest)
        if not os.path.exists(dir):
            os.makedirs(dir)

    # put the request on the queue (a worker thread will take care of the job)
    Q1.put((url, dest, complete_cb, progress_cb, min_size))


def _download_worker():
    while True:
        # wait here until an item in the queue is present
        item = Q1.get()
        #~ print "worker " + str(item)

        # quit the worker if requested
        if isinstance(item, str) and item == 'exit':
            print 'Download worker END'
            return

        (url, dest, complete_cb, progress_cb, min_size) = item

        (filename, headers) = urllib.urlretrieve(url, dest)
        # TODO check download result

        # check downloaded file size
        if os.path.getsize(filename) < min_size:
            #~ print "TOO SHORT " + str(os.path.getsize(filename))
            os.remove(filename)

        # put the item in the second queue (_check_q2() will handle this, in the main thread)
        Q2.put((url, filename, headers, complete_cb))


def _check_q2():
    if not Q2.empty():
        item = Q2.get_nowait()
        (url, filename, headers, complete_cb) = item
        if complete_cb:
            complete_cb(url, filename, headers)
    return True
