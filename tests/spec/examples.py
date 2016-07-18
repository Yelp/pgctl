# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os

import pytest
import six
from testing import norm
from testing import pty
from testing.assertions import assert_svstat
from testing.assertions import wait_for
from testing.norm import norm_trailing_whitespace_json
from testing.subprocess import assert_command

from pgctl.daemontools import SvStat
from pgctl.subprocess import check_call
from pgctl.subprocess import Popen


class DescribePgctlLog(object):

    @pytest.yield_fixture
    def service_name(self):
        yield 'output'

    def it_is_empty_before_anything_starts(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/ohhi/log <==

==> playground/sweet/log <==
''',
            '',
            0,
        )

    def it_shows_stdout_and_stderr(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'sweet'))

        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/ohhi/log <==

==> playground/sweet/log <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error
''',
            '',
            0,
            norm=norm.pgctl,
        )

        check_call(('pgctl-2015', 'restart', 'sweet'))

        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/ohhi/log <==

==> playground/sweet/log <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error
''',
            '',
            0,
            norm=norm.pgctl,
        )

    def it_logs_continuously_when_run_interactively(self, in_example_dir):
        check_call(('pgctl-2015', 'start'))

        # this pty simulates running in a terminal
        read, write = os.openpty()
        pty.normalize_newlines(read)
        p = Popen(('pgctl-2015', 'log'), stdout=write, stderr=write)
        os.close(write)

        import fcntl
        fl = fcntl.fcntl(read, fcntl.F_GETFL)
        fcntl.fcntl(read, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        assert p.poll() is None  # it's still running

        # needs to loop for several seconds because the default event loop
        # in tail-f is one second.
        # TODO: buf is a list, use wait_for() to append to it
        limit = 3.0
        wait = .1
        buf = b''
        while True:
            try:
                block = os.read(read, 1024)
                print('BLOCK:', block)
            except OSError as error:
                print('ERROR:', error)
                if error.errno == 11:  # other end didn't write yet
                    if limit > 0:
                        import time
                        time.sleep(wait)
                        limit -= wait
                        continue
                    else:
                        break
                else:
                    raise
            buf += block

        from testfixtures import StringComparison as S
        buf = norm.pgctl(buf.decode('UTF-8'))
        print('NORMED:')
        print(buf)
        assert buf == S('''(?s)\
==> playground/ohhi/log <==
{TIMESTAMP} [oe].*
==> playground/sweet/log <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error

==> playground/ohhi/log <==
.*{TIMESTAMP} .*$''')
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

    @pytest.yield_fixture
    def service_name(self):
        yield 'date'

    def it_does_start(self, in_example_dir, scratch_dir):
        assert not scratch_dir.join('now.date').isfile()
        check_call(('pgctl-2015', 'start', 'date'))
        wait_for(lambda: scratch_dir.join('now.date').isfile())

    def it_can_start_via_abspath_service(self, in_example_dir, scratch_dir, tmpdir):
        with tmpdir.ensure_dir('arbitrary').as_cwd():
            assert not scratch_dir.join('now.date').isfile()
            date_abspath = str(in_example_dir.join('playground/date'))
            check_call(('pgctl-2015', 'start', date_abspath))
            wait_for(lambda: scratch_dir.join('now.date').isfile())

    def it_can_start_via_abspath_pgdir(self, in_example_dir, scratch_dir, tmpdir):
        with tmpdir.ensure_dir('arbitrary').as_cwd():
            assert not scratch_dir.join('now.date').isfile()
            env = os.environ.copy()
            env['PGCTL_PGDIR'] = str(in_example_dir.join('playground'))
            check_call(('pgctl-2015', 'start', 'date'), env=env)
            wait_for(lambda: scratch_dir.join('now.date').isfile())


class DescribeTailExample(object):

    @pytest.yield_fixture
    def service_name(self):
        yield 'tail'

    def it_does_start(self, in_example_dir):
        test_string = 'oh, hi there.\n'
        with open('input', 'w') as input:
            input.write(test_string)
        assert not os.path.isfile('output')

        check_call(('pgctl-2015', 'start', 'tail'))
        wait_for(lambda: os.path.isfile('output'))
        assert open('output').read() == test_string


class DescribeStart(object):

    def it_fails_given_unknown(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'start', 'unknown'),
            '',
            '''\
