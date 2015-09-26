# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from subprocess import check_call
from subprocess import PIPE
from subprocess import Popen

import pytest
from pytest import yield_fixture as fixture
from testfixtures import StringComparison as S
from testing import assert_command
from testing import ctrl_c
from testing.assertions import assert_svstat
from testing.assertions import retry

from pgctl.daemontools import SvStat
from pgctl.errors import LockHeld
from pgctl.functions import check_lock

parametrize = pytest.mark.parametrize


class DescribePgctlLog(object):

    @fixture
    def service_name(self):
        yield 'output'

    def it_is_empty_before_anything_starts(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/ohhi/stdout.log <==

==> playground/ohhi/stderr.log <==

==> playground/sweet/stdout.log <==

==> playground/sweet/stderr.log <==
''',
            '',
            0,
        )

    def it_shows_stdout_and_stderr(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'sweet'))

        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/ohhi/stdout.log <==

==> playground/ohhi/stderr.log <==

==> playground/sweet/stdout.log <==
sweet

==> playground/sweet/stderr.log <==
sweet_error
''',
            '',
            0,
        )

        check_call(('pgctl-2015', 'restart', 'sweet'))

        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/ohhi/stdout.log <==

==> playground/ohhi/stderr.log <==

==> playground/sweet/stdout.log <==
sweet

==> playground/sweet/stderr.log <==
sweet_error
''',
            '',
            0,
        )

    def it_logs_continuously_when_run_interactively(self, in_example_dir):
        check_call(('pgctl-2015', 'start'))

        # this pty simulates running in a terminal
        read, write = os.openpty()
        pty_normalize_newlines(read)
        p = Popen(('pgctl-2015', 'log'), stdout=write, stderr=write)
        os.close(write)

        import fcntl
        fl = fcntl.fcntl(read, fcntl.F_GETFL)
        fcntl.fcntl(read, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        assert p.poll() is None  # it's still running

        # needs to loop for at least two seconds because the default event loop
        # in tail-f is one second.
        retries = 20
        buf = ''
        while True:
            try:
                block = os.read(read, 1024)
                print('BLOCK:', block)
            except OSError as error:
                print('ERROR:', error)
                if error.errno == 11:  # other end didn't write yet
                    if retries > 0:
                        retries -= 1
                        import time
                        time.sleep(.1)
                        continue
                    else:
                        break
                else:
                    raise
            buf += block

        assert buf == S('''(?s)\
==> playground/ohhi/stdout\\.log <==
o.*
==> playground/ohhi/stderr\\.log <==
e.*
==> playground/sweet/stdout\\.log <==
sweet

==> playground/sweet/stderr\\.log <==
sweet_error
.*$''')
        assert p.poll() is None  # it's still running

        p.terminate()

        assert p.wait() == -15

    def it_is_line_buffered(self):
        """
        Show that the interleaved output of ohhi becomes separated per-line.
        """

    def it_distinguishes_multiple_services(self):
        """
        There's some indication of which output came from which services.
        A (colorized?) [servicename] prefix.
        """

    def it_distinguishes_stderr(self):
        """
        There's some indication of which output came from stderr.
        Red, with [error] prefix.
        """

    def it_has_timestamps(self):
        """By default each line of output is timestamped"""

    def it_can_disable_timestamps(self):
        """Users should be able to turn off the timestamp output. V3"""

    def it_can_disable_coloring(self):
        """Users should be able to turn off colored output. V3"""

    def it_automatically_disables_color_for_nontty(self):
        """When printing to a file, don't produce color, by default. V3"""


class DescribeDateExample(object):

    @fixture
    def service_name(self):
        yield 'date'

    def it_does_start(self, in_example_dir, scratch_dir):
        assert not scratch_dir.join('now.date').isfile()
        check_call(('pgctl-2015', 'start', 'date'))
        retry(lambda: scratch_dir.join('now.date').isfile())


class DescribeTailExample(object):

    @fixture
    def service_name(self):
        yield 'tail'

    def it_does_start(self, in_example_dir):
        test_string = 'oh, hi there.\n'
        with open('input', 'w') as input:
            input.write(test_string)
        assert not os.path.isfile('output')

        check_call(('pgctl-2015', 'start', 'tail'))
        retry(lambda: os.path.isfile('output'))
        assert open('output').read() == test_string


class DescribeStart(object):

    def it_fails_given_unknown(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'start', 'unknown'),
            '',
            '''\
