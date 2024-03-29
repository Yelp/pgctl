import json
import os
import subprocess
from unittest import mock

import pytest
from testing import norm
from testing import pty
from testing.assertions import assert_svstat
from testing.assertions import wait_for
from testing.subprocess import assert_command
from testing.subprocess import ctrl_c
from testing.subprocess import run

from pgctl.daemontools import SvStat
from pgctl.subprocess import check_call
from pgctl.subprocess import PIPE
from pgctl.subprocess import Popen


class ANY_INTEGER:

    def __eq__(self, other):
        return isinstance(other, int)


class DescribePgctlLog:

    @pytest.fixture
    def service_name(self):
        yield 'output'

    def it_is_empty_before_anything_starts(self, in_example_dir):
        assert_command(
            ('pgctl', 'log'),
            '''\
==> playground/ohhi/logs/current <==

==> playground/sweet/logs/current <==
''',
            '',
            0,
        )

    def it_shows_stdout_and_stderr(self, in_example_dir):
        check_call(('pgctl', 'start', 'sweet'))

        assert_command(
            ('pgctl', 'log'),
            '''\
==> playground/ohhi/logs/current <==

==> playground/sweet/logs/current <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error
''',
            '',
            0,
            norm=norm.pgctl,
        )

        check_call(('pgctl', 'restart', 'sweet'))

        assert_command(
            ('pgctl', 'log'),
            '''\
==> playground/ohhi/logs/current <==

==> playground/sweet/logs/current <==
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
        check_call(('pgctl', 'start'))

        # this pty simulates running in a terminal
        read, write = os.openpty()
        pty.normalize_newlines(read)
        p = Popen(('pgctl', 'log'), stdout=write, stderr=write)
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
==> playground/ohhi/logs/current <==
{TIMESTAMP} [oe].*
==> playground/sweet/logs/current <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error

==> playground/ohhi/logs/current <==
.*{TIMESTAMP} .*$''')
        assert p.poll() is None  # it's still running

        p.terminate()

        assert p.wait() == -15

    def it_fails_for_nonexistent_services(self, in_example_dir):
        assert_command(
            ('pgctl', 'log', 'i-dont-exist'),
            '',
            '''\
[pgctl] ERROR: No such service: 'playground/i-dont-exist'
''',
            1,
        )

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


class DescribeDateExample:

    @pytest.fixture
    def service_name(self):
        yield 'date'

    def it_does_start(self, in_example_dir, scratch_dir):
        assert not scratch_dir.join('now.date').isfile()
        check_call(('pgctl', 'start', 'date'))
        wait_for(lambda: scratch_dir.join('now.date').isfile())

    def it_can_start_via_abspath_service(self, in_example_dir, scratch_dir, tmpdir):
        with tmpdir.ensure_dir('arbitrary').as_cwd():
            assert not scratch_dir.join('now.date').isfile()
            date_abspath = str(in_example_dir.join('playground/date'))
            check_call(('pgctl', 'start', date_abspath))
            wait_for(lambda: scratch_dir.join('now.date').isfile())

    def it_can_start_via_abspath_pgdir(self, in_example_dir, scratch_dir, tmpdir):
        with tmpdir.ensure_dir('arbitrary').as_cwd():
            assert not scratch_dir.join('now.date').isfile()
            env = os.environ.copy()
            env['PGCTL_PGDIR'] = str(in_example_dir.join('playground'))
            check_call(('pgctl', 'start', 'date'), env=env)
            wait_for(lambda: scratch_dir.join('now.date').isfile())


class DescribeTailExample:

    @pytest.fixture
    def service_name(self):
        yield 'tail'

    def it_does_start(self, in_example_dir):
        test_string = 'oh, hi there.\n'
        with open('input', 'w') as input:
            input.write(test_string)
        assert not os.path.isfile('output')

        check_call(('pgctl', 'start', 'tail'))
        wait_for(lambda: os.path.isfile('output'))
        assert open('output').read() == test_string