[pgctl] ERROR: No such service: 'playground/unknown'
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
[pgctl] Starting: sleep
[pgctl] Started: sleep
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
[pgctl] ERROR: No such service: 'playground/unknown'
''',
            1,
        )


class DescribeRestart(object):

    def it_is_just_stop_then_start(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'restart', 'sleep'),
            '',
            '''\
[pgctl] Stopping: sleep
[pgctl] Stopped: sleep
[pgctl] Starting: sleep
[pgctl] Started: sleep
''',
            0,
        )
        assert_svstat('playground/sleep', state='up')

    def it_also_works_when_up(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'sleep'))
        assert_svstat('playground/sleep', state='up')

        self.it_is_just_stop_then_start(in_example_dir)


class DescribeStartMultipleServices(object):

    @pytest.yield_fixture
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

    @pytest.yield_fixture
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
            'sleep: ready (pid {PID}) {TIME} seconds\n',
            '',
            0,
            norm=norm.pgctl,
        )

    def it_displays_the_status_of_multiple_services(self, in_example_dir):
        """Expect multiple services with status and PID"""
        check_call(('pgctl-2015', 'start', 'sleep'))
        assert_command(
            ('pgctl-2015', 'status', 'sleep', 'tail'),
            '''\
sleep: ready (pid {PID}) {TIME} seconds
tail: down
''',
            '',
            0,
            norm=norm.pgctl,
        )

    def it_displays_the_status_of_all_services(self, in_example_dir):
        """Expect all services to provide status when no service is specified"""
        check_call(('pgctl-2015', 'start', 'tail'))
        assert_command(
            ('pgctl-2015', 'status'),
            '''\
sleep: down
tail: ready (pid {PID}) {TIME} seconds
''',
            '',
            0,
            norm=norm.pgctl,
        )

    def it_displays_status_for_unknown_services(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'status', 'garbage'),
            '',
            '''\
[pgctl] ERROR: No such service: 'playground/garbage'
''',
            1,
        )

    def it_can_recover_from_a_git_clean(self, in_example_dir, service_name):
        def assert_status():
            assert_command(
                ('pgctl-2015', 'status'),
                '''\
sleep: down
tail: ready (pid {PID}) {TIME} seconds
''',
                '',
                0,
                norm=norm.pgctl,
            )

        check_call(('pgctl-2015', 'start', 'tail'))
        assert_status()

        # simulate a git-clean: blow everything away, create a fresh copy
        parent_dir = in_example_dir.join('..')
        with parent_dir.as_cwd():
            in_example_dir.remove(rec=True)
            from testing import copy_example
            copy_example(service_name, parent_dir)

        assert_status()


class DescribeReload(object):

    def it_is_unimplemented(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'reload'),
            '',
            '''\
[pgctl] reload: sleep
[pgctl] ERROR: reloading is not yet implemented.
''',
            1,
        )


class DescribeAliases(object):

    @pytest.yield_fixture
    def service_name(self):
        yield 'output'

    def it_can_expand_properly(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'start', 'a'),
            '',
            '''\
[pgctl] Starting: ohhi, sweet
[pgctl] Started: ohhi
[pgctl] Started: sweet
''',
            0,
        )

    def it_can_detect_cycles(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'start', 'b'),
            '',
            "[pgctl] ERROR: Circular aliases! Visited twice during alias expansion: 'b'\n",
            1,
        )

    def it_can_start_when_default_is_not_defined_explicitly(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'start'),
            '',
            '''\
