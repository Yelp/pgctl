from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import time

import pytest

from pgctl.subprocess import check_call

pytestmark = pytest.mark.usefixtures('in_example_dir')
SLOW_STARTUP_TIME = 6


@pytest.yield_fixture
def service_name():
    yield 'poll-ready-quick-shutdown'


def it_stops_quickly():
    """Tests a regression in pgctl where services using pgctl-poll-ready fail to
    stop because the background process started by pgctl-poll-ready isn't dying
    quickly."""
    check_call(('pgctl', 'start'))
    prestop_time = time.time()
    check_call(('pgctl', 'stop'))
    poststop_time = time.time()
    assert poststop_time - prestop_time < 2
