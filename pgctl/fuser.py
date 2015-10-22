#!/usr/bin/env python2.7
# pylint:disable=missing-docstring,invalid-name,redefined-outer-name,too-few-public-methods
"""\
usage: pgctl-fuser file [file ...]

Shows the pids (of the current user) that have this file opened.
This is useful for finding which processes hold a file lock (flock).
This has the same behavior as `lsof -t file`, but is *much* faster.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from .debug import trace


def stat(path):
    from os import stat
    try:
        path = stat(path)
    except EnvironmentError as error:
        trace('fuser suppressed: %s', error)
        return None
    else:
        return (path.st_ino, path.st_dev)


def listdir(path):
    from os import listdir
    try:
        return listdir(path)
    except EnvironmentError as error:
        trace('fuser suppressed: %s', error)
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
    try:
        path = argv[1]
    except IndexError:
        return __doc__

    for pid in fuser(path):
        print(pid)


if __name__ == '__main__':
    exit(main())
