# -*- coding: utf-8 -*-
# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
import StringIO

import mock
import pytest
import six
from frozendict import frozendict
from testfixtures import ShouldRaise
from testing.assertions import wait_for
from testing.norm import norm_trailing_whitespace_json

from pgctl.errors import LockHeld
from pgctl.functions import bestrelpath
from pgctl.functions import JSONEncoder
from pgctl.functions import logger_preexec
from pgctl.functions import show_runaway_processes
from pgctl.functions import supervisor_preexec
from pgctl.functions import terminate_runaway_processes
from pgctl.functions import unique
from pgctl.fuser import fuser
from pgctl.subprocess import Popen


class DescribeUnique(object):

    def it_does_not_have_duplicates(self):
        data = ['b', 'b', 'b']
        assert list(unique(data)) == ['b']

    def it_removes_duplicates_with_first_one_wins_mentality(self):
        data = ['a', 'b', 'c', 'b', 'd', 'a']
        assert list(unique(data)) == ['a', 'b', 'c', 'd']


class DescribeJSONEncoder(object):

    def it_encodes_frozendict(self):
        test_dict = frozendict({
            'pgdir': 'playground',
            'services': ('default',),
            'aliases': frozendict({
                'default': ('')
            }),
        })
        result = JSONEncoder(sort_keys=True, indent=4).encode(test_dict)
        assert norm_trailing_whitespace_json(result) == '''\
{
    "aliases": {
        "default": ""
    },
    "pgdir": "playground",
    "services": [
        "default"
    ]
}'''

    def it_encodes_other(self):
        msg = 'type' if six.PY2 else 'class'
        with ShouldRaise(TypeError("<{} 'object'> is not JSON serializable".format(msg))):
            JSONEncoder(sort_keys=True, indent=4).encode(object)


class DescribeBestrelpath(object):

    def it_prefers_shorter_strings(self):
        assert bestrelpath('/a/b/c', '/a/b') == 'c'
        assert bestrelpath('/a/b', '/a/b/c') == '/a/b'
        assert bestrelpath('/a/b', '/a/b/c/d') == '/a/b'


class DescribeShowRunawayProcesses(object):

    def it_fails_when_there_are_locks(self, tmpdir):
        lockfile = tmpdir.ensure('lock')
        lock = lockfile.open()

        with ShouldRaise(LockHeld):
            show_runaway_processes(lockfile.strpath)

        lock.close()

        show_runaway_processes(lockfile.strpath)

    def it_passes_when_there_are_no_locks(self, tmpdir):
        assert show_runaway_processes(tmpdir.strpath) is None


class DescribeTerminateRunawayProcesses(object):

    def it_kills_processes_holding_the_lock(self, tmpdir):
        lockfile = tmpdir.ensure('lock')
        lock = lockfile.open()
        process = Popen(('sleep', 'infinity'))
        lock.close()

        # assert `process` has `lock`
        assert list(fuser(lockfile.strpath)) == [process.pid]

        with mock.patch('sys.stderr', new_callable=StringIO.StringIO) as mock_stderr:
            terminate_runaway_processes(lockfile.strpath)

        assert 'WARNING: Killing these runaway ' in mock_stderr.getvalue()
        wait_for(lambda: process.poll() == -9)

    def it_passes_when_there_are_no_locks(self, tmpdir):
        lockfile = tmpdir.ensure('lock')

        with mock.patch('sys.stderr', new_callable=StringIO.StringIO) as mock_stderr:
            terminate_runaway_processes(lockfile.strpath)
        assert mock_stderr.getvalue() == ''


class DescribePreexecFuncs(object):
    LOG_PIPE_FD = 5
    DEV_NULL_FD = 10

    @pytest.fixture(autouse=True)
    def mock_open(self):
        def fake_open(file_path, mode):  # pylint:disable=unused-argument
            if file_path == '/dev/null':
                return self.DEV_NULL_FD
            elif file_path == '/log/path':
                return self.LOG_PIPE_FD
            else:  # pragma: no cover
                raise Exception('Bad open call.')

        with mock.patch.object(os, 'open', new=fake_open):
            yield

    @pytest.fixture(autouse=True)
    def mock_close(self):
        def fake_close(fd):
            if fd not in [self.DEV_NULL_FD, self.LOG_PIPE_FD]:  # pragma: no cover
                raise Exception('Bad close call.')

        with mock.patch.object(os, 'close', new=fake_close):
            yield

    def it_works_for_loggers(self):
        # This can't be moved to a fixture because pytest
        # related dup2 calls will leak into the mock_calls list
        with mock.patch.object(
            os,
            'dup2',
            autospec=True,
        ) as mock_dup2:
            logger_preexec('/log/path')

        assert mock_dup2.mock_calls == [
            mock.call(self.LOG_PIPE_FD, 0),
            mock.call(self.DEV_NULL_FD, 1),
            mock.call(self.DEV_NULL_FD, 2),
        ]

    def it_works_for_superivsors(self):
        with mock.patch.object(
            os,
            'dup2',
            autospec=True,
        ) as mock_dup2:
            supervisor_preexec('/log/path')

        assert mock_dup2.mock_calls == [
            mock.call(self.DEV_NULL_FD, 0),
            mock.call(self.LOG_PIPE_FD, 1),
            mock.call(self.LOG_PIPE_FD, 2),
        ]
