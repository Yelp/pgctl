# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import Popen


class NoSuchService(Exception):
    pass


def svc(args):
    """Wrapper for daemontools svc cmd"""
    # svc never writes to stdout.
    cmd = ('svc',) + tuple(args)
    process = Popen(cmd, stderr=PIPE)
    _, error = process.communicate()
    if 'unable to chdir' in error:
        raise NoSuchService(error)
    if process.returncode:  # pragma: no cover: there's no known way to hit this.
        import sys
        sys.stderr.write(error)
        raise CalledProcessError(process.returncode, cmd)


class SvStat(
        namedtuple('SvStat', ['name', 'state', 'pid', 'seconds', 'process'])
):
    UNSUPERVISED = 'could not get status, supervisor is down'
    INVALID = 'no such service'

    def __repr__(self):
        format = '{0.name}: {0.state}'
        if self.pid is not None:
            format += ' (pid {0.pid})'
        if self.seconds is not None:
            format += ' {0.seconds} seconds'
        if self.process is not None:
            format += ', {0.process}'

        return format.format(self)


def svstat_string(args):
    """Wrapper for daemontools svstat cmd"""
    # svstat *always* exits with code zero...
    cmd = ('svstat',) + tuple(args)
    process = Popen(cmd, stdout=PIPE)
    status, _ = process.communicate()

    #status is listed per line for each argument
    return status


def svstat_parse(svstat_string):
    r'''
    >>> svstat_parse('date: up (pid 1202562) 100 seconds\n')
    date: up (pid 1202562) 100 seconds

    >>> svstat_parse('date: down 4334 seconds, normally up, want up')
    date: down 4334 seconds, starting

    >>> svstat_parse('playground/date: down 0 seconds, normally up')
    playground/date: down 0 seconds

    >>> svstat_parse('date: up (pid 1202) 1 seconds, want down\n')
    date: up (pid 1202) 1 seconds, stopping

    >>> svstat_parse('playground/date: down 0 seconds, normally up')
    playground/date: down 0 seconds

    >>> svstat_parse('playground/date: down 0 seconds, normally up')
    playground/date: down 0 seconds

    >>> svstat_parse('docs: unable to open supervise/ok: file does not exist')
    docs: could not get status, supervisor is down

    >>> svstat_parse("date: supervise not running\n")
    date: could not get status, supervisor is down

    >>> svstat_parse('d: unable to chdir: file does not exist')
    d: no such service

    >>> svstat_parse('d: totally unpredictable error message')
    d: totally unpredictable error message
    '''
    status = svstat_string.strip()
    name, status = status.split(': ', 1)

    first, rest = status.split(None, 1)
    if first in ('up', 'down'):
        state, status = first, rest
    elif status.startswith('unable to chdir:'):
        state, status = SvStat.INVALID, rest
    elif status.startswith((
            'unable to open supervise/ok:',
            'supervise not running',
    )):
        state, status = SvStat.UNSUPERVISED, rest
    else:  # unknown errors
        state, status = status, ''

    if status.startswith('(pid '):
        pid, status = status[4:].rsplit(') ', 1)
        pid = int(pid)
    else:
        pid = None

    try:
        seconds, status = status.split(' seconds', 1)
        seconds = int(seconds)
    except ValueError:
        seconds = None

    if status.endswith(', want up'):
        process = 'starting'
    elif status.endswith(', want down'):
        process = 'stopping'
    else:
        process = None

    return SvStat(name, state, pid, seconds, process)


def svstat(*args):
    return [
        svstat_parse(line)
        for line in svstat_string(args).splitlines()
    ]
