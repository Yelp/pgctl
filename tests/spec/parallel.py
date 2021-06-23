from time import sleep

import pytest
from testing import norm
from testing.service_context import set_slow_shutdown_sleeptime
from testing.subprocess import assert_command
from testing.subprocess import show_both

from pgctl.subprocess import PIPE
from pgctl.subprocess import Popen


@pytest.yield_fixture(autouse=True)
def sleep_short_background_long_foreground():
    with set_slow_shutdown_sleeptime(0.75, 2.25):
        yield


@pytest.mark.parametrize('service_name', ['slow-shutdown'])
@pytest.mark.usefixtures('in_example_dir')
def it_is_disallowed():
    assert_command(
        ('pgctl', 'start'),
        '',
        '''\
[pgctl] Starting: sweet
[pgctl] Started: sweet
''',
        0,
    )

    first = Popen(('pgctl', 'restart'), stdout=PIPE, stderr=PIPE)

    # slow-shutdown takes two seconds to shut down; aim for the middle:
    sleep(1)

    second = Popen(('pgctl', 'restart'), stdout=PIPE, stderr=PIPE)

    first_stdout, first_stderr = first.communicate()
    first_stdout, first_stderr = first_stdout.decode('UTF-8'), first_stderr.decode('UTF-8')
    show_both(first_stdout, first_stderr)
    assert norm.pgctl(first_stderr) == '''\
[pgctl] Stopping: sweet
[pgctl] ERROR: service 'sweet' failed to stop after {TIME} seconds, its status is ready (pid {PID}) {TIME} seconds
==> playground/sweet/logs/current <==
{TIMESTAMP} sweet
{TIMESTAMP} sweet_error
[pgctl]
[pgctl] There might be useful information further up in the log; you can view it by running:
[pgctl]     less +G playground/sweet/logs/current
[pgctl] ERROR: Some services failed to stop: sweet
'''
    assert first_stdout == ''
    assert first.returncode == 1

    second_stdout, second_stderr = second.communicate()
    second_stdout, second_stderr = second_stdout.decode('UTF-8'), second_stderr.decode('UTF-8')
    show_both(second_stdout, second_stderr)
    assert norm.pgctl(second_stderr) == '''\
[pgctl] ERROR: another pgctl command is currently managing this service: (playground/sweet/.pgctl.lock)
{PS-HEADER}
{PS-STATS} ${PREFIX}/bin/python ${PREFIX}/bin/pgctl restart

'''
    assert second_stdout == ''
    assert second.returncode == 1
