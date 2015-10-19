# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
import signal
from subprocess import check_call

import pytest
from testing import norm
from testing.assertions import assert_svstat
from testing.subprocess import assert_command

from pgctl.daemontools import SvStat
from pgctl.errors import LockHeld
from pgctl.functions import check_lock
from pgctl.fuser import fuser


def clean_service(service_path):
    # we use SIGTERM; SIGKILL is cheating.
    limit = 100
    while limit > 0:  # pragma: no branch: we don't expect to ever hit the limit
        assert os.path.isdir(service_path), service_path
        try:
            check_lock(service_path)
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
  \\* temporarily: lsof -t playground/{service} | xargs kill -9
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
            ('pgctl-2015', 'start'),
            '',
            '''\
[pgctl] Starting: slow-startup, sweet
[pgctl] Started: sweet
[pgctl] Started: slow-startup
''',
            0,
        )
        assert_command(
            ('pgctl-2015', 'log'),
            '''\
==> playground/slow-startup/log <==
{TIMESTAMP} pgctl-poll-ready: service's ready check succeeded

==> playground/sweet/log <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error
''',
            '',
            0,
            norm=norm.pgctl,
        )

    def it_shows_error_on_stop_for_sweet(self):
        assert_command(
            ('pgctl-2015', 'start', 'sweet'),
            '',
            '''\
[pgctl] Starting: sweet
[pgctl] Started: sweet
''',
            0,
        )
        assert_command(
            ('pgctl-2015', 'restart', 'sweet'),
            '',
            '''\
[pgctl] Stopping: sweet
[pgctl] ERROR: service 'sweet' failed to stop after {TIME} seconds, these runaway processes did not stop:
{PS-HEADER}
{PS-STATS} sleep infinity

There are two ways you can fix this:
  * temporarily: lsof -t playground/sweet | xargs kill -9
  * permanently: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

==> playground/sweet/log <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error
[pgctl] ERROR: Some services failed to stop: sweet
''',
            1,
            norm=norm.pgctl,
        )

    def it_shows_error_on_stop_for_slow_start(self):
        assert_command(
            ('pgctl-2015', 'start', 'slow-startup'),
            '',
            '''\
[pgctl] Starting: slow-startup
[pgctl] Started: slow-startup
''',
            0,
        )
        assert_command(
            ('pgctl-2015', 'restart', 'slow-startup'),
            '',
            '''\
[pgctl] Stopping: slow-startup
[pgctl] ERROR: service 'slow-startup' failed to stop after {TIME} seconds, these runaway processes did not stop:
{PS-HEADER}
{PS-STATS} sleep 987654

There are two ways you can fix this:
  * temporarily: lsof -t playground/slow-startup | xargs kill -9
  * permanently: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services

==> playground/slow-startup/log <==
{TIMESTAMP} pgctl-poll-ready: service's ready check succeeded
{TIMESTAMP} pgctl-poll-ready: service is stopping -- quitting the poll
[pgctl] ERROR: Some services failed to stop: slow-startup
''',
            1,
            norm=norm.pgctl,
        )


class DescribeSlowShutdown(DirtyTest):
    """This test case takes three seconds to shut down"""

    @pytest.yield_fixture()
    def service_name(self):
        yield 'slow-shutdown'

    @pytest.yield_fixture(autouse=True)
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
            '''\
[pgctl] Stopping: sweet
[pgctl] ERROR: service 'sweet' failed to stop after {TIME} seconds, its status is ready (pid {PID}) {TIME} seconds
==> playground/sweet/log <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error
[pgctl] ERROR: Some services failed to stop: sweet
''',
            1,
            norm=norm.pgctl,
        )

    def it_can_shut_down_successfully(self):
        # if we configure it to wait a bit longer, it works fine
        with open('playground/sweet/timeout-stop', 'w') as timeout:
            timeout.write('3')

        check_call(('pgctl-2015', 'start'))
        assert_svstat('playground/sweet', state='up')

        check_call(('pgctl-2015', 'restart'))
        assert_svstat('playground/sweet', state='up')

        check_call(('pgctl-2015', 'stop'))
        assert_svstat('playground/sweet', state=SvStat.UNSUPERVISED)
