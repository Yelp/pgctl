import os
import shutil
from unittest import mock

import pytest
from testing.assertions import wait_for

from pgctl.log_viewer import LogViewer
from pgctl.log_viewer import Tailer
from pgctl.log_viewer import TailEvent


def test_tailer(tmp_path):
    file_a = (tmp_path / 'a').open('a+')
    file_b = (tmp_path / 'b').open('a+')

    # At the start there should be no lines.
    tailer = Tailer((file_a.name, file_b.name))
    assert tailer.new_lines_available() is False
    assert tailer.get_logs() == []

    # It should pick up changes to a single file.
    file_a.write('A\n')
    file_a.flush()
    wait_for(lambda: tailer.new_lines_available() is True)
    assert tailer.get_logs() == [TailEvent(file_a.name, [b'A'])]

    assert tailer.new_lines_available() is False
    assert tailer.get_logs() == []

    # It should pick up changes to multiple files.
    file_a.write('A\nA\n')
    file_a.flush()
    file_b.write('B\n')
    file_b.flush()
    wait_for(lambda: len(tailer._poll.poll()) == 2)
    assert tailer.new_lines_available() is True
    assert sorted(tailer.get_logs()) == [
        TailEvent(file_a.name, [b'A', b'A']),
        TailEvent(file_b.name, [b'B']),
    ]

    # It can stop tailing a file.
    tailer.stop_tailing(file_a.name)
    file_a.write('A\n')
    file_a.flush()
    file_b.write('B\n')
    file_b.flush()
    wait_for(lambda: tailer.new_lines_available() is True)
    assert tailer.get_logs() == [TailEvent(file_b.name, [b'B'])]

    tailer.cleanup()


@pytest.fixture
def mock_terminal_width():
    fake_size = os.terminal_size((40, 40))
    with mock.patch.object(shutil, 'get_terminal_size', autospec=True, return_value=fake_size) as m:
        yield m


@pytest.mark.parametrize(
    ('size', 'expected_width'),
    (
        (os.terminal_size((40, 20)), 40),
        (os.terminal_size((0, 0)), 80),
        (os.terminal_size((-1, -1)), 80),
    ),
)
def test_log_viewer_terminal_width(size, expected_width, mock_terminal_width):
    mock_terminal_width.return_value = size
    log_viewer = LogViewer(10, {})
    assert log_viewer._terminal_width() == expected_width


@pytest.mark.usefixtures('mock_terminal_width')
def test_log_viewer(tmp_path):
    test_file = (tmp_path / 'test').open('a+')
    log_viewer = LogViewer(10, {'test': test_file.name})
    # A redraw is always needed at the start.
    assert log_viewer.redraw_needed() is True
    # Has not drawn so moving to top is a noop.
    assert log_viewer.move_cursor_to_top() == ''

    # It should initially draw an empty box.
    assert log_viewer.draw_logs('My cool logs:') == (
        '\x1b[?7lMy cool logs:\n'
        '\x1b[?7h\x1b[?7l\x1b[?25l\x1b[1m╔═════════════════════════════════════╗\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m                                     \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m                                     \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m                                     \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m                                     \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m                                     \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m                                     \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m                                     \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m                                     \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m╚═════════════════════════════════════╝\x1b[0K\x1b[0m\n'
        '\x1b[?7h\x1b[?25h'
    )
    assert log_viewer.redraw_needed() is False

    # It should pick up on log changes.
    test_file.write(''.join(f'my cool log {i}\n' for i in range(30)))
    test_file.flush()
    wait_for(lambda: log_viewer.redraw_needed() is True)
    assert log_viewer.move_cursor_to_top() == '\x1b[11F'
    assert log_viewer.clear_below() == '\x1b[0J'

    # It should now draw a box with the log lines.
    assert log_viewer.draw_logs('My cool logs:') == (
        '\x1b[?7lMy cool logs:\n'
        '\x1b[?7h\x1b[?7l\x1b[?25l\x1b[1m╔═════════════════════════════════════╗\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m[test] my cool log 22                \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m[test] my cool log 23                \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m[test] my cool log 24                \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m[test] my cool log 25                \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m[test] my cool log 26                \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m[test] my cool log 27                \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m[test] my cool log 28                \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m║\x1b[0m[test] my cool log 29                \x1b[39G\x1b[1m║\x1b[0K\x1b[0m\n'
        '\x1b[1m╚═════════════════════════════════════╝\x1b[0K\x1b[0m\n'
        '\x1b[?7h\x1b[?25h'
    )
    assert log_viewer.redraw_needed() is False

    log_viewer.cleanup()