Starting: unknown
ERROR: No such playground service: 'unknown'
''',
            1,
        )

    def it_is_idempotent(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'sleep'))
        check_call(('pgctl-2015', 'start', 'sleep'))

    def it_should_work_in_a_subdirectory(self, in_example_dir):
        os.chdir(in_example_dir.join('playground').strpath)
        assert_command(
            ('pgctl-2015', 'start', 'sleep'),
            '',
            '''\
Starting: sleep
Started: sleep
''',
            0,
        )


class DescribeStop(object):

    def it_does_stop(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'sleep'))
        check_call(('pgctl-2015', 'stop', 'sleep'))

        assert_svstat('playground/sleep', state=SvStat.UNSUPERVISED)

    def it_is_successful_before_start(self, in_example_dir):
        check_call(('pgctl-2015', 'stop', 'sleep'))

    def it_fails_given_unknown(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'stop', 'unknown'),
            '',
            '''\
Stopping: unknown
ERROR: No such playground service: 'unknown'
''',
            1,
        )


def pty_normalize_newlines(fd):
    r"""
    Twiddle the tty flags such that \n won't get munged to \r\n.
    Details:
        https://docs.python.org/2/library/termios.html
        http://ftp.gnu.org/old-gnu/Manuals/glibc-2.2.3/html_chapter/libc_17.html#SEC362
    """
    import termios as T
    attrs = T.tcgetattr(fd)
    attrs[1] &= ~(T.ONLCR | T.OPOST)
    T.tcsetattr(fd, T.TCSANOW, attrs)


def read_line(fd):
    # read one-byte-at-a-time to avoid deadlocking by reading too much
    line = ''
    byte = None
    while byte not in ('\n', ''):
        byte = os.read(fd, 1).decode('utf-8')
        line += byte
    return line


class DescribeDebug(object):

    @fixture
    def service_name(self):
        yield 'greeter'

    def assert_works_interactively(self):
        read, write = os.openpty()
        pty_normalize_newlines(read)
        # setsid: this simulates the shell's job-control behavior
        proc = Popen(('setsid', 'pgctl-2015', 'debug', 'greeter'), stdin=PIPE, stdout=write)
        os.close(write)

        try:
            assert read_line(read) == 'What is your name?\n'
            proc.stdin.write('Buck\n')
            assert read_line(read) == 'Hello, Buck.\n'
        finally:
            ctrl_c(proc)

    def it_works_with_nothing_running(self, in_example_dir):
        assert_svstat('playground/greeter', state=SvStat.UNSUPERVISED)
        self.assert_works_interactively()

    def it_fails_with_multiple_services(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'debug', 'abc', 'def'),
            '',
            'ERROR: Must debug exactly one service, not: abc, def\n',
            1,
        )

    def it_first_stops_the_background_service_if_running(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'greeter'))
        assert_svstat('playground/greeter', state='up')

        self.assert_works_interactively()


class DescribeRestart(object):

    def it_is_just_stop_then_start(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'restart', 'sleep'),
            '',
            '''\
