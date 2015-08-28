# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from subprocess import check_call
from subprocess import PIPE
from subprocess import Popen

from pytest import yield_fixture as fixture
from testfixtures import Comparison as C
from testfixtures import StringComparison as S
from testing import run
from testing.assertions import retry

from pgctl.cli import SvStat
from pgctl.cli import svstat


class DescribePgctlLog(object):

    @fixture
    def service_name(self):
        yield 'output'

    def it_is_empty_before_anything_starts(self, in_example_dir):
        p = Popen(('pgctl-2015', 'log'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stderr == ''
        assert stdout == '''\
==> ohhi/stdout.log <==

==> ohhi/stderr.log <==

==> sweet/stdout.log <==

==> sweet/stderr.log <==
'''
        assert p.returncode == 0

    def it_shows_stdout_and_stderr(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'sweet'))

        p = Popen(('pgctl-2015', 'log'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stderr == ''
        assert stdout == '''\
==> ohhi/stdout.log <==

==> ohhi/stderr.log <==

==> sweet/stdout.log <==
sweet

==> sweet/stderr.log <==
sweet_error
'''
        assert p.returncode == 0

        check_call(('pgctl-2015', 'restart', 'sweet'))

        p = Popen(('pgctl-2015', 'log'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stderr == ''
        assert stdout == '''\
==> ohhi/stdout.log <==

==> ohhi/stderr.log <==

==> sweet/stdout.log <==
sweet

==> sweet/stderr.log <==
sweet_error
'''
        assert p.returncode == 0

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
==> ohhi/stdout\\.log <==
o.*
==> ohhi/stderr\\.log <==
e.*
==> sweet/stdout\\.log <==
sweet

==> sweet/stderr\\.log <==
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
        try:
            retry(lambda: scratch_dir.join('now.date').isfile())
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))


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
        try:
            retry(lambda: os.path.isfile('output'))
            assert open('output').read() == test_string
        finally:
            check_call(('pgctl-2015', 'stop', 'tail'))


class DescribeStart(object):

    def it_fails_given_unknown(self, in_example_dir):
        p = Popen(('pgctl-2015', 'start', 'unknown'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == ''
        assert stderr == (
            'Starting: unknown\n'
            "No such playground service: 'unknown'\n"
        )
        assert p.returncode == 1

    def it_is_idempotent(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            check_call(('pgctl-2015', 'start', 'date'))
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_should_work_in_a_subdirectory(self, in_example_dir):
        os.chdir(in_example_dir.join('playground').strpath)
        p = Popen(('pgctl-2015', 'start', 'date'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert p.returncode == 0
        assert stdout == ''
        assert stderr == '''\
Starting: date
Started: date
'''


class DescribeStop(object):

    def it_does_stop(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        check_call(('pgctl-2015', 'stop', 'date'))

        assert svstat('playground/date') == [C(SvStat, state=SvStat.UNSUPERVISED)]

    def it_is_successful_before_start(self, in_example_dir):
        check_call(('pgctl-2015', 'stop', 'date'))

    def it_fails_given_unknown(self, in_example_dir):
        p = Popen(('pgctl-2015', 'stop', 'unknown'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == ''
        assert stderr == (
            'Stopping: unknown\n'
            "No such playground service: 'unknown'\n"
        )
        assert p.returncode == 1


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
        proc = Popen(('pgctl-2015', 'debug', 'greeter'), stdin=PIPE, stdout=write)
        os.close(write)

        try:
            assert read_line(read) == 'What is your name?\n'
            proc.stdin.write('Buck\n')
            assert read_line(read) == 'Hello, Buck.\n'

            # the service should re-start
            assert read_line(read) == 'What is your name?\n'
        finally:
            proc.kill()

    def it_works_with_nothing_running(self, in_example_dir):
        assert svstat('playground/greeter') == [C(SvStat, state=SvStat.UNSUPERVISED)]
        self.assert_works_interactively()

    def it_fails_with_multiple_services(self, in_example_dir):
        p = Popen(('pgctl-2015', 'debug', 'abc', 'def'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == ''
        assert stderr == (
            'Must debug exactly one service, not: abc, def\n'
        )
        assert p.returncode == 1

    def it_first_stops_the_background_service_if_running(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'greeter'))
        assert svstat('playground/greeter') == [C(SvStat, state='up')]

        self.assert_works_interactively()


class DescribeRestart(object):

    def it_is_just_stop_then_start(self, in_example_dir):
        p = Popen(('pgctl-2015', 'restart', 'date'), stdout=PIPE, stderr=PIPE)
        _, stderr = run(p)
        assert stderr == '''\
Stopping: date
Stopped: date
Starting: date
Started: date
'''
        assert p.returncode == 0
        assert svstat('playground/date') == [C(SvStat, state='up')]

    def it_also_works_when_up(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        assert svstat('playground/date') == [C(SvStat, state='up')]

        self.it_is_just_stop_then_start(in_example_dir)


class DescribeStartMultipleServices(object):

    @fixture
    def service_name(self):
        yield 'multiple'

    def it_only_starts_the_indicated_services(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start', 'date'))

            assert svstat('playground/date') == [C(SvStat, state='up')]
            assert svstat('playground/tail') == [C(SvStat, state='down')]
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_starts_multiple_services(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start', 'date', 'tail'))

            assert svstat('playground/date') == [C(SvStat, state='up')]
            assert svstat('playground/tail') == [C(SvStat, state='up')]
        finally:
            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

    def it_stops_multiple_services(self, in_example_dir):
        try:
            check_call(('pgctl-2015', 'start', 'date', 'tail'))

            assert svstat('playground/date') == [C(SvStat, state='up')]
            assert svstat('playground/tail') == [C(SvStat, state='up')]

            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

            assert svstat('playground/date', 'playground/tail') == [
                C(SvStat, state=SvStat.UNSUPERVISED),
                C(SvStat, state=SvStat.UNSUPERVISED),
            ]
        finally:
            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

    def it_starts_everything_with_no_arguments_no_config(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start'))

            assert svstat('playground/date') == [C(SvStat, state='up')]
            assert svstat('playground/tail') == [C(SvStat, state='up')]
        finally:
            check_call(('pgctl-2015', 'stop'))


class DescribeStatus(object):

    @fixture
    def service_name(self):
        yield 'multiple'

    def it_displays_correctly_when_the_service_is_down(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        check_call(('pgctl-2015', 'stop', 'date'))
        p = Popen(('pgctl-2015', 'status', 'date'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == S('date: down \\d+ seconds\\n$')
        assert stderr == ''

    def it_displays_correctly_when_the_service_is_up(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            p = Popen(('pgctl-2015', 'status', 'date'), stdout=PIPE, stderr=PIPE)
            stdout, stderr = run(p)
            assert stdout == S('date: up \\(pid \\d+\\) \\d+ seconds\\n$')
            assert stderr == ''
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_displays_the_status_of_multiple_services(self, in_example_dir):
        """Expect multiple services with status and PID"""
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            p = Popen(('pgctl-2015', 'status', 'date', 'tail'), stdout=PIPE, stderr=PIPE)
            stdout, stderr = run(p)
            assert stdout == S('''\
date: up \\(pid \\d+\\) \\d+ seconds
tail: down \\d+ seconds
$''')
            assert stderr == ''
            assert p.returncode == 0
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_displays_the_status_of_all_services(self, in_example_dir):
        """Expect all services to provide status when no service is specified"""
        check_call(('pgctl-2015', 'start', 'tail'))
        try:
            p = Popen(('pgctl-2015', 'status'), stdout=PIPE, stderr=PIPE)
            stdout, stderr = run(p)
            assert stdout == S('''\
date: down \\d+ seconds
tail: up \\(pid \\d+\\) \\d+ seconds
$''')
            assert stderr == ''
            assert p.returncode == 0
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_displays_status_for_unknown_services(self, in_example_dir):
        try:
            p = Popen(('pgctl-2015', 'status', 'garbage'), stdout=PIPE, stderr=PIPE)
            stdout, stderr = run(p)
            assert stdout == '''\
garbage: no such service
'''
            assert stderr == ''
            assert p.returncode == 0
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))


class DescribeReload(object):

    def it_is_unimplemented(self, in_example_dir):
        p = Popen(('pgctl-2015', 'reload'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == ''
        assert stderr == (
            'reload: date\n'
            'reloading is not yet implemented.\n'
        )
        assert p.returncode == 1


class DescribeAliases(object):

    @fixture
    def service_name(self):
        yield 'output'

    def it_can_expand_properly(self, in_example_dir):
        p = Popen(('pgctl-2015', 'start', 'a'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == ''
        assert stderr == '''\
Starting: ohhi, sweet
Started: ohhi, sweet
'''
        assert p.returncode == 0

    def it_can_detect_cycles(self, in_example_dir):
        p = Popen(('pgctl-2015', 'start', 'b'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert p.returncode == 1
        assert stdout == ''
        assert stderr == "Circular aliases! Visited twice during alias expansion: 'b'\n"

    def it_can_start_when_default_is_not_defined_explicitly(self, in_example_dir):
        p = Popen(('pgctl-2015', 'start'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert p.returncode == 0
        assert stdout == ''
        assert stderr == '''\
Starting: ohhi, sweet
Started: ohhi, sweet
'''


class DescribeEnvironment(object):

    @fixture
    def service_name(self):
        yield 'environment'

    def it_can_accept_different_environment_variables(self, in_example_dir):
        check_call(('sh', '-c', 'MYVAR=ohhi pgctl-2015 start'))

        p = Popen(('pgctl-2015', 'log'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert p.returncode == 0
        assert stderr == ''
        assert stdout == '''\
==> environment/stdout.log <==
ohhi

==> environment/stderr.log <==
'''
        check_call(('pgctl-2015', 'stop'))
        check_call(('sh', '-c', 'MYVAR=bye pgctl-2015 start'))

        p = Popen(('pgctl-2015', 'log'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert p.returncode == 0
        assert stderr == ''
        assert stdout == '''\
==> environment/stdout.log <==
bye

==> environment/stderr.log <==
'''
