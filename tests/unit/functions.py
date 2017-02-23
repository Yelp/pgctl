# -*- coding: utf-8 -*-
# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os

import mock
import pytest
import six
from frozendict import frozendict
from testfixtures import ShouldRaise
from testing.norm import norm_trailing_whitespace_json

import pgctl.subprocess
from pgctl.errors import LockHeld
from pgctl.functions import _show_runaway_processes
from pgctl.functions import _terminate_runaway_processes
from pgctl.functions import bestrelpath
from pgctl.functions import JSONEncoder
from pgctl.functions import unique


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
            _show_runaway_processes(lockfile.strpath)

        lock.close()

        _show_runaway_processes(lockfile.strpath)

    def it_passes_when_there_are_no_locks(self, tmpdir):
        assert _show_runaway_processes(tmpdir.strpath) is None


class DescribeTerminateRunawayProcesses(object):

    @pytest.yield_fixture
    def mock_subprocess_call(self):
        with mock.patch.object(pgctl.subprocess, 'call', autospec=True) as mock_call:
            yield mock_call

    def it_kills_processes_holding_the_lock(self, tmpdir, mock_subprocess_call):
        lockfile = tmpdir.ensure('lock')
        lock = lockfile.open()

        _terminate_runaway_processes(lockfile.strpath)
        mock_subprocess_call.assert_called_once_with(
            ('kill', '-9', '{}'.format(os.getpid()),)
        )

        lock.close()

    def it_passes_when_there_are_no_locks(self, tmpdir, mock_subprocess_call):
        lockfile = tmpdir.ensure('lock')

        _terminate_runaway_processes(lockfile.strpath)
        assert not mock_subprocess_call.called
