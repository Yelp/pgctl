from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os

import pytest
from testing import assert_command
from testing.assertions import assert_svstat
from testing.assertions import wait_for

from pgctl.daemontools import SvStat


pytestmark = pytest.mark.usefixtures('in_example_dir')


@pytest.yield_fixture
def service_name():
    yield 'slow-startup'


def it_times_out():
    assert_command(
        ('pgctl-2015', 'start'),
        '''\
==> playground/slow-startup/stdout.log <==

==> playground/slow-startup/stderr.log <==
''',
        '''\
[pgctl] Starting: slow-startup
[pgctl] ERROR: 'slow-startup' timed out at 2 seconds: not ready
[pgctl] Stopping: slow-startup
[pgctl] Stopped: slow-startup
[pgctl] ERROR: Some services failed to start: slow-startup
''',
        1
    )
    assert_svstat('playground/slow-startup', state=SvStat.UNSUPERVISED)


def it_can_succeed():
    import mock
    with mock.patch.dict(os.environ, [('PGCTL_TIMEOUT', '5')]):
        assert_command(
            ('pgctl-2015', 'start'),
            '',
            '[pgctl] Starting: slow-startup\n[pgctl] Started: slow-startup\n',
            0
        )
    assert_svstat('playground/slow-startup', state='ready')


def it_restarts_on_unready():

    def it_is_ready():
        assert_svstat('playground/slow-startup', state='ready')

    def it_stopped():
        assert_svstat('playground/slow-startup', state=SvStat.UNSUPERVISED)

    it_can_succeed()
    os.remove('playground/slow-startup/readyfile')
    wait_for(it_stopped)
    wait_for(it_is_ready, limit=5)
