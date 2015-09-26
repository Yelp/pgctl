from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os

import pytest
from testing import assert_command
from testing.assertions import assert_svstat

from pgctl.daemontools import SvStat


pytestmark = pytest.mark.usefixtures('in_example_dir')


@pytest.yield_fixture
def service_name():
    yield 'slow-startup'


def it_times_out():
    assert_command(
        ('pgctl-2015', 'start'),
        '',
        '''\
Starting: slow-startup
ERROR: service slow-startup timed out at 2 seconds: not ready
Started: slow-startup
Stopping: slow-startup
Stopped: slow-startup
ERROR: Some services failed to start: slow-startup
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
            'Starting: slow-startup\nStarted: slow-startup\n',
            0
        )
    assert_svstat('playground/slow-startup', state='ready')
