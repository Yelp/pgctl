# -*- coding: utf-8 -*-
# TODO: open source this thing?
"""
General handling of POSIX file locks (flocks).

This is meant to be entirely general purpose.
pgctl-specific functionality belongs elsewhere.

TODO: put this in its own package?
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import fcntl
import os
from contextlib import contextmanager

import six


class Locked(IOError):
    pass


def set_fd_inheritable(fd, inheritable):
    """
    disable the "inheritability" of a file descriptor

    See Also:
        https://docs.python.org/3/library/os.html#inheritance-of-file-descriptors
        https://github.com/python/cpython/blob/65e6c1eff3/Python/fileutils.c#L846-L857
    """
    from fcntl import ioctl
    if inheritable:
        from termios import FIONCLEX
        return ioctl(fd, FIONCLEX)
    else:
        from termios import FIOCLEX
        return ioctl(fd, FIOCLEX)


def _acquire_fail(path):
    six.reraise(Locked, Locked(path))


def acquire(file_or_dir, on_fail=_acquire_fail):
    """raises flock.Locked on failure"""
    try:
        fd = os.open(file_or_dir, os.O_CREAT)
    except OSError as error:
        if error.errno == 21:  # is a directory
            fd = os.open(file_or_dir, 0)
        else:
            raise

    try:
        # exclusive, nonblocking
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError as error:
        if error.errno == 11:
            release(fd)
            return on_fail(file_or_dir)
        else:
            raise

    set_fd_inheritable(fd, True)
    return fd


def release(lock):
    os.close(lock)


@contextmanager
def flock(file_or_dir, **acquire_args):
    """A context for flock.acquire()."""
    fd = None
    while fd is None:
        fd = acquire(file_or_dir, **acquire_args)
    try:
        yield fd
    finally:
        os.close(fd)

# handy alias =X
flock.Locked = Locked
