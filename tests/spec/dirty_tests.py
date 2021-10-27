import os
import signal
import subprocess
import time

import pytest
from testing import norm
from testing.assertions import assert_svstat
from testing.assertions import wait_for
from testing.service_context import set_slow_shutdown_sleeptime
from testing.subprocess import assert_command

from pgctl.daemontools import SvStat
from pgctl.errors import LockHeld
from pgctl.functions import show_runaway_processes
from pgctl.fuser import fuser
from pgctl.subprocess import check_call


def clean_service(service_path):
    # we use SIGTERM; SIGKILL is cheating.
    limit = 100
    while limit > 0:  # pragma: no branch: we don't expect to ever hit the limit
        assert os.path.isdir(service_path), service_path
        try:
            show_runaway_processes(service_path)
            print('lock released -- done.')
            break
        except LockHeld:
            print('lock held -- killing!')
            for pid in fuser(service_path):
                try:
                    os.system('ps -fj %i' % pid)
                    os.kill(pid, signal.SIGTERM)
                except OSError as error:  # race condition -- process stopped between list and kill :pragma: no-cover
                    if error.errno == 3:  # no such process
                        pass
                    else:
                        raise
        limit -= 1


class DirtyTest:

    @pytest.fixture(autouse=True)
    def cleanup(self, in_example_dir):
        try:
            yield in_example_dir
        finally:
            for service in in_example_dir.join('playground').listdir():
                clean_service(str(service))


class DescribeOrphanSubprocess(DirtyTest):

    @pytest.fixture(autouse=True)
    def environment(self):
        os.environ['PGCTL_TIMEOUT'] = '5'
        yield
        del os.environ['PGCTL_TIMEOUT']

    @pytest.fixture
    def service_name(self):
        yield 'orphan-subprocess'

    def it_starts_up_fine(self):
        assert_command(
            ('pgctl', 'start'),
            '',
            '''\
[pgctl] Starting: slow-startup, sweet
[pgctl] Started: sweet
[pgctl] Started: slow-startup
''',
            0,
        )
        assert_command(
            ('pgctl', 'log'),
            '''\
==> playground/slow-startup/logs/current <==
{TIMESTAMP} pgctl-poll-ready: service's ready check succeeded

==> playground/sweet/logs/current <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error
''',
            '',
            0,
            norm=norm.pgctl,
        )

    def it_shows_error_but_still_succeeds_on_stop_for_sweet(self):
        check_call(('pgctl', 'start', 'sweet'))
        assert_command(
            ('pgctl', 'restart', 'sweet'),
            '',
            '''\
[pgctl] Stopping: sweet
[pgctl] WARNING: Killing these runaway processes which did not stop:
{PS-HEADER}
{PS-STATS} sleep infinity

This usually means these processes are buggy.
Learn more: https://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

[pgctl] Stopped: sweet
[pgctl] Starting: sweet
[pgctl] Started: sweet
''',
            0,
            norm=norm.pgctl,
        )

    def it_shows_error_but_still_succeeds_on_stop_for_slow_start(self):
        check_call(('pgctl', 'start', 'slow-startup'))
        assert_command(
            ('pgctl', 'restart', 'slow-startup'),
            '',
            '''\
[pgctl] Stopping: slow-startup
[pgctl] WARNING: Killing these runaway processes which did not stop:
{PS-HEADER}
{PS-STATS} sleep 987654

This usually means these processes are buggy.
Learn more: https://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

[pgctl] Stopped: slow-startup
[pgctl] Starting: slow-startup
[pgctl] Started: slow-startup
''',
            0,
            norm=norm.pgctl,
        )


class DescribeSlowShutdownOnForeground(DirtyTest):
    """This test case takes three seconds to shut down"""

    @pytest.fixture()
    def service_name(self):
        yield 'slow-shutdown'

    @pytest.fixture(autouse=True)
    def environment(self):
        os.environ['PGCTL_TIMEOUT'] = '1.5'
        yield
        del os.environ['PGCTL_TIMEOUT']

    @pytest.fixture(autouse=True)
    def configure_sleeptime(self):
        with set_slow_shutdown_sleeptime(0.75, 2.5):
            yield

    def it_fails_by_default(self):
        check_call(('pgctl', 'start'))
        assert_svstat('playground/sweet', state='up')
        assert_command(
            ('pgctl', 'stop', '--no-force'),
            '',
            '''\
[pgctl] Stopping: sweet
[pgctl] ERROR: service 'sweet' failed to stop after {TIME} seconds, its status is ready (pid {PID}) {TIME} seconds
==> playground/sweet/logs/current <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error
[pgctl]
[pgctl] There might be useful information further up in the log; you can view it by running:
[pgctl]     less +G playground/sweet/logs/current
[pgctl] ERROR: Some services failed to stop: sweet
''',
            1,
            norm=norm.pgctl,
        )

    def it_succeeds_on_normal_forceful_stop(self):
        check_call(('pgctl', 'start'))
        assert_svstat('playground/sweet', state='up')
        assert_command(
            ('pgctl', 'stop'),
            '',
            '''\
[pgctl] Stopping: sweet
[pgctl] WARNING: Killing these runaway processes which did not stop:
{PS-HEADER}
{PS-STATS} {S6-PROCESS}
{PS-STATS} \\_ /bin/bash ./run
{PS-STATS} \\_ sleep 2.5

This usually means these processes are buggy.
Learn more: https://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

[pgctl] Stopped: sweet
''',
            0,
            norm=norm.pgctl,
        )

    def it_can_shut_down_successfully_with_longer_timeout(self):
        # if we configure it to wait a bit longer, it works fine
        with open('playground/sweet/timeout-stop', 'w') as timeout:
            timeout.write('3')

        check_call(('pgctl', 'start'))
        assert_svstat('playground/sweet', state='up')

        check_call(('pgctl', 'restart'))
        assert_svstat('playground/sweet', state='up')

        check_call(('pgctl', 'stop', '--no-force'))
        assert_svstat('playground/sweet', state=SvStat.UNSUPERVISED)


