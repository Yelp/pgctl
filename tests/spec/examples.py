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
from testing import assert_command
from testing.assertions import retry

from pgctl.cli import SvStat
from pgctl.cli import svstat


class DescribePgctlLog(object):

    @fixture
    def service_name(self):
        yield 'output'

    def it_is_empty_before_anything_starts(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> ohhi/stdout.log <==

==> ohhi/stderr.log <==

==> sweet/stdout.log <==

==> sweet/stderr.log <==
''',
            '',
            0,
        )

    def it_shows_stdout_and_stderr(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'sweet'))

        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> ohhi/stdout.log <==

==> ohhi/stderr.log <==

==> sweet/stdout.log <==
sweet

==> sweet/stderr.log <==
sweet_error
''',
            '',
            0,
        )

        check_call(('pgctl-2015', 'restart', 'sweet'))

        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> ohhi/stdout.log <==

==> ohhi/stderr.log <==

==> sweet/stdout.log <==
sweet
sweet

==> sweet/stderr.log <==
sweet_error
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
        assert_command(
            ('pgctl-2015', 'start', 'unknown'),
            '',
            '''\
Starting: unknown
No such playground service: 'unknown'
''',
            1,
        )

    def it_is_idempotent(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            check_call(('pgctl-2015', 'start', 'date'))
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_should_work_in_a_subdirectory(self, in_example_dir):
        os.chdir(in_example_dir.join('playground').strpath)
        assert_command(
            ('pgctl-2015', 'start', 'date'),
            '',
            '''\
Starting: date
Started: date
''',
            0,
        )


class DescribeStop(object):

    def it_does_stop(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        check_call(('pgctl-2015', 'stop', 'date'))

        assert svstat('playground/date') == [C(SvStat, state='down')]

    def it_is_successful_before_start(self, in_example_dir):
        check_call(('pgctl-2015', 'stop', 'date'))

    def it_fails_given_unknown(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'stop', 'unknown'),
            '',
            '''\
Stopping: unknown
No such playground service: 'unknown'
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
        assert_command(
            ('pgctl-2015', 'debug', 'abc', 'def'),
            '',
            'Must debug exactly one service, not: abc, def\n',
            1,
        )

    def it_first_stops_the_background_service_if_running(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'greeter'))
        assert svstat('playground/greeter') == [C(SvStat, state='up')]

        self.assert_works_interactively()


class DescribeRestart(object):

    def it_is_just_stop_then_start(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'restart', 'date'),
            '',
            '''\
Stopping: date
Stopped: date
Starting: date
Started: date
''',
            0,
        )
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
                C(SvStat, state='down'),
                C(SvStat, state='down'),
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
        assert_command(
            ('pgctl-2015', 'status', 'date'),
            S('date: down \\d+ seconds\\n$'),
            '',
            0,
        )

    def it_displays_correctly_when_the_service_is_up(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            assert_command(
                ('pgctl-2015', 'status', 'date'),
                S('date: up \\(pid \\d+\\) \\d+ seconds\\n$'),
                '',
                0,
            )
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_displays_the_status_of_multiple_services(self, in_example_dir):
        """Expect multiple services with status and PID"""
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            assert_command(
                ('pgctl-2015', 'status', 'date', 'tail'),
                S('''\
date: up \\(pid \\d+\\) \\d+ seconds
tail: down \\d+ seconds
$'''),
                '',
                0,
            )
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_displays_the_status_of_all_services(self, in_example_dir):
        """Expect all services to provide status when no service is specified"""
        check_call(('pgctl-2015', 'start', 'tail'))
        try:
            assert_command(
                ('pgctl-2015', 'status'),
                S('''\
date: down \\d+ seconds
tail: up \\(pid \\d+\\) \\d+ seconds
$'''),
                '',
                0,
            )
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_displays_status_for_unknown_services(self, in_example_dir):
        try:
            assert_command(
                ('pgctl-2015', 'status', 'garbage'),
                '''\
garbage: no such service
''',
                '',
                0,
            )
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))


class DescribeReload(object):

    def it_is_unimplemented(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'reload'),
            '',
            '''\
reload: date
reloading is not yet implemented.
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
            "Circular aliases! Visited twice during alias expansion: 'b'\n",
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
