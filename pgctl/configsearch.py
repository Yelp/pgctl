#!/usr/bin/env python
# -*- coding: UTF-8 -*-
## stolen from aactivator
# TODO: package and share
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import stat
import os
from os.path import (
    abspath,
    dirname,
    isdir,
    join,
)


def get_filesystem_id(path):
    return os.stat(path).st_dev


def insecure(path):
    """This path can be altered by someone other than the owner"""
    pathstat = os.stat(path).st_mode
    # Directories with a sticky bit are acceptable.
    if isdir(path) and pathstat & stat.S_ISVTX:
        pass
    # The path is writable by someone who is not us.
    elif pathstat & (stat.S_IWGRP | stat.S_IWOTH):
        return path


def search_parent_directories(path, predicate):
    original_fs_id = fs_id = get_filesystem_id(path)
    previous_path = None

    while original_fs_id == fs_id and path != previous_path:
        result = predicate(path)
        if result:
            yield result
        previous_path = path
        path = dirname(path)
        fs_id = get_filesystem_id(path)


def glob_exists(fname):
    def predicate(path):
        from glob import glob
        return glob(join(path, fname))
    return predicate


def configsearch(fname, starting_path='.'):
    starting_path = abspath(starting_path)
    for foundlist in search_parent_directories(starting_path, glob_exists(fname)):
        for found in foundlist:
            if not any(search_parent_directories(found, insecure)):
                yield found


def main():
    from sys import argv
    for fname in argv[1:]:
        for found in configsearch(fname):
            print(found)


if __name__ == '__main__':
    exit(main())
