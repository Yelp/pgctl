import json
from unittest import mock

import pytest

from pgctl import __version__
from pgctl import telemetry


@pytest.fixture
def mock_clog():
    with mock.patch.object(telemetry, '_clog_configured', True):
        with mock.patch.object(telemetry, 'clog') as fake_clog:
            yield fake_clog


def test_event_context():
    context = telemetry._event_context()
    assert context['time'].startswith('20')
    assert context['version'] == __version__


def test_emit_event(mock_clog):
    telemetry.emit_event('my_event', {'attr1': 'value1', 'attr2': 'value2'})
    call, = mock_clog.mock_calls
    _, args, _ = call

    assert args[0] == 'tmp_pgctl_events'
    payload = json.loads(args[1])
    assert payload['attributes'] == {
        'attr1': 'value1',
        'attr2': 'value2',
    }
    assert payload['event'] == 'my_event'

    # Just spot-checking some of the auto-injected context variables.
    assert 'version' in payload
    assert 'time' in payload
