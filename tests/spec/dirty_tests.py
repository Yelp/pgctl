# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
import signal
import subprocess
import time

import pytest
from testing import norm
from testing.assertions import assert_svstat
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


class DirtyTest(object):

    LOCKERROR = '''\
[pgctl] Stopping: {service}
\\[pgctl\\] ERROR: service '{service}' failed to stop after [\\d.]+ seconds.*, these runaway processes did not stop:
UID +PID +PPID +PGID +SID +C +STIME +TTY +STAT +TIME +CMD
\\S+ +\\d+ +\\d+ +\\d+ +\\d+ +\\d+ +\\S+ +\\S+ +\\S+ +\\S+ +{cmd}

There are two ways you can fix this:
  \\* temporarily: pgctl stop --force playground/{service}
  \\* permanently: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

{log}\\[pgctl\\] ERROR: Some services failed to stop: {service}
$'''

    @pytest.yield_fixture(autouse=True)
    def cleanup(self, in_example_dir):
        try:
            yield in_example_dir
        finally:
            for service in in_example_dir.join('playground').listdir():
                clean_service(str(service))


class DescribeOrphanSubprocess(DirtyTest):

    @pytest.yield_fixture(autouse=True)
    def environment(self):
        os.environ['PGCTL_TIMEOUT'] = '5'
        yield
        del os.environ['PGCTL_TIMEOUT']

    @pytest.yield_fixture
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

    def it_shows_error_on_stop_for_sweet(self):
        check_call(('pgctl', 'start', 'sweet'))
        assert_command(
            ('pgctl', 'restart', 'sweet'),
            '',
            '''\
[pgctl] Stopping: sweet
[pgctl] ERROR: service 'sweet' failed to stop after {TIME} seconds, these runaway processes did not stop:
{PS-HEADER}
{PS-STATS} sleep infinity

There are two ways you can fix this:
  * temporarily: pgctl stop --force playground/sweet
  * permanently: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

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

    def it_shows_error_on_stop_for_slow_start(self):
        check_call(('pgctl', 'start', 'slow-startup'))
        assert_command(
            ('pgctl', 'restart', 'slow-startup'),
            '',
            '''\
[pgctl] Stopping: slow-startup
[pgctl] ERROR: service 'slow-startup' failed to stop after {TIME} seconds, these runaway processes did not stop:
{PS-HEADER}
{PS-STATS} sleep 987654

There are two ways you can fix this:
  * temporarily: pgctl stop --force playground/slow-startup
  * permanently: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

==> playground/slow-startup/logs/current <==
{TIMESTAMP} pgctl-poll-ready: service's ready check succeeded
{TIMESTAMP} pgctl-poll-ready: service is stopping -- quitting the poll
[pgctl]
[pgctl] There might be useful information further up in the log; you can view it by running:
[pgctl]     less +G playground/slow-startup/logs/current
[pgctl] ERROR: Some services failed to stop: slow-startup
''',
            1,
            norm=norm.pgctl,
        )

    def it_warns_on_forcelly_stop_for_sweet(self):
        check_call(('pgctl', 'start', 'sweet'))
        assert_command(
            ('pgctl', 'restart', 'sweet', '--force'),
            '',
            '''\
[pgctl] Stopping: sweet
[pgctl] WARNING: Killing these runaway processes at user's request (--force):
{PS-HEADER}
{PS-STATS} sleep infinity

Learn why they did not stop: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

[pgctl] Stopped: sweet
[pgctl] Starting: sweet
[pgctl] Started: sweet
''',
            0,
            norm=norm.pgctl,
        )

    def it_warns_on_forcelly_stop_for_slow_start(self):
        check_call(('pgctl', 'start', 'slow-startup'))
        assert_command(
            ('pgctl', 'restart', 'slow-startup', '--force'),
            '',
            '''\
[pgctl] Stopping: slow-startup
[pgctl] WARNING: Killing these runaway processes at user's request (--force):
{PS-HEADER}
{PS-STATS} sleep 987654

Learn why they did not stop: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

[pgctl] Stopped: slow-startup
[pgctl] Starting: slow-startup
[pgctl] Started: slow-startup
''',
            0,
            norm=norm.pgctl,
        )

    def it_ignores_force_flag_upon_normal_start(self):
        assert_command(
            ('pgctl', 'start', 'sweet', '--force'),
            '',
            '''\
[pgctl] Starting: sweet
[pgctl] Started: sweet
''',
            0,
        )

    def it_ignores_force_flag_upon_dirty_start(self):
        check_call(('pgctl', 'start', 'sweet'))

        with pytest.raises(subprocess.CalledProcessError):
            check_call(('pgctl', 'stop', 'sweet'))

        assert_command(
            ('pgctl', 'start', 'sweet', '--force'),
            '',
            '''\
[pgctl] Starting: sweet
[pgctl] ERROR: these runaway processes did not stop:
{PS-HEADER}
{PS-STATS} sleep infinity

There are two ways you can fix this:
  * temporarily: pgctl stop --force playground/sweet
  * permanently: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

''',
            1,
            norm=norm.pgctl,
        )


class DescribeSlowShutdownOnForeground(DirtyTest):
    """This test case takes three seconds to shut down"""

    @pytest.yield_fixture()
    def service_name(self):
        yield 'slow-shutdown'

    @pytest.yield_fixture(autouse=True)
    def environment(self):
        os.environ['PGCTL_TIMEOUT'] = '1.5'
        yield
        del os.environ['PGCTL_TIMEOUT']

    @pytest.yield_fixture(autouse=True)
    def configure_sleeptime(self):
        with set_slow_shutdown_sleeptime(0.75, 2.5):
            yield

    def it_fails_by_default(self):
        check_call(('pgctl', 'start'))
        assert_svstat('playground/sweet', state='up')
        assert_command(
            ('pgctl', 'stop'),
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

    def it_succeeds_on_forceful_stop(self):
        check_call(('pgctl', 'start'))
        assert_svstat('playground/sweet', state='up')
        assert_command(
            ('pgctl', 'stop', '--force'),
            '',
            '''\
[pgctl] Stopping: sweet
[pgctl] WARNING: Killing these runaway processes at user's request (--force):
{PS-HEADER}
{PS-STATS} {S6-PROCESS}
{PS-STATS} \\_ /bin/bash ./run
{PS-STATS} \\_ sleep 2.5

Learn why they did not stop: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

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

        check_call(('pgctl', 'stop'))
        assert_svstat('playground/sweet', state=SvStat.UNSUPERVISED)


class DescribeSlowShutdownOnBackground(DirtyTest):

    @pytest.yield_fixture()
    def service_name(self):
        yield 'slow-shutdown'

    @pytest.yield_fixture(autouse=True)
    def environment(self):
        os.environ['PGCTL_TIMEOUT'] = '1.5'
        yield
        del os.environ['PGCTL_TIMEOUT']

    @pytest.yield_fixture(autouse=True)
    def configure_sleeptime(self):
        with set_slow_shutdown_sleeptime(2.5, 0.75):
            yield

    def it_fails_by_leaking_runaway_process_on_stop(self):
        check_call(('pgctl', 'start'))
        assert_svstat('playground/sweet', state='up')

        assert_command(
            ('pgctl', 'stop'),
            '',
            '''\
[pgctl] Stopping: sweet
[pgctl] ERROR: service 'sweet' failed to stop after {TIME} seconds, these runaway processes did not stop:
{PS-HEADER}
{PS-STATS} sleep 2.5

There are two ways you can fix this:
  * temporarily: pgctl stop --force playground/sweet
  * permanently: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

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
            check_call(('pgctl', 'stop'))

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

    def it_succeeds_on_forceful_stop(self):
        check_call(('pgctl', 'start'))
        assert_svstat('playground/sweet', state='up')
        assert_command(
            ('pgctl', 'stop', '--force'),
            '',
            '''\
[pgctl] Stopping: sweet
[pgctl] WARNING: Killing these runaway processes at user's request (--force):
{PS-HEADER}
{PS-STATS} sleep 2.5

Learn why they did not stop: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

[pgctl] Stopped: sweet
''',
            0,
            norm=norm.pgctl,
        )