Stopping: sleep
Stopped: sleep
Starting: sleep
Started: sleep
''',
            0,
        )
        assert_svstat('playground/sleep', state='up')

    def it_also_works_when_up(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'sleep'))
        assert_svstat('playground/sleep', state='up')

        self.it_is_just_stop_then_start(in_example_dir)


class DescribeStartMultipleServices(object):

    @fixture
    def service_name(self):
        yield 'multiple'

    def it_only_starts_the_indicated_services(self, in_example_dir, request):
        check_call(('pgctl-2015', 'start', 'sleep'))

        assert_svstat('playground/sleep', state='up')
        assert_svstat('playground/tail', state=SvStat.UNSUPERVISED)

    def it_starts_multiple_services(self, in_example_dir, request):
        check_call(('pgctl-2015', 'start', 'sleep', 'tail'))

        assert_svstat('playground/sleep', state='up')
        assert_svstat('playground/tail', state='up')

    def it_stops_multiple_services(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'sleep', 'tail'))

        assert_svstat('playground/sleep', state='up')
        assert_svstat('playground/tail', state='up')

        check_call(('pgctl-2015', 'stop', 'sleep', 'tail'))

        assert_svstat('playground/sleep', state=SvStat.UNSUPERVISED)
        assert_svstat('playground/tail', state=SvStat.UNSUPERVISED)

    def it_starts_everything_with_no_arguments_no_config(self, in_example_dir, request):
        check_call(('pgctl-2015', 'start'))

        assert_svstat('playground/sleep', state='up')
        assert_svstat('playground/tail', state='up')


class DescribeStatus(object):

    @fixture
    def service_name(self):
        yield 'multiple'

    def it_displays_correctly_when_the_service_is_down(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'sleep'))
        check_call(('pgctl-2015', 'stop', 'sleep'))
        assert_command(
            ('pgctl-2015', 'status', 'sleep'),
            'sleep: down\n',
            '',
            0,
        )

    def it_displays_correctly_when_the_service_is_up(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'sleep'))
        assert_command(
            ('pgctl-2015', 'status', 'sleep'),
            S('sleep: ready \\(pid \\d+\\) \\d+ seconds\\n$'),
            '',
            0,
        )

    def it_displays_the_status_of_multiple_services(self, in_example_dir):
        """Expect multiple services with status and PID"""
        check_call(('pgctl-2015', 'start', 'sleep'))
        assert_command(
            ('pgctl-2015', 'status', 'sleep', 'tail'),
            S('''\
sleep: ready \\(pid \\d+\\) \\d+ seconds
tail: down
$'''),
            '',
            0,
        )

    def it_displays_the_status_of_all_services(self, in_example_dir):
        """Expect all services to provide status when no service is specified"""
        check_call(('pgctl-2015', 'start', 'tail'))
        assert_command(
            ('pgctl-2015', 'status'),
            S('''\
sleep: down
tail: ready \\(pid \\d+\\) \\d+ seconds
$'''),
            '',
            0,
        )

    def it_displays_status_for_unknown_services(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'status', 'garbage'),
            '',
            '''\
ERROR: No such playground service: 'garbage'
''',
            1,
        )


class DescribeReload(object):

    def it_is_unimplemented(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'reload'),
            '',
            '''\
reload: sleep
ERROR: reloading is not yet implemented.
''',
            1,
        )


class DescribeAliases(object):

    @fixture
    def service_name(self):
        yield 'output'

    def it_can_expand_properly(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'start', 'a'),
            '',
            '''\
Starting: ohhi, sweet
Started: ohhi, sweet
''',
            0,
        )

    def it_can_detect_cycles(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'start', 'b'),
            '',
            "ERROR: Circular aliases! Visited twice during alias expansion: 'b'\n",
            1,
        )

    def it_can_start_when_default_is_not_defined_explicitly(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'start'),
            '',
            '''\
Starting: ohhi, sweet
Started: ohhi, sweet
''',
            0,
        )


class DescribeEnvironment(object):

    @fixture
    def service_name(self):
        yield 'environment'

    def it_can_accept_different_environment_variables(self, in_example_dir):
        check_call(('sh', '-c', 'MYVAR=ohhi pgctl-2015 start'))

        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/environment/stdout.log <==
ohhi

==> playground/environment/stderr.log <==
''',
            '',
            0,
        )

        check_call(('sh', '-c', 'MYVAR=bye pgctl-2015 restart'))

        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/environment/stdout.log <==
bye

==> playground/environment/stderr.log <==
''',
            '',
            0,
        )


class DescribePgdirMissing(object):

    @parametrize(
        'command',
        ('start', 'stop', 'status', 'restart', 'reload', 'log', 'debug'),
    )
    def it_shows_an_error(self, command, tmpdir):
        with tmpdir.as_cwd():
            assert_command(
                ('pgctl-2015', command),
                '',
                "ERROR: could not find any directory named 'playground'\n",
                1,
            )

    def it_can_still_show_config(self, tmpdir):
        expected_output = '''\
{
    "aliases": {
        "default": [
            "(all services)"
        ]
    }, 
    "command": "config", 
    "pgdir": "playground", 
    "pghome": "~/.run/pgctl", 
    "poll": ".01", 
    "services": [
        "default"
    ], 
    "timeout": "2.0"
}
'''  # noqa

        with tmpdir.as_cwd():
            assert_command(
                ('pgctl-2015', 'config'),
                expected_output,
                '',
                0,
            )

    def it_can_still_show_help(self, tmpdir):
        with tmpdir.as_cwd():
            assert_command(
                ('pgctl-2015', '--help'),
                '''\
