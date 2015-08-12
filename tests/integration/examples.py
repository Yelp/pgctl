# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from subprocess import check_call
from subprocess import PIPE
from subprocess import Popen

from pytest import yield_fixture as fixture
from testfixtures import StringComparison as S
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
        assert stdout == "Starting: ('unknown',)\n"
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

        assert svstat('playground/date')['playground/date'].state == 'down'

    def it_is_successful_before_start(self, in_example_dir):
        check_call(('pgctl-2015', 'stop', 'date'))

    def it_fails_given_unknown(self, in_example_dir):
        p = Popen(('pgctl-2015', 'stop', 'unknown'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == "Stopping: ('unknown',)\n"
        assert "No such playground service: 'unknown'\n" == stderr
        assert p.returncode == 1


class DescribeRestart(object):

    def it_is_just_stop_then_start(self, in_example_dir):
        p = Popen(('pgctl-2015', 'restart', 'date'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == '''\
Stopping: ('date',)
Stopped: ('date',)
Starting: ('date',)
Started: ('date',)
'''
        assert '' == stderr
        assert p.returncode == 0
        assert svstat('playground/date')['playground/date'].state == 'up'

    def it_also_works_when_up(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        assert svstat('playground/date')['playground/date'].state == 'up'

        self.it_is_just_stop_then_start(in_example_dir)


class DescribeStartMultipleServices(object):

    @fixture
    def service_name(self):
        yield 'multiple'

    def it_only_starts_the_indicated_services(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start', 'date'))

            assert svstat('playground/date')['playground/date'].state == 'up'
            assert svstat('playground/tail')['playground/tail'].state == 'down'
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_starts_multiple_services(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start', 'date', 'tail'))

            assert svstat('playground/date')['playground/date'].state == 'up'
            assert svstat('playground/tail')['playground/tail'].state == 'up'
        finally:
            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

    def it_stops_multiple_services(self, in_example_dir):
        try:
            check_call(('pgctl-2015', 'start', 'date', 'tail'))

            assert svstat('playground/date')['playground/date'].state == 'up'
            assert svstat('playground/tail')['playground/tail'].state == 'up'

            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

            status = svstat('playground/date', 'playground/tail')
            assert status['playground/date'].state == 'down'
            assert status['playground/tail'].state == 'down'
        finally:
            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

    def it_starts_everything_with_no_arguments_no_config(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start'))

            assert svstat('playground/date')['playground/date'].state == 'up'
            assert svstat('playground/tail')['playground/tail'].state == 'up'
        finally:
            check_call(('pgctl-2015', 'stop'))


class DescribeStatus(object):

    @fixture
    def service_name(self):
        yield 'multiple'

    def it_displays_correctly_when_the_service_is_down(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        check_call(('pgctl-2015', 'stop', 'date'))
        p = Popen(('pgctl-2015', 'status', 'date'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == S('date: down \\d+ seconds\\n$')
        assert stderr == ''

    def it_displays_correctly_when_the_service_is_up(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            p = Popen(('pgctl-2015', 'status', 'date'), stdout=PIPE, stderr=PIPE)
            stdout, stderr = run(p)
            assert stdout == S('date: up \\(pid \\d+\\) \\d+ seconds\\n$')
            assert stderr == ''
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_displays_the_status_of_multiple_services(self, in_example_dir):
        """Expect multiple services with status and PID"""
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            p = Popen(('pgctl-2015', 'status', 'date', 'tail'), stdout=PIPE, stderr=PIPE)
            stdout, stderr = run(p)
            assert stdout == S('''\
date: up \\(pid \\d+\\) \\d+ seconds
tail: down \\d+ seconds
$''')
            assert stderr == ''
            assert p.returncode == 0
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_displays_the_status_of_all_services(self, in_example_dir):
        """Expect all services to provide status when no service is specified"""
        check_call(('pgctl-2015', 'start', 'tail'))
        try:
            p = Popen(('pgctl-2015', 'status'), stdout=PIPE, stderr=PIPE)
            stdout, stderr = run(p)
            assert stdout == S('''\
date: down \\d+ seconds
tail: up \\(pid \\d+\\) \\d+ seconds
$''')
            assert stderr == ''
            assert p.returncode == 0
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_displays_status_when_supervise_is_down(self, in_example_dir):
        try:
            p = Popen(('pgctl-2015', 'status'), stdout=PIPE, stderr=PIPE)
            stdout, stderr = run(p)
            assert stdout == '''\
date: could not get status, supervisor is down
tail: could not get status, supervisor is down
'''
            assert stderr == ''
            assert p.returncode == 0
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_displays_status_for_unknown_services(self, in_example_dir):
        try:
            p = Popen(('pgctl-2015', 'status', 'garbage'), stdout=PIPE, stderr=PIPE)
            stdout, stderr = run(p)
            assert stdout == '''\
garbage: no such service
'''
            assert stderr == ''
            assert p.returncode == 0
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))
