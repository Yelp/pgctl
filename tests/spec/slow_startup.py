import os

import pytest
from py._path.local import LocalPath as Path
from testing import norm
from testing.assertions import assert_svstat
from testing.assertions import wait_for
from testing.subprocess import assert_command

from pgctl.daemontools import SvStat


pytestmark = pytest.mark.usefixtures('in_example_dir')
SLOW_STARTUP_TIME = 6


@pytest.fixture
def service_name():
    yield 'slow-startup'


def assert_it_times_out_regardless_force(is_force):
    assert_command(
        ('pgctl', 'start') + (('--force',) if is_force else ()),
        '''\
''',
        '''\
[pgctl] Starting: slow-startup
[pgctl] ERROR: service 'slow-startup' failed to start after {TIME} seconds, its status is up (pid {PID}) {TIME} seconds
==> playground/slow-startup/logs/current <==
[pgctl] Stopping: slow-startup
[pgctl] Stopped: slow-startup
[pgctl]
[pgctl] There might be useful information further up in the log; you can view it by running:
[pgctl]     less +G playground/slow-startup/logs/current
[pgctl] ERROR: Some services failed to start: slow-startup
''',
        1,
        norm=norm.pgctl,
    )
    assert_svstat('playground/slow-startup', state=SvStat.UNSUPERVISED)

    assert_command(
        ('pgctl', 'log'),
        '''\
==> playground/slow-startup/logs/current <==
{TIMESTAMP} pgctl-poll-ready: service is stopping -- quitting the poll
''',
        '',
        0,
        norm=norm.pgctl,
    )


def it_times_out():
    assert_it_times_out_regardless_force(is_force=False)


def it_times_out_because_force_is_ignored():
    assert_it_times_out_regardless_force(is_force=True)


def it_can_succeed():
    from unittest.mock import patch, ANY
    with patch.dict(os.environ, [('PGCTL_TIMEOUT', str(SLOW_STARTUP_TIME))]):
        assert_command(
            ('pgctl', 'start'),
            '',
            #'[pgctl] Starting: slow-startup\n[pgctl] Started: slow-startup\n',
            ANY,
            0
        )
    assert_svstat('playground/slow-startup', state='ready')


def it_restarts_on_unready():

    def it_is_ready():
        assert_svstat('playground/slow-startup', state='ready')

    def it_becomes_unready():
        from testfixtures import Comparison as C
        from pgctl.daemontools import svstat
        assert svstat('playground/slow-startup') != C(SvStat, {'state': 'ready'}, strict=False)

    it_can_succeed()
    os.remove('playground/slow-startup/readyfile')
    wait_for(it_becomes_unready)
    wait_for(it_is_ready)

    assert_command(
        ('pgctl', 'log'),
        '''\
==> playground/slow-startup/logs/current <==
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed for more than {TIME} seconds -- we are restarting this service for you
{TIMESTAMP} [pgctl] Stopping: slow-startup
{TIMESTAMP} [pgctl] Stopped: slow-startup
{TIMESTAMP} [pgctl] Starting: slow-startup
{TIMESTAMP} pgctl-poll-ready: service's ready check succeeded
{TIMESTAMP} [pgctl] Started: slow-startup
''',
        '',
        0,
        norm=norm.pgctl,
    )


def it_removes_down_file():
    path = Path(os.getcwd()).join('playground/slow-startup/down')
    path.ensure()
    assert path.check()
    it_can_succeed()
    assert not path.check()
