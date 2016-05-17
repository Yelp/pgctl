from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import pytest
from testing import norm
from testing.assertions import assert_svstat
from testing.assertions import wait_for
from testing.subprocess import assert_command


pytestmark = pytest.mark.usefixtures('in_example_dir')


@pytest.yield_fixture
def service_name():
    yield 'unreliable'


def it_fails_twice_but_doesnt_restart():

    def it_is_ready():
        assert_svstat('playground/unreliable', state='ready')

    assert_command(
        ('pgctl-2015', 'start'),
        '',
        '[pgctl] Starting: unreliable\n[pgctl] Started: unreliable\n',
        0
    )
    wait_for(it_is_ready)

    assert_command(
        ('pgctl-2015', 'log'),
        '''\
==> playground/unreliable/log <==
{TIMESTAMP} pgctl-poll-ready: service's ready check succeeded
{TIMESTAMP} pgctl-poll-ready: failed (restarting in 2.00 seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in 1.99 seconds)
''',
        '',
        0,
        norm=norm.timestamp,
    )
