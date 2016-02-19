"""normalize python2/3 subprocess calls"""
from __future__ import absolute_import
from __future__ import unicode_literals

import functools
import subprocess


def set_defaults(func, **defaults):
    @functools.wraps(func)
    def wrapped(cmd, **kwargs):
        kwargs = dict(defaults, **kwargs)
        return func(cmd, **kwargs)
    return wrapped


call = set_defaults(subprocess.call, close_fds=False)
check_call = set_defaults(subprocess.check_call, close_fds=False)
Popen = set_defaults(subprocess.Popen, close_fds=False)

PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
CalledProcessError = subprocess.CalledProcessError
