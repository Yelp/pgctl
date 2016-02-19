# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple

from .debug import trace
from .errors import Unsupervised
from .subprocess import CalledProcessError
from .subprocess import PIPE
from .subprocess import Popen
from .subprocess import STDOUT


def svc(args):
    """Wrapper for daemontools svc cmd"""
    # svc never writes to stdout.
    cmd = ('s6-svc',) + tuple(args)
    trace('CMD: %s', cmd)
    process = Popen(cmd, stderr=PIPE)
    _, error = process.communicate()
    if error.startswith(b's6-svc: fatal: unable to control '):
        raise Unsupervised(cmd, error)
    if process.returncode:  # pragma: no cover: there's no known way to hit this.
        import sys
        sys.stderr.write(error.decode('UTF-8'))
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


def svok(path):
    return Popen(('s6-svok', path)).wait() == 0


def svstat_string(service_path):
    """Wrapper for daemontools svstat cmd"""
    # svstat *always* exits with code zero...
    if not svok(service_path):
        return SvStat.UNSUPERVISED

    cmd = ('s6-svstat', service_path)
    process = Popen(cmd, stdout=PIPE, stderr=STDOUT)
    status, _ = process.communicate()
    status = status.decode('UTF-8')

    #status is listed per line for each argument
    return status


def parse(string, start, divider, type=str):
    """general purpose tokenizer, used below"""
    if string.startswith(start):
        string = string[len(start):]
        try:
            result, string = string.split(divider, 1)
        except ValueError:
            # if there's no separator found and we found the `start` token, the whole input is the result
            result, string = string, ''
    else:
        result = None
    if result is not None:
        result = type(result)
    return result, string


def svstat_parse(svstat_string):
    r'''
    >>> svstat_parse('up (pid 3714560) 13 seconds, normally down, ready 7 seconds\n')
    ready (pid 3714560) 7 seconds

    >>> svstat_parse('up (pid 1202562) 100 seconds, ready 10 seconds\n')
    ready (pid 1202562) 10 seconds

    >>> svstat_parse('up (pid 1202562) 100 seconds\n')
    up (pid 1202562) 100 seconds

    >>> svstat_parse('down 4334 seconds, normally up, want up')
    down 4334 seconds, starting

    >>> svstat_parse('down (exitcode 0) 0 seconds, normally up, want up, ready 0 seconds')
    down (exitcode 0) 0 seconds, starting

    >>> svstat_parse('down 0 seconds, normally up')
    down 0 seconds

    >>> svstat_parse('up (pid 1202) 1 seconds, want down\n')
    up (pid 1202) 1 seconds, stopping

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

    >>> svstat_parse('down (exitcode 0) 0 seconds, normally up, want wat, ready 0 seconds')
    Traceback (most recent call last):
        ...
    ValueError: unexpected value for `process`: 'wat'

    >>> svstat_parse('down (exitcode 0) 0 seconds, normally up, want up\x00, ready 0 seconds')
    down (exitcode 0) 0 seconds, starting
    '''
    status = svstat_string.strip()
    trace('RAW   : %s', status)
    if status.startswith(('up ', 'down ')):
        state, buffer = parse(status, '', ' ')
    elif status.startswith('unable to chdir:'):
        return SvStat(SvStat.INVALID, None, None, None, None)
    elif (
            status.startswith('s6-svstat: fatal: unable to read status for ') and status.endswith((
                ': No such file or directory',
                ': Broken pipe',
            ))
    ):
        # the service has never been started before; it's down.
        return SvStat(SvStat.UNSUPERVISED, None, None, None, None)
    else:  # unknown errors
        return SvStat(status, None, None, None, None)

    pid, buffer = parse(buffer, '(pid ', ') ', int)
    exitcode, buffer = parse(buffer, '(exitcode ', ') ', int)
    _, buffer = parse(buffer, '(signal ', ') ')

    seconds, buffer = parse(buffer, '', ' seconds', int)
    buffer = buffer.lstrip(', ')

    # we actually dont care about this value
    _, buffer = parse(buffer, 'normally ', ', ')

    process, buffer = parse(buffer, 'want ', ', ')
    if process is not None:
        process = process.strip('\x00')  # s6 microbug
        if process == 'up':
            process = 'starting'
        elif process == 'down':
            process = 'stopping'
        else:
            raise ValueError("unexpected value for `process`: '%s'" % process)

    ready, buffer = parse(buffer, 'ready ', ' seconds', int)
    if ready is not None and state == 'up':
        state = 'ready'
        seconds = ready

    assert buffer == '', (buffer, status)  # we parsed it all.
    return SvStat(state, pid, exitcode, seconds, process)


def prepend_timestamps_to(logfile):
    """write a timestamped log to a file. The return value is a file descriptor to write to."""
    timestamps = _pipeline(('pgctl-timestamp'), PIPE, logfile)
    return timestamps.stdin


def _pipeline(cmd, stdin, stdout):
    return Popen(
        cmd,
        stdin=stdin,
        stdout=stdout,
        # prevents deadlock undertest where the framework wants to read exhaustively from stderr
        stderr=STDOUT,
        # we don't need/want to maintain a lock here, because we'll die when our input pipe closes
        close_fds=True,
    )


def svstat(path):
    return svstat_parse(svstat_string(path))
