# pylint:disable=invalid-name
"""miscellany pgctl functions"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import json
import os
import sys

from frozendict import frozendict

from .errors import LockHeld


def exec_(argv, env=None):  # never returns
    """Wrapper to os.execv which runs any atexit handlers (for coverage's sake).
    Like os.execv, this function never returns.
    """
    if env is None:
        env = os.environ

    # in python3, sys.exitfunc has gone away, and atexit._run_exitfuncs seems to be the only pubic-ish interface
    #   https://hg.python.org/cpython/file/3.4/Modules/atexitmodule.c#l289
    import atexit
    atexit._run_exitfuncs()  # pylint:disable=protected-access
    os.execvpe(argv[0], argv, env)


def unique(iterable):
    """remove duplicates while preserving ordering -- first one wins"""
    return tuple(_unique(iterable))


def _unique(iterable):
    seen = set()
    for i in iterable:
        if i in seen:
            pass
        else:
            yield i
            seen.add(i)


class JSONEncoder(json.JSONEncoder):
    """knows that frozendict is like dict"""

    def default(self, obj):  # pylint:disable=method-hidden
        if isinstance(obj, frozendict):
            return dict(obj)
        else:
            # Let the base class default method raise the TypeError
            return json.JSONEncoder.default(self, obj)


def bestrelpath(path, relto=None):
    """Return a relative path only if it's under $PWD (or `relto`)"""
    if relto is None:
        from os import getcwd
        relto = getcwd()
    from os.path import relpath
    relpath = relpath(path, relto)
    if relpath.startswith('.'):
        return path
    else:
        return relpath


def ps(pids):
    """Give a (somewhat) human-readable printout of a list of processes"""
    pids = tuple([str(pid) for pid in pids])
    if not pids:
        return ''

    from .subprocess import PIPE, Popen
    cmd = ('ps', '--forest', '-wwfj',) + pids
    process = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, _ = process.communicate()
    stdout = stdout.decode('UTF-8')
    if stdout.count('\n') > 1:
        return stdout
    else:
        # race condition: we only got the ps -f header
        return ''  # pragma: no cover, we don't expect to hit this


def show_runaway_processes(path):
    from .fuser import fuser
    processes = ps(fuser(path))
    if processes:
        raise LockHeld(
            '''\
these runaway processes did not stop:
%s
There are two ways you can fix this:
  * temporarily: lsof -t %s | xargs kill -9
  * permanently: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services
''' % (processes, bestrelpath(path))
        )
    else:
        pass


def commafy(items):
    return ', '.join(str(x) for x in items)


def symlink_if_necessary(path, destination):
    """forcefully create a symlink with a given value, but only if it doesn't already exist"""
    # TODO-TEST
    from py._error import error as pylib_error
    try:
        supervise_link = destination.readlink()
    except (pylib_error.ENOENT, pylib_error.EINVAL):
        supervise_link = None

    if supervise_link != path.strpath:
        # TODO-TEST: a test that fails without -n
        from .subprocess import check_call
        check_call((
            'ln', '-sfn', '--',
            path.strpath,
            destination.strpath,
        ))


def print_stderr(s):
    # Sadness: https://bugs.python.org/issue13601
    print(s, file=sys.stderr)
    sys.stderr.flush()