usage: pgctl-2015 [-h] [--version] [--pgdir PGDIR] [--pghome PGHOME]
                  {start,stop,status,restart,reload,log,debug,config}
                  [services [services ...]]

positional arguments:
  {start,stop,status,restart,reload,log,debug,config}
                        specify what action to take
  services              specify which services to act upon

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --pgdir PGDIR         name the playground directory
  --pghome PGHOME       directory to keep user-level playground state
''',
                '',
                0,
            )

    def it_still_shows_help_without_args(self, tmpdir):
        with tmpdir.as_cwd():
            assert_command(
                ('pgctl-2015'),
                '',
                '''\
usage: pgctl-2015 [-h] [--version] [--pgdir PGDIR] [--pghome PGHOME]
                  {start,stop,status,restart,reload,log,debug,config}
                  [services [services ...]]
pgctl-2015: error: too few arguments
''',
                2,
            )


class DirtyTest(object):

    LOCKERROR = '''\
Stopping: sweet
ERROR: service sweet timed out at {time} seconds: The supervisor has stopped, but these processes did not:
UID +PID +PPID +PGID +SID +C +STIME +TTY +STAT +TIME +CMD
\\S+ +\\d+ +\\d+ +\\d+ +\\d+ +\\d+ +\\S+ +\\S+ +\\S+ +\\S+ +{cmd}

temporary fix: lsof -t playground/sweet | xargs kill -9
permanent fix: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

Stopped: sweet
ERROR: Some services timed out.
$'''

    @fixture(autouse=True)
    def cleanup(self, in_example_dir):
        try:
            yield in_example_dir
        finally:
            # we use SIGTERM; SIGKILL is cheating.
            print('killing.')
            limit = 100
            while limit > 0:  # pragma: no cover: we don't expect to ever hit the limit
                try:
                    check_lock('playground/sweet')
                    break
                except LockHeld:
                    cmd = 'lsof -tau $(whoami) playground/sweet | xargs --replace kill -TERM {}'
                    Popen(('sh', '-c', cmd)).wait()
                    limit -= 1


class DescribeOrphanSubprocess(DirtyTest):

    @fixture
    def service_name(self):
        yield 'orphan-subprocess'

    def it_starts_up_fine(self):
        assert_command(
            ('pgctl-2015', 'start'),
            '',
            '''\
Starting: sweet
Started: sweet
''',
            0,
        )
        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/sweet/stdout.log <==
sweet

==> playground/sweet/stderr.log <==
sweet_error
''',
            '',
            0,
        )

    def it_shows_error_on_stop(self):
        assert_command(
            ('pgctl-2015', 'start'),
            '',
            '''\
Starting: sweet
Started: sweet
''',
            0,
        )
        assert_command(
            ('pgctl-2015', 'restart'),
            '',
            S(self.LOCKERROR.format(time='2', cmd='sleep infinity')),
            1,
        )


class DescribeSlowShutdown(DirtyTest):
    """This test case takes three seconds to shut down"""

    @fixture
    def service_name(self):
        yield 'slow-shutdown'

    @fixture(autouse=True)
    def environment(self):
        os.environ['PGCTL_TIMEOUT'] = '1.5'
        yield
        del os.environ['PGCTL_TIMEOUT']

    def it_fails_by_default(self):
        check_call(('pgctl-2015', 'start'))
        assert_svstat('playground/sweet', state='up')
        assert_command(
            ('pgctl-2015', 'stop'),
            '',
            S(self.LOCKERROR.format(time='1\\.5', cmd='sleep 2\\.25')),
            1,
        )

    def it_can_shut_down_successfully(self):
        # if we configure it to wait a bit longer, it works fine
        with open('playground/sweet/timeout', 'w') as timeout:
            timeout.write('3')

        check_call(('pgctl-2015', 'start'))
        assert_svstat('playground/sweet', state='up')

        check_call(('pgctl-2015', 'restart'))
        assert_svstat('playground/sweet', state='up')

        check_call(('pgctl-2015', 'stop'))
        assert_svstat('playground/sweet', state=SvStat.UNSUPERVISED)