class DescribeSlowShutdownOnBackground(DirtyTest):

    @pytest.fixture()
    def service_name(self):
        yield 'slow-shutdown'

    @pytest.fixture(autouse=True)
    def environment(self):
        os.environ['PGCTL_TIMEOUT'] = '1.5'
        yield
        del os.environ['PGCTL_TIMEOUT']

    @pytest.fixture(autouse=True)
    def configure_sleeptime(self):
        with set_slow_shutdown_sleeptime(2.5, 0.75):
            yield

    def it_fails_by_leaking_runaway_process_on_stop(self):
        check_call(('pgctl', 'start'))
        assert_svstat('playground/sweet', state='up')

        assert_command(
            ('pgctl', 'stop', '--no-force'),
            '',
            '''\
[pgctl] Stopping: sweet
[pgctl] ERROR: service 'sweet' failed to stop after {TIME} seconds, these runaway processes did not stop:
{PS-HEADER}
{PS-STATS} sleep 2.5

This usually means these processes are buggy.
Normally pgctl would kill these automatically for you, but you specified the --no-force option.
Learn more: https://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

==> playground/sweet/logs/current <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error
[pgctl]
[pgctl] There might be useful information further up in the log; you can view it by running:
[pgctl]     less +G playground/sweet/logs/current
[pgctl] ERROR: Some services failed to stop: sweet
''',
            1,
            norm=norm.pgctl,
        )

    def it_succeeds_on_second_stop_after_some_delay(self):
        check_call(('pgctl', 'start'))
        assert_svstat('playground/sweet', state='up')

        with pytest.raises(subprocess.CalledProcessError):
            check_call(('pgctl', 'stop', '--no-force'))

        time.sleep(3)
        assert_command(
            ('pgctl', 'stop'),
            '',
            '''\
[pgctl] Already stopped: sweet
''',
            0,
            norm=norm.pgctl,
        )

    def it_succeeds_on_normal_forceful_stop(self):
        check_call(('pgctl', 'start'))
        assert_svstat('playground/sweet', state='up')
        assert_command(
            ('pgctl', 'stop'),
            '',
            '''\
[pgctl] Stopping: sweet
[pgctl] WARNING: Killing these runaway processes which did not stop:
{PS-HEADER}
{PS-STATS} sleep 2.5

This usually means these processes are buggy.
Learn more: https://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

[pgctl] Stopped: sweet
''',
            0,
            norm=norm.pgctl,
        )


class DescribeSubprocessWithClosedFds(DirtyTest):

    @pytest.fixture()
    def service_name(self):
        yield 'subprocess-with-closed-fds'

    def it_starts_and_cannot_be_stopped_without_force(self):
        # It should start up properly and write out a PID.
        check_call(('pgctl', 'start'))
        assert_svstat('playground/bad-subprocess', state='up')

        wait_for(lambda: os.path.exists('playground/bad-subprocess/child.pid'))

        # pgctl stop should fail based on environment variable tracing.
        assert_command(
            ('pgctl', 'stop', '--no-force'),
            '',
            '''\
[pgctl] Stopping: bad-subprocess
[pgctl] ERROR: service 'bad-subprocess' failed to stop after {TIME} seconds, these runaway processes did not stop:
{PS-HEADER}
{PS-STATS} sleep infinity

This usually means these processes are buggy.
Learn more: https://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

==> playground/bad-subprocess/logs/current <==
[pgctl]
[pgctl] There might be useful information further up in the log; you can view it by running:
[pgctl]     less +G playground/bad-subprocess/logs/current
[pgctl] ERROR: Some services failed to stop: bad-subprocess
''',  # noqa: E501
            1,
            norm=norm.pgctl,
        )

        # pgctl stop without --no-force should succeed.
        assert_command(
            ('pgctl', 'stop'),
            '',
            '''\
[pgctl] Stopping: bad-subprocess
[pgctl] WARNING: Killing these runaway processes which did not stop:
{PS-HEADER}
{PS-STATS} sleep infinity

This usually means these processes are buggy.
Learn more: https://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

[pgctl] Stopped: bad-subprocess
''',
            0,
            norm=norm.pgctl,
        )
