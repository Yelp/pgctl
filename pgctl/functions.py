"""miscellany pgctl functions"""
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import os

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


def uniq(iterable):
    """remove duplicates while preserving ordering -- first one wins"""
    return tuple(_uniq(iterable))


def _uniq(iterable):
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
    if relto is None:
        from os import getcwd
        relto = getcwd()
    from os.path import relpath
    relpath = relpath(path, relto)
    if len(relpath) < len(path):
        return relpath
    else:
        return path


def lsof(path):
    from subprocess import STDOUT, Popen, PIPE
    cmd = 'lsof -tau $(whoami) {} | xargs -r ps -fj'.format(path)
    p = Popen(('sh', '-c', cmd), stdout=PIPE, stderr=STDOUT)
    stdout, _ = p.communicate()
    if stdout.count('\n') > 1:
        return stdout
    else:
        # race condition: we only got the ps -f header
        return ''


def check_lock(path):
    locks = lsof(path)
    if locks:
        raise LockHeld(
            '''\
The supervisor has stopped, but these processes did not:
%s
temporary fix: lsof -t %s | xargs kill -9
permanent fix: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services
''' % (locks, bestrelpath(path))
        )
    else:
        pass


def commafy(items):
    return ', '.join(str(x) for x in items)
