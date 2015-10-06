# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import Popen
from subprocess import STDOUT

from .debug import debug
from .errors import Unsupervised


def svc(args):
    """Wrapper for daemontools svc cmd"""
    # svc never writes to stdout.
    cmd = ('s6-svc',) + tuple(args)
    debug('CMD: %s', cmd)
    process = Popen(cmd, stderr=PIPE)
    _, error = process.communicate()
    if error.startswith('s6-svc: fatal: unable to control '):
        raise Unsupervised(cmd, error)
    if process.returncode:  # pragma: no cover: there's no known way to hit this.
        import sys
        sys.stderr.write(error)
        raise CalledProcessError(process.returncode, cmd)


class SvStat(
        namedtuple('SvStat', ['state', 'pid', 'exitcode', 'seconds', 'process'])
):
    __slots__ = ()
    UNSUPERVISED = 'could not get status, supervisor is down'
    INVALID = 'no such service'

    def __repr__(self):
        format = '{0.state}'
        if self.pid is not None:
            format += ' (pid {0.pid})'
        if self.exitcode is not None:
            format += ' (exitcode {0.exitcode})'
        if self.seconds is not None:
            format += ' {0.seconds} seconds'
        if self.process is not None:
            format += ', {0.process}'

        return format.format(self)


def svstat_string(service_path):
    """Wrapper for daemontools svstat cmd"""
    # svstat *always* exits with code zero...
    cmd = ('s6-svok', service_path)
    process = Popen(cmd, stdout=PIPE, stderr=STDOUT)
    status, _ = process.communicate()
    assert status == ''
    if process.returncode != 0:
        return SvStat.UNSUPERVISED

    cmd = ('s6-svstat', service_path)
    process = Popen(cmd, stdout=PIPE, stderr=STDOUT)
    status, _ = process.communicate()

    #status is listed per line for each argument
    return status


def svstat_parse(svstat_string):
    r'''
    >>> svstat_parse('down (exitcode 0) 0 seconds, normally up, want up, ready 0 seconds')
    down (exitcode 0) 0 seconds, starting

    >>> svstat_parse('up (pid 3714560) 13 seconds, normally down, ready 7 seconds\n')
    ready (pid 3714560) 7 seconds

    >>> svstat_parse('up (pid 1202562) 100 seconds, ready 10 seconds\n')
    ready (pid 1202562) 10 seconds

    >>> svstat_parse('up (pid 1202562) 100 seconds\n')
    up (pid 1202562) 100 seconds

    >>> svstat_parse('down 4334 seconds, normally up, want up')
    down 4334 seconds, starting

    >>> svstat_parse('down 0 seconds, normally up')
    down 0 seconds

    >>> svstat_parse('up (pid 1202) 1 seconds, want down\n')
    up (pid 1202) 1 seconds, stopping

    >>> svstat_parse('down 0 seconds, normally up')
    down 0 seconds

    >>> svstat_parse('down 0 seconds, normally up')
    down 0 seconds

    >>> svstat_parse('s6-svstat: fatal: unable to read status for wat: No such file or directory')
    could not get status, supervisor is down

    >>> svstat_parse("s6-svstat: fatal: unable to read status for sweet: Broken pipe\n")
    could not get status, supervisor is down

    >>> svstat_parse('unable to chdir: file does not exist')
    no such service

    >>> svstat_parse('totally unpredictable error message')
    totally unpredictable error message
    '''
    status = svstat_string.strip()
    orig_status = status
    debug('RAW   : %s', status)
    state, status = __get_state(status)
    if state == SvStat.INVALID:
        return SvStat(state, None, None, None, None)

    if status.startswith('(pid '):
        pid, status = status[5:].split(') ', 1)
        pid = int(pid)
    else:
        pid = None

    if status.startswith('(exitcode '):
        exitcode, status = status[10:].split(') ', 1)
        exitcode = int(exitcode)
    else:
        exitcode = None

    if status.startswith('(signal '):
        _, status = status.split(') ', 1)

    try:
        seconds, status = status.split(' seconds', 1)
        status = status.lstrip(', ')
        seconds = int(seconds)
    except ValueError:
        seconds = None

    if status.startswith('normally '):
        try:
            # we actually dont care about this value
            _, status = status.split(', ', 1)
        except ValueError:  # sometimes there is no comma
            status = ''

    if status.startswith('want '):
        try:
            process, status = status.split(', ', 1)
        except ValueError:
            process, status = status, ''
        if process == 'want up':
            process = 'starting'
        elif process == 'want down':
            process = 'stopping'
    else:
        process = None

    if status.startswith('ready '):
        if state == 'up':
            state = 'ready'
        status = status[6:]
        seconds, status = status.split(' seconds', 1)
        seconds = int(seconds)

    assert status == '', (status, orig_status)  # we parsed it all.
    return SvStat(state, pid, exitcode, seconds, process)


def __get_state(status):
    first, rest = status.split(None, 1)
    if first in ('up', 'down'):
        return first, rest
    elif status.startswith('unable to chdir:'):
        return SvStat.INVALID, status
    elif (
            status.startswith('s6-svstat: fatal: unable to read status for ') and status.endswith((
                ': No such file or directory',
                ': Broken pipe',
            ))
    ):
        # the service has never been started before; it's down.
        return SvStat.UNSUPERVISED, ''
    else:  # unknown errors
        return status, ''


def svstat(path):
    return svstat_parse(svstat_string(path))
