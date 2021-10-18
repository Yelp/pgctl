import pytest
from testing import norm
from testing.assertions import assert_svstat
from testing.assertions import wait_for
from testing.subprocess import assert_command


pytestmark = pytest.mark.usefixtures('in_example_dir')


@pytest.fixture
def service_name():
    yield 'unreliable'


def it_fails_twice_but_doesnt_restart():

    def it_is_ready():
        assert_svstat('playground/unreliable', state='ready')

    assert_command(
        ('pgctl', 'start'),
        '',
        '[pgctl] Starting: unreliable\n[pgctl] Started: unreliable\n',
        0
    )
    wait_for(it_is_ready)

    assert_command(
        ('pgctl', 'log'),
        '''\
==> playground/unreliable/logs/current <==
{TIMESTAMP} pgctl-poll-ready: service's ready check succeeded
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
{TIMESTAMP} pgctl-poll-ready: failed (restarting in {TIME} seconds)
''',
        '',
        0,
        norm=norm.pgctl,
    )
