import sys
from unittest import mock

import pytest

import pgctl.cli
from pgctl.cli import _humanize_seconds
from pgctl.cli import PgctlApp
from pgctl.cli import TermStyle
from pgctl.daemontools import SvStat
from pgctl.service import Service


@pytest.mark.parametrize(('seconds', 'expected'), [
    (0, '0 seconds'),
    (59, '59 seconds'),
    (60, '1.0 minutes'),
    (7000, '1.9 hours'),
])
def test_humanize_seconds(seconds, expected):
    assert _humanize_seconds(seconds) == expected


def test_termstyle_wrap_no_colors_if_no_tty():
    with mock.patch.object(sys.stdout, 'isatty', return_value=False):
        assert TermStyle.wrap('hello world', TermStyle.RED) == 'hello world'


def test_termstyle_wrap_uses_colors_if_tty():
    with mock.patch.object(sys.stdout, 'isatty', return_value=True):
        assert (
            TermStyle.wrap('hello world', TermStyle.RED) ==
            '\033[91mhello world\033[0m'
        )


def fake_statuses(statuses):
    app = PgctlApp()
    app.services = []
    for name, status in statuses:
        service = Service('/dev/null', '/dev/null', 100)
        service.svstat = mock.Mock(spec=service.svstat)
        service.svstat.return_value = status
        service.name = name
        app.services.append(service)
    return app


@pytest.mark.parametrize(('statuses', 'expected'), [
    (
        (
            ('derp', SvStat('down', 5678, 1, 23, 'starting')),
            ('herp', SvStat('up', 1234, None, 23, None)),
        ),
        ' ● derp: down\n'
        '   └─ pid: 5678, exitcode: 1, 23 seconds, starting\n'
        ' ● herp: up\n'
        '   └─ pid: 1234, 23 seconds',
    ),
])
def test_status(statuses, expected):
    with mock.patch.object(pgctl.cli, 'unbuf_print') as mock_print:
        app = fake_statuses(statuses)
        app.status()

    printed = '\n'.join(
        call[0][0] for call in mock_print.call_args_list
    )
    assert printed == expected


def test_stop_logs_state():
    """Because StopLogs executes a SIGKILL, the timeout can go unused in tests,
    which causes coverage to miss the function. So we test it directly here.
    """
    class FakeService:
        timeout_stop = 5
        name = 'fake_service'
    assert pgctl.cli.StopLogs(FakeService).get_timeout() == 5
