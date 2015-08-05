# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from subprocess import check_call
from subprocess import PIPE
from subprocess import Popen

from pytest import yield_fixture as fixture
from testing import run

from pgctl.cli import svstat


class DescribeDateExample(object):

    @fixture
    def service_name(self):
        yield 'date'

    def it_does_start(self, in_example_dir):
        assert not os.path.isfile('now.date')
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            assert os.path.isfile('now.date')
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))


class DescribeTailExample(object):

    @fixture
    def service_name(self):
        yield 'tail'

    def it_does_start(self, in_example_dir):
        test_string = 'oh, hi there.\n'
        with open('input', 'w') as input:
            input.write(test_string)
        assert not os.path.isfile('output')

        check_call(('pgctl-2015', 'start', 'tail'))
        try:
            assert os.path.isfile('output')
            assert open('output').read() == test_string
        finally:
            check_call(('pgctl-2015', 'stop', 'tail'))


class DescribeStart(object):

    def it_fails_given_unknown(self, in_example_dir):
        p = Popen(('pgctl-2015', 'start', 'unknown'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == 'Starting: unknown\n'
        assert "No such playground service: 'unknown'\n" == stderr
        assert p.returncode == 1

    def it_is_idempotent(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            check_call(('pgctl-2015', 'start', 'date'))
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))


class DescribeStop(object):

    def it_does_stop(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        check_call(('pgctl-2015', 'stop', 'date'))

        assert svstat('playground/date') == 'down'

    def it_is_successful_before_start(self, in_example_dir):
        check_call(('pgctl-2015', 'stop', 'date'))

    def it_fails_given_unknown(self, in_example_dir):
        p = Popen(('pgctl-2015', 'stop', 'unknown'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == 'Stopping: unknown\n'
        assert "No such playground service: 'unknown'\n" == stderr
        assert p.returncode == 1


class DescribeRestart(object):

    def it_is_just_stop_then_start(self, in_example_dir):
        p = Popen(('pgctl-2015', 'restart', 'date'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == '''\
Stopping: date
Stopped: date
Starting: date
Started: date
'''
        assert '' == stderr
        assert p.returncode == 0
        assert svstat('playground/date') == 'up'

    def it_also_works_when_up(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        assert svstat('playground/date') == 'up'

        self.it_is_just_stop_then_start(in_example_dir)
