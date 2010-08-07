#!/usr/bin/env python

import os
import shelve

import ecore
import Queue

import utils


class EmcDatabase(object):
    """ TODO doc this """

    def __init__(self, name):
        file = os.path.join(utils.config_dir_get(), 'db_' + name)
        print 'Open DB: ' + name + '  from file: ' + file
        self.__sh = shelve.open(file)
        self.__name = name

    def __del__(self):
        self.__sh.close()

    def get_data(self, id):
        print 'Get Data on db ' + self.__name + ', id: ' + id
        return self.__sh[id]

    def set_data(self, id, data, thread_safe = False):
        print 'Set data for db ' + self.__name + ', id: ' + id
        if thread_safe:
            # just put in queue
            pass
        else:
            self.__sh[id] = data
            self.__sh.sync() # TODO really sync at every vrite ??

    def del_data(self, db, id):
        if self.__sh.has_key(id):
            del self.__sh[id]

    def id_exists(self, id):
        return self.__sh.has_key(id)

    def keys(self):
        return self.__sh.keys()

##################


def init():
    global __queue
    global __queue_timer

    __queue = Queue.Queue()
    __queue_timer = ecore.Timer(2.0, __process_queue)

def shutdown():
    global __queue
    global __queue_timer

    __queue_timer.delete()
    del __queue

def __process_queue():
    global __queue

    #~ print 'Queue processing...'
    return True
