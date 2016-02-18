#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""stolen from aactivator"""
# TODO: package and share
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import stat

log = logging.getLogger(__name__)


def get_filesystem_id(path):
    return os.stat(path).st_dev


def insecure(path):
    """Can this path can be altered by someone other than the owner (or root)?"""
    # TODO: return the reason it's insecure, and have caller print warning
    from os.path import isdir
    pathstat = os.stat(path)
    mode = pathstat.st_mode
    owner = pathstat.st_uid
    # Directories with a sticky bit are acceptable.
    if mode & stat.S_ISVTX and isdir(path):
        pass
    # The path is writable by a group or by everyone.
    elif mode & (stat.S_IWGRP | stat.S_IWOTH):
        return path
    # If the file is owned by me (or root) at this point, we're good.
    elif owner == 0 or owner == os.getuid():
        pass
    # Otherwise, no dice.
    else:
        return path


def search_parent_directories(path='.'):
    from os.path import abspath, dirname
    path = abspath(path)
    original_fs_id = fs_id = get_filesystem_id(path)
    previous_path = None

    while original_fs_id == fs_id and path != previous_path:
        yield path
        previous_path = path
        path = dirname(path)
        fs_id = get_filesystem_id(path)


def any_insecure_path_segment(path):
    for segment in search_parent_directories(path):
        if insecure(segment):
            log.debug('insecure path segment: %r -> %r', path, segment)
            return segment


def glob(pattern):
    from glob import glob
    for fname in sorted(glob(pattern)):
        if not any_insecure_path_segment(fname):
            yield fname


def parentglob(pattern, path='.'):
    from os.path import join
    for parent_dir in search_parent_directories(path):
        for found in glob(join(parent_dir, pattern)):
            yield found


def main():
    from sys import argv
    for pattern in argv[1:]:
        for found in parentglob(pattern):
            print(found)


if __name__ == '__main__':
    exit(main())