class DescribeStart:

    def it_fails_given_unknown(self, in_example_dir):
        assert_command(
            ('pgctl', 'start', 'unknown'),
            '',
            '''\
[pgctl] ERROR: No such service: 'playground/unknown'
''',
            1,
        )

    def it_is_idempotent(self, in_example_dir):
        check_call(('pgctl', 'start', 'sleep'))
        check_call(('pgctl', 'start', 'sleep'))

    def it_should_work_in_a_subdirectory(self, in_example_dir):
        os.chdir(in_example_dir.join('playground').strpath)
        assert_command(
            ('pgctl', 'start', 'sleep'),
            '',
            '''\
[pgctl] Starting: sleep
[pgctl] Started: sleep
''',
            0,
        )


class DescribeStartWithLogViewer:

    @pytest.fixture
    def service_name(self):
        yield 'slow-startup'

    def it_should_work_in_a_subdirectory(self, in_example_dir, capfd):
        os.chdir(in_example_dir.join('playground').strpath)
        with open(os.path.join('slow-startup', 'timeout-ready'), 'w') as f:
            f.write('10\n')
        with mock.patch.dict(
            os.environ,
            {'PGCTL_FORCE_ENABLE_LOG_VIEWER': '1'},
        ):
            subprocess.check_call(('pgctl', 'start', 'slow-startup'))

        output = capfd.readouterr()

        # Don't want to assert the entire embedded log viewer output, just
        # testing for a few strings that should be present.
        assert '[pgctl] Starting: slow-startup\n' in output.err
        assert 'Still starting: slow-startup\n' in output.err
        assert '[pgctl] All services have started\n' in output.err

        # Make sure there's a log line that looks like:
        # ║[slow-startup] 2021-11-02 10:39:51.406518500  waiting 2 seconds to become rea║
        assert any(
            '[slow-startup]' in line and 'waiting 2 seconds to become re' in line
            for line in output.err.splitlines()
        )


class DescribeStop:

    def it_does_stop(self, in_example_dir):
        check_call(('pgctl', 'start', 'sleep'))
        check_call(('pgctl', 'stop', 'sleep'))

        assert_svstat('playground/sleep', state=SvStat.UNSUPERVISED)

    def it_prints_log_stop_info_for_verbose(self, in_example_dir):
        check_call(('pgctl', 'start', 'sleep'))
        # TODO: Finish this
        assert_command(
            ('pgctl', 'stop', 'sleep', '--verbose'),
            '',
            '''\
[pgctl] Stopping: sleep
[pgctl] Stopped: sleep
[pgctl] Stopping logger for: sleep
[pgctl] Stopped logger for: sleep
''',
            0,
        )

    def it_is_successful_before_start(self, in_example_dir):
        check_call(('pgctl', 'stop', 'sleep'))

    def it_fails_given_unknown(self, in_example_dir):
        assert_command(
            ('pgctl', 'stop', 'unknown'),
            '',
            '''\
[pgctl] ERROR: No such service: 'playground/unknown'
''',
            1,
        )