[pgctl] Starting: ohhi, sweet
[pgctl] Started: ohhi
[pgctl] Started: sweet
''',
            0,
        )


class DescribeEnvironment(object):

    @pytest.yield_fixture
    def service_name(self):
        yield 'environment'

    def it_can_accept_different_environment_variables(self, in_example_dir):
        check_call(('sh', '-c', 'MYVAR=ohhi pgctl-2015 start'))

        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/environment/log <==
{TIMESTAMP} ohhi
''',
            '',
            0,
            norm=norm.pgctl,
        )

        check_call(('sh', '-c', 'MYVAR=bye pgctl-2015 restart'))

        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/environment/log <==
{TIMESTAMP} ohhi
{TIMESTAMP} bye
''',
            '',
            0,
            norm=norm.pgctl,
        )


class DescribePgdirMissing(object):

    @pytest.mark.parametrize(
        'command',
        ('start', 'stop', 'status', 'restart', 'reload', 'log', 'debug'),
    )
    def it_shows_an_error(self, command, tmpdir):
        with tmpdir.as_cwd():
            assert_command(
                ('pgctl-2015', command),
                '',
                "[pgctl] ERROR: could not find any directory named 'playground'\n",
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
'''

        with tmpdir.as_cwd():
            assert_command(
                ('pgctl-2015', 'config'),
                expected_output,
                '',
                0,
                norm=norm_trailing_whitespace_json,
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
        expected = '''\
usage: pgctl-2015 [-h] [--version] [--pgdir PGDIR] [--pghome PGHOME]
                  {{start,stop,status,restart,reload,log,debug,config}}
                  [services [services ...]]
pgctl-2015: error: {}
'''.format(
            'too few arguments'
            if six.PY2 else
            'the following arguments are required: command'
        )
        with tmpdir.as_cwd():
            assert_command(
                ('pgctl-2015'),
                '',
                expected,
                2,
            )


class DescribeDependentServices(object):

    @pytest.yield_fixture
    def service_name(self):
        yield 'dependent'

    def it_works(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'start', 'A'),
            '',
            '''\
[pgctl] Starting: A
[pgctl] Started: A
''',
            0,
        )
        wait_for(lambda: assert_command(
            ('pgctl-2015', 'log', 'A'),
            '''\
==> playground/A/log <==
{TIMESTAMP} [pgctl] Starting: B
{TIMESTAMP} [pgctl] DEBUG: parentlock: '%s/playground/A'
{TIMESTAMP} [pgctl] DEBUG: LOCK: ${LOCK}
{TIMESTAMP} [pgctl] DEBUG: loop: check_time $TIME
{TIMESTAMP} [pgctl] Started: B
{TIMESTAMP} this is stdout
{TIMESTAMP} this is stderr
''' % in_example_dir,
            '',
            0,
            norm=norm.pgctl,
        ))
        assert_command(
            ('pgctl-2015', 'stop', 'A'),
            '',
            '''\
[pgctl] Stopping: A
[pgctl] Stopped: A
''',
            0,
        )


class DescribeStartMessageSuccess(object):

    @pytest.yield_fixture
    def service_name(self):
        yield 'start-message'

    def it_prints_a_start_message_on_successful_startup(self, in_example_dir):
        assert_command(
            ('pgctl-2015', 'start', 'start-message'),
            '',
            '''\
[pgctl] Starting: start-message
[pgctl] Started: start-message
Service has started at localhost:9001
''',
            0
        )


class DescribePreStartHook(object):

    @pytest.yield_fixture
    def service_name(self):
        yield 'pre-start-hook'

    @pytest.mark.usefixtures('in_example_dir')
    def it_runs_before_starting_a_service(self):
        assert_command(
            ('pgctl-2015', 'start'),
            '',
            '''\
hello, i am a pre-start script
--> $PWD basename: pre-start-hook
--> cwd basename: pre-start-hook
[pgctl] Starting: sweet
[pgctl] Started: sweet
''',
            0,
            norm=norm.pgctl,
        )
