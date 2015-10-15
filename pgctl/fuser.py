#!/usr/bin/env python2.7
# pylint:disable=missing-docstring,invalid-name,redefined-outer-name,too-few-public-methods
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from .debug import debug

NO_SUCH_FILE = OSError(2, 'No such file.')
PERMISSION_DENIED = OSError(13, 'Permission denied.')


def stat(path):
    from os import stat
    try:
        path = stat(path)
    except EnvironmentError as error:
        debug('fuser suppressed:', error)
        return None
    else:
        return (path.st_ino, path.st_dev)


def listdir(path):
    from os import listdir
    try:
        return listdir(path)
    except EnvironmentError as error:
        debug('fuser suppressed:', error)
        return ()


def fuser(path):
    """Return the list of pids that have 'path' open, for the current user"""
    search = stat(path)
    if search is None:
        return

    from glob import glob
    for fddir in glob('/proc/*/fd/'):
        try:
            pid = int(fddir.split('/', 3)[2])
        except ValueError:
            continue

        fds = listdir(fddir)
        for fd in fds:
            from os.path import join
            fd = join(fddir, fd)
            found = stat(fd)
            if found == search:
                yield pid
                break


def main():
    from sys import argv
    path = argv[1]

    for pid in fuser(path):
        print(pid)


if __name__ == '__main__':
    exit(main())
