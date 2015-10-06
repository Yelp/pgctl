# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from os import environ
from sys import stderr

VERBOSE = environ.get('PGCTL_VERBOSE', '')


def debug(msg, *args):
    if VERBOSE:
        print('[pgctl] DEBUG:', msg % args, file=stderr)  # pragma: no cover
