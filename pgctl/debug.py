# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from os import environ
from sys import stderr

DEBUG = environ.get('PGCTL_DEBUG', '')


def debug(msg, *args):
    if DEBUG:
        print('DEBUG:', msg % args, file=stderr)  # pragma: no cover
