# -*- coding: utf-8 -*-
"""
set $PGCTL_VERBOSE to get more output from pgctl

numbers higher than 1 will produce more output
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from os import environ
from sys import stderr

VERBOSE = environ.get('PGCTL_VERBOSE', '')

if VERBOSE:  # :pragma:nocover:
    try:
        VERBOSE = float(VERBOSE)
    except ValueError:
        VERBOSE = 1
else:
    VERBOSE = 0


def debug(msg, *args, **kwargs):
    level = kwargs.pop('level', 1)
    if level <= VERBOSE:  # pragma: no cover
        print('[pgctl] DEBUG:', msg % args, file=stderr)
        stderr.flush()


def trace(msg, *args):
    debug(msg, *args, level=3)
