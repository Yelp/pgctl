from __future__ import absolute_import
from __future__ import unicode_literals

import os

import pytest
from testing import pty
from testing.assertions import assert_svstat
from testing.assertions import wait_for
from testing.subprocess import assert_command
from testing.subprocess import ctrl_c

from pgctl.daemontools import SvStat
from pgctl.subprocess import check_call
from pgctl.subprocess import PIPE
from pgctl.subprocess import Popen

pytestmark = pytest.mark.usefixtures('in_example_dir')
greeter_service = pytest.mark.parametrize('service_name', ['greeter'])
unreliable_service = pytest.mark.parametrize('service_name', ['unreliable'])


def read_line(fd):
    # read one-byte-at-a-time to avoid deadlocking by reading too much
    from os import read
    line = ''
    byte = None
    while byte not in ('\n', ''):
        byte = read(fd, 1).decode('utf-8')
        line += byte
    return line


@greeter_service
def assert_works_interactively():
    read, write = os.openpty()
    pty.normalize_newlines(read)
    # setsid: this simulates the shell's job-control behavior
    proc = Popen(('setsid', 'pgctl-2015', 'debug', 'greeter'), stdin=PIPE, stdout=write)
    os.close(write)

    try:
        assert read_line(read) == 'What is your name?\n'
        proc.stdin.write(b'Buck\n')
        proc.stdin.flush()
        assert read_line(read) == 'Hello, Buck.\n'
    finally:
        ctrl_c(proc)
        proc.wait()


@greeter_service
def it_works_with_nothing_running():
    assert_svstat('playground/greeter', state=SvStat.UNSUPERVISED)
    assert_works_interactively()


@greeter_service
def it_fails_with_multiple_services():
    assert_command(
        ('pgctl-2015', 'debug', 'abc', 'def'),
        '',
        '[pgctl] ERROR: Must debug exactly one service, not: abc, def\n',
        1,
    )


@greeter_service
def it_first_stops_the_background_service_if_running():
    check_call(('pgctl-2015', 'start', 'greeter'))
    assert_svstat('playground/greeter', state='up')

    assert_works_interactively()


@unreliable_service
def it_disables_polling():
    stderr = open('stderr', 'w')
    proc = Popen(('pgctl-2015', 'debug', 'unreliable'), stdin=open(os.devnull), stdout=PIPE, stderr=stderr)

    def check_file_contents():
        expected = '''\
[pgctl] Stopping: unreliable
[pgctl] Stopped: unreliable
pgctl-poll-ready: disabled during debug -- quitting
'''
        with open('stderr') as fd:
            actual = fd.read()
        return expected == actual

    wait_for(check_file_contents)
    proc.terminate()
    stderr.close()