class DescribeRestart:

    def it_is_just_stop_then_start(self, in_example_dir):
        assert_command(
            ('pgctl', 'restart', 'sleep'),
            '',
            '''\
[pgctl] Already stopped: sleep
[pgctl] Starting: sleep
[pgctl] Started: sleep
''',
            0,
        )
        assert_svstat('playground/sleep', state='up')

    def it_also_works_when_up(self, in_example_dir):
        check_call(('pgctl', 'start', 'sleep'))
        assert_svstat('playground/sleep', state='up')

        assert_command(
            ('pgctl', 'restart', 'sleep'),
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


class DescribeStartMultipleServices:

    @pytest.fixture
    def service_name(self):
        yield 'multiple'

    def it_only_starts_the_indicated_services(self, in_example_dir, request):
        check_call(('pgctl', 'start', 'sleep'))

        assert_svstat('playground/sleep', state='up')
        assert_svstat('playground/tail', state=SvStat.UNSUPERVISED)

    def it_starts_multiple_services(self, in_example_dir, request):
        check_call(('pgctl', 'start', 'sleep', 'tail'))

        assert_svstat('playground/sleep', state='up')
        assert_svstat('playground/tail', state='up')

    def it_stops_multiple_services(self, in_example_dir):
        check_call(('pgctl', 'start', 'sleep', 'tail'))

        assert_svstat('playground/sleep', state='up')
        assert_svstat('playground/tail', state='up')

        check_call(('pgctl', 'stop', 'sleep', 'tail'))

        assert_svstat('playground/sleep', state=SvStat.UNSUPERVISED)
        assert_svstat('playground/tail', state=SvStat.UNSUPERVISED)

    def it_starts_everything_with_no_arguments_no_config(self, in_example_dir, request):
        check_call(('pgctl', 'start'))

        assert_svstat('playground/sleep', state='up')
        assert_svstat('playground/tail', state='up')


class DescribeStatus:

    @pytest.fixture
    def service_name(self):
        yield 'multiple'

    def it_displays_correctly_when_the_service_is_down(self, in_example_dir):
        check_call(('pgctl', 'start', 'sleep'))
        check_call(('pgctl', 'stop', 'sleep'))
        assert_command(
            ('pgctl', 'status', 'sleep'),
            ' ● sleep: down\n',
            '',
            0,
        )

    def it_displays_correctly_when_the_service_is_down_json(self, in_example_dir):
        check_call(('pgctl', 'start', 'sleep'))
        check_call(('pgctl', 'stop', 'sleep'))
        stdout, stderr, returncode = run(
            ('pgctl', '--json', 'status', 'sleep'),
        )
        assert returncode == 0
        assert json.loads(stdout) == {
            'sleep': {
                'exitcode': None,
                'pid': None,
                'process': None,
                'seconds': None,
                'state': 'down',
            },
        }
        assert stderr == ''

    def it_displays_correctly_when_the_service_is_up(self, in_example_dir):
        check_call(('pgctl', 'start', 'sleep'))
        assert_command(
            ('pgctl', 'status', 'sleep'),
            ' ● sleep: ready\n'
            '   └─ pid: {PID}, {TIME} seconds\n',
            '',
            0,
            norm=norm.pgctl,
        )

    def it_displays_correctly_when_the_service_is_up_json(self, in_example_dir):
        check_call(('pgctl', 'start', 'sleep'))
        stdout, stderr, returncode = run(
            ('pgctl', '--json', 'status', 'sleep'),
        )
        assert returncode == 0
        assert json.loads(stdout) == {
            'sleep': {
                'exitcode': None,
                'pid': ANY_INTEGER(),
                'process': None,
                'seconds': ANY_INTEGER(),
                'state': 'ready',
            },
        }
        assert stderr == ''

    def it_displays_the_status_of_multiple_services(self, in_example_dir):
        """Expect multiple services with status and PID"""
        check_call(('pgctl', 'start', 'sleep'))
        assert_command(
            ('pgctl', 'status', 'sleep', 'tail'),
            '''\
 ● sleep: ready
   └─ pid: {PID}, {TIME} seconds
 ● tail: down
''',
            '',
            0,
            norm=norm.pgctl,
        )

    def it_displays_the_status_of_multiple_services_json(self, in_example_dir):
        """Expect multiple services with status and PID"""
        check_call(('pgctl', 'start', 'sleep'))
        stdout, stderr, returncode = run(
            ('pgctl', '--json', 'status', 'sleep', 'tail'),
        )
        assert returncode == 0
        assert json.loads(stdout) == {
            'sleep': {
                'exitcode': None,
                'pid': ANY_INTEGER(),
                'process': None,
                'seconds': ANY_INTEGER(),
                'state': 'ready',
            },
            'tail': {
                'exitcode': None,
                'pid': None,
                'process': None,
                'seconds': None,
                'state': 'down',
            }
        }
        assert stderr == ''

    def it_displays_the_status_of_all_services(self, in_example_dir):
        """Expect all services to provide status when no service is specified"""
        check_call(('pgctl', 'start', 'tail'))
        assert_command(
            ('pgctl', 'status'),
            '''\
 ● sleep: down
 ● tail: ready
   └─ pid: {PID}, {TIME} seconds
''',
            '',
            0,
            norm=norm.pgctl,
        )

    def it_displays_status_for_unknown_services(self, in_example_dir):
        assert_command(
            ('pgctl', 'status', 'garbage'),
            '',
            '''\
[pgctl] ERROR: No such service: 'playground/garbage'
''',
            1,
        )

    def it_can_recover_from_a_git_clean(self, in_example_dir, service_name):
        def assert_status():
            assert_command(
                ('pgctl', 'status'),
                '''\
 ● sleep: down
 ● tail: ready
   └─ pid: {PID}, {TIME} seconds
''',
                '',
                0,
                norm=norm.pgctl,
            )

        check_call(('pgctl', 'start', 'tail'))
        assert_status()

        # simulate a git-clean: blow everything away, create a fresh copy
        parent_dir = in_example_dir.join('..')
        with parent_dir.as_cwd():
            in_example_dir.remove(rec=True)
            from testing import copy_example
            copy_example(service_name, parent_dir)

        assert_status()


class DescribeReload:

    def it_is_unimplemented(self, in_example_dir):
        assert_command(
            ('pgctl', 'reload'),
            '',
            '''\
[pgctl] reload: sleep
[pgctl] ERROR: reloading is not yet implemented.
''',
            1,
        )


class DescribeAliases:

    @pytest.fixture
    def service_name(self):
        yield 'output'

    def it_can_expand_properly(self, in_example_dir):
        assert_command(
            ('pgctl', 'start', 'a'),
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
            ('pgctl', 'start', 'b'),
            '',
            "[pgctl] ERROR: Circular aliases! Visited twice during alias expansion: 'b'\n",
            1,
        )

    def it_can_start_when_default_is_not_defined_explicitly(self, in_example_dir):
        assert_command(
            ('pgctl', 'start'),
            '',
            '''\
[pgctl] Starting: ohhi, sweet
[pgctl] Started: ohhi
[pgctl] Started: sweet
''',
            0,
        )

    @pytest.mark.usefixtures('in_example_dir')
    def it_shows_all_services_with_dash_a(self):
        assert_command(
            ('pgctl', 'status'),
            '''\
 ● ohhi: down
 ● sweet: down
''',
            '',
            0,
        )

        assert_command(
            ('pgctl', 'status', '-a'),
            '''\
 ● ohhi: down
 ● sleep: down
 ● sweet: down
''',
            '',
            0,
        )


class DescribeEnvironment:

    @pytest.fixture
    def service_name(self):
        yield 'environment'

    def it_can_accept_different_environment_variables(self, in_example_dir):
        check_call(('sh', '-c', 'MYVAR=ohhi pgctl start'))

        assert_command(
            ('pgctl', 'log'),
            '''\
==> playground/environment/logs/current <==
{TIMESTAMP} ohhi
''',
            '',
            0,
            norm=norm.pgctl,
        )

        check_call(('sh', '-c', 'MYVAR=bye pgctl restart'))

        assert_command(
            ('pgctl', 'log'),
            '''\
==> playground/environment/logs/current <==
{TIMESTAMP} ohhi
{TIMESTAMP} bye
''',
            '',
            0,
            norm=norm.pgctl,
        )


class DescribePgdirMissing:

    @pytest.mark.parametrize(
        'command',
        ('start', 'stop', 'status', 'restart', 'reload', 'log', 'debug'),
    )
    def it_shows_an_error(self, command, tmpdir):
        with tmpdir.as_cwd():
            assert_command(
                ('pgctl', command),
                '',
                "[pgctl] ERROR: could not find any directory named 'playground'\n",
                1,
            )

    def it_can_still_show_config(self, tmpdir):
        with tmpdir.as_cwd():
            output = json.loads(subprocess.check_output(('pgctl', 'config')))

        # Just smoke testing that a few values are present.
        assert 'aliases' in output
        assert 'verbose' in output

    def it_can_still_show_help(self, tmpdir):
        with tmpdir.as_cwd():
            output = subprocess.check_output(('pgctl', '--help'), stderr=subprocess.PIPE)
        assert b'usage: pgctl' in output

    def it_still_shows_help_without_args(self, tmpdir):
        with tmpdir.as_cwd():
            proc = subprocess.run(('pgctl',), capture_output=True)
        assert proc.returncode == 2
        assert b'usage: pgctl' in proc.stderr
        assert b'pgctl: error: the following arguments are required: command' in proc.stderr


class DescribeDependentServices:

    @pytest.fixture
    def service_name(self):
        yield 'dependent'

    def it_works(self, in_example_dir):
        assert_command(
            ('pgctl', 'start', 'A'),
            '',
            '''\
[pgctl] Starting: A
[pgctl] Started: A
''',
            0,
        )
        wait_for(lambda: assert_command(
            ('pgctl', 'log', 'A'),
            '''\
==> playground/A/logs/current <==
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
            ('pgctl', 'stop', 'A'),
            '',
            '''\
[pgctl] Stopping: A
[pgctl] Stopped: A
''',
            0,
        )


class DescribeStartMessageSuccess:

    @pytest.fixture
    def service_name(self):
        yield 'start-message'

    def it_prints_a_start_message_on_successful_startup(self, in_example_dir):
        assert_command(
            ('pgctl', 'start', 'start-message'),
            '',
            '''\
[pgctl] Starting: start-message
[pgctl] Started: start-message
Service has started at localhost:9001
''',
            0
        )


class DescribePreStartHook:

    @pytest.fixture
    def service_name(self):
        yield 'pre-start-hook'

    @pytest.mark.usefixtures('in_example_dir')
    def it_runs_before_starting_a_service(self):
        assert_command(
            ('pgctl', 'start'),
            'hello, i am a pre-start script in stdout\n',
            '''\
hello, i am a pre-start script in stderr
--> $PWD basename: pre-start-hook
--> cwd basename: pre-start-hook
[pgctl] Starting: sweet
[pgctl] Started: sweet
''',
            0,
            norm=norm.pgctl,
        )

        # starting when already up doesn't trigger pre-start to run again
        assert_command(
            ('pgctl', 'start'),
            '',
            '''\
[pgctl] Already started: sweet
''',
            0,
            norm=norm.pgctl,
        )

    @pytest.mark.usefixtures('in_example_dir')
    def it_runs_before_debugging_a_service(self):
        proc = Popen(('setsid', 'pgctl', 'debug', 'sweet'), stdin=PIPE, stdout=PIPE)
        proc.stdin.close()
        try:
            assert proc.stdout.readline().decode('utf-8') == 'hello, i am a pre-start script in stdout\n'
        finally:
            ctrl_c(proc)
            proc.wait()


class DescribePostStopHook:

    @pytest.fixture
    def service_name(self):
        yield 'post-stop-hook'

    @pytest.mark.usefixtures('in_example_dir')
    def it_runs_after_all_services_have_stopped(self):
        assert_command(
            ('pgctl', 'start', 'A'),
            '',
            '''\
[pgctl] Starting: A
[pgctl] Started: A
''',
            0,
            norm=norm.pgctl,
        )
        assert_command(
            ('pgctl', 'start', 'B'),
            '',
            '''\
[pgctl] Starting: B
[pgctl] Started: B
''',
            0,
            norm=norm.pgctl,
        )

        assert_command(
            ('pgctl', 'stop', 'A'),
            '',
            '''\
[pgctl] Stopping: A
[pgctl] Stopped: A
''',
            0,
            norm=norm.pgctl,
        )
        assert_command(
            ('pgctl', 'stop', 'B'),
            '',
            '''\
[pgctl] Stopping: B
[pgctl] Stopped: B
hello, i am a post-stop script
--> $PWD basename: post-stop-hook
--> cwd basename: post-stop-hook
''',
            0,
            norm=norm.pgctl,
        )

        # stopping when already down doesn't trigger post-stop to run again
        assert_command(
            ('pgctl', 'stop', 'A'),
            '',
            '''\
[pgctl] Already stopped: A
''',
            0,
            norm=norm.pgctl,
        )
