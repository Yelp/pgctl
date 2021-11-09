"""miscellany pgctl functions"""
import json
import os
import signal
import sys
import typing

from frozendict import frozendict

from .errors import LockHeld


class StreamFileDescriptor:
    """For some reason, Python neglected to put this in the standard lib."""
    STDIN = 0
    STDOUT = 1
    STDERR = 2


def exec_(argv, env=None):  # never returns
    """Wrapper to os.execv which runs any atexit handlers (for coverage's sake).
    Like os.execv, this function never returns.
    """
    if env is None:
        env = os.environ

    # in python3, sys.exitfunc has gone away, and atexit._run_exitfuncs seems to be the only pubic-ish interface
    #   https://hg.python.org/cpython/file/3.4/Modules/atexitmodule.c#l289
    import atexit
    atexit._run_exitfuncs()
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

    def default(self, o):
        if isinstance(o, frozendict):
            return dict(o)
        else:
            # Let the base class default method raise the TypeError
            return json.JSONEncoder.default(self, o)


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
    pids = tuple(str(pid) for pid in pids)
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
{}
This usually means these processes are buggy.
Normally pgctl would kill these automatically for you, but you specified the --no-force option.
Learn more: https://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services
'''.format(processes)
        )


def terminate_processes(pids: typing.Iterable[int], is_stop: bool = True) -> typing.Optional[str]:
    """forcefully kill processes"""
    processes = ps(pids)
    if processes:
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:  # pragma: no cover
                # race condition: processes stopped slightly after timeout, before we kill it
                pass

        if is_stop:
            return '''WARNING: Killing these runaway processes which did not stop:
{}
This usually means these processes are buggy.
Learn more: https://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services
'''.format(processes)
        else:
            return '''WARNING: Killing these processes which were still running but escaped supervision:
{}
This usually means that s6-supervise was not stopped cleanly (e.g. manually killed).
Learn more: https://pgctl.readthedocs.io/en/latest/user/usage.html#stop
'''.format(processes)


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


def logger_preexec(log_path):
    """Pre exec func. for starting the logger process for a service.

    Before execing the logger service (s6-log), connect stdin to the logging
    FIFO so that it reads log lines from the service, and connect stdout/stderr
    to the void since we ignore the logger's console output.
    (The logger writes actual log output to files in $SERVICE_DIR/logs.)

    :param log_path: path to the logging FIFO
    """
    # Even though this is technically RDONLY, we open
    # it as RDWR to avoid blocking
    #
    # http://bugs.python.org/issue10635
    log_fifo_reader = os.open(log_path, os.O_RDWR)
    devnull = os.open(os.devnull, os.O_WRONLY)

    os.dup2(log_fifo_reader, StreamFileDescriptor.STDIN)
    os.dup2(devnull, StreamFileDescriptor.STDOUT)
    os.dup2(devnull, StreamFileDescriptor.STDERR)

    os.close(log_fifo_reader)
    os.close(devnull)


def supervisor_preexec(log_path):
    """Pre exec func. for starting a service.

    Before execing the service, attach the output streams of the supervised
    process to the logging FIFO so that they will be logged to a file by the
    service's logger (s6-log). Also, attach the service's stdin to the void
    since it's running in a supervised context (and shouldn't have any data
    going to stdin).

    :param log_path: path to the logging pipe
    """
    # Should be WRONLY, but we can't block (see logger_preexec)
    log_fifo_writer = os.open(log_path, os.O_RDWR)

    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, StreamFileDescriptor.STDIN)
    os.dup2(log_fifo_writer, StreamFileDescriptor.STDOUT)
    os.dup2(log_fifo_writer, StreamFileDescriptor.STDERR)

    os.close(log_fifo_writer)
    os.close(devnull)
