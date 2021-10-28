import fcntl
import os
import re
import select
import shutil
import subprocess
import typing


# https://stackoverflow.com/a/14693789
# 7-bit C1 ANSI sequences
ANSI_ESCAPES = re.compile(r'''
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
''', re.VERBOSE)


class TailEvent(typing.NamedTuple):
    path: str
    log_lines: typing.Tuple[str]


class Tailer:

    def __init__(self, paths: typing.Iterable[str]) -> None:
        self._poll = select.poll()
        self._path_to_tail = {}
        self._fdno_to_path = {}

        for path in paths:
            self._path_to_tail[path] = proc = subprocess.Popen(
                ('tail', '-F', path),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            self._fdno_to_path[proc.stdout.fileno()] = path
            self._poll.register(proc.stdout, select.POLLIN)

            # Put stdout in non-blocking mode so we can read from it without blocking.
            flags = fcntl.fcntl(proc.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK
            fcntl.fcntl(proc.stdout.fileno(), fcntl.F_SETFL, flags)

    def get_logs(self, timeout: typing.Optional[float] = 0) -> typing.List[TailEvent]:
        fd_events = self._poll.poll(timeout)
        ret = []
        for fd, event in fd_events:
            content = b''
            while True:
                try:
                    content += os.read(fd, 10000)
                except BlockingIOError:
                    break
            ret.append(TailEvent(self._fdno_to_path[fd], content.splitlines()))
        return ret

    def new_lines_available(self) -> bool:
        return len(self._poll.poll(0)) > 0

    def stop_tailing(self, path: str) -> None:
        proc = self._path_to_tail[path]
        self._poll.unregister(proc.stdout)
        del self._fdno_to_path[proc.stdout.fileno()]
        del self._path_to_tail[path]
        proc.terminate()
        proc.communicate()

    def cleanup(self) -> None:
        for path in tuple(self._path_to_tail):
            self.stop_tailing(path)


def _draw_box(width: int, height: int, content_lines: typing.Sequence[str]):
    inner_width = width - 2
    inner_height = height - 2
    assert inner_width >= 0, inner_width
    assert inner_height >= 0, inner_height
    assert len(content_lines) <= inner_height, (len(content_lines), inner_height)

    # Disable screen wrap.
    print('\x1b[?7l', end='')
    # Hide the cursor.
    print('\x1b[?25l', end='')

    # Top border.
    print('\x1b[1m╔' + '═' * inner_width + '╗\x1b[0K\x1b[0m')

    # Inside box and log lines.
    for i in range(inner_height):
        try:
            line = content_lines[i]
        except IndexError:
            line = ''
        line = line[:inner_width].ljust(inner_width)
        print('\x1b[1m║\x1b[0m' + line + f'\x1b[{width}G\x1b[1m║\x1b[0K\x1b[0m')

    # Bottom border.
    print('\x1b[1m╚' + '═' * inner_width + '╝\x1b[0K\x1b[0m')

    # Re-enable screen wrap.
    print('\x1b[?7h', end='')

    # Show the cursor.
    print('\x1b[?25h', end='', flush=True)


class LogViewer:

    def __init__(self, height: int, name_to_path: typing.Dict[str, str]):
        self._tailer = Tailer(name_to_path.values())
        self._prev_width = None
        self._visible_lines = []
        self._name_to_path = name_to_path
        self._path_to_name = {path: name for name, path in name_to_path.items()}
        self.height = height

    def move_cursor_to_top(self) -> None:
        if self._prev_width is not None:
            # Move cursor back to the top of the box.
            print(f'\x1b[{self.height + 2}F')

    def _terminal_width(self) -> int:
        return shutil.get_terminal_size((80, 20)).columns

    def redraw_needed(self) -> bool:
        return self._tailer.new_lines_available() or self._prev_width != self._terminal_width()

    def clear_below(self) -> None:
        print('\x1b[0J', end='', flush=True)

    def draw_logs(self, title: str) -> None:
        width = self._terminal_width()

        log_events = self._tailer.get_logs(0)
        for event in log_events:
            for line in event.log_lines:
                service = self._path_to_name[event.path]
                line = ANSI_ESCAPES.sub('', line.decode('utf8', errors='replace'))
                self._visible_lines.append(f'[{service}] {line}')
        self._visible_lines = self._visible_lines[-(self.height - 2):]

        # Disable screen wrap.
        print('\x1b[?7l', end='')
        print(title + '\x1b[0K')
        # Re-enable screen wrap.
        print('\x1b[?7h', end='')
        _draw_box(width - 1, self.height, self._visible_lines)

        self._prev_width = width

    def stop_tailing(self, name: str) -> None:
        self._tailer.stop_tailing(self._name_to_path[name])

    def cleanup(self) -> None:
        self._tailer.cleanup()
