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


class DescribePgctlLog(object):

    @fixture
    def service_name(self):
        yield 'output'

    def it_is_empty_before_anything_starts(self, in_example_dir):
        p = Popen(('pgctl-2015', 'log'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == stderr == ''

    def it_shows_stdout_and_stderr(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'printstuff'))

        p = Popen(('pgctl-2015', 'log'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == 'sweet\nsweet_error\n'
        assert stderr == ''
        assert p.returncode == 0

        check_call(('pgctl-2015', 'restart', 'printstuff'))

        p = Popen(('pgctl-2015', 'log'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == 'sweet\nsweet_error\nsweet\nsweet_error\n'
        assert stderr == ''
        assert p.returncode == 0

    def it_is_line_buffered(self):
        """
        Show that the interleaved output of ohhi becomes separated per-line.
        """

    def it_distinguishes_multiple_services(self):
        """
        There's some indication of which output came from which services.
        A (colorized?) [servicename] prefix.
        """

    def it_distinguishes_stderr(self):
        """
        There's some indication of which output came from stderr.
        Red, with [error] prefix.
        """

    def it_has_timestamps(self):
        """By default each line of output is timestamped"""

    def it_can_disable_timestamps(self):
        """Users should be able to turn off the timestamp output. V3"""

    def it_can_disable_coloring(self):
        """Users should be able to turn off colored output. V3"""

    def it_automatically_disables_color_for_nontty(self):
        """When printing to a file, don't produce color, by default. V3"""

    def it_has_this_implementation(self, in_example_dir):
        assert not os.path.isfile('playground/printstuff/log/current')
        check_call(('pgctl-2015', 'start', 'printstuff'))
        try:
            assert os.path.isfile('playground/printstuff/log/current')
            with open('playground/printstuff/log/current', 'r') as f:
                contents = f.read()
            lines = contents.splitlines()
            assert lines[0].split(' ')[1] == 'sweet'
            assert lines[1].split(' ')[1] == 'sweet_error'
        finally:
            check_call(('pgctl-2015', 'stop', 'printstuff'))


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

        assert svstat('playground/date') == ['down']

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
        assert svstat('playground/date') == ['up']

    def it_also_works_when_up(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        assert svstat('playground/date') == ['up']

        self.it_is_just_stop_then_start(in_example_dir)


class DescribeStartMultipleServices(object):

    @fixture
    def service_name(self):
        yield 'multiple'

    def it_only_starts_the_indicated_services(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start', 'date'))

            assert svstat('playground/date') == ['up']
            assert svstat('playground/tail') == ['down']
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_starts_multiple_services(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start', 'date', 'tail'))

            assert svstat('playground/date') == ['up']
            assert svstat('playground/tail') == ['up']
        finally:
            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

    def it_stops_multiple_services(self, in_example_dir):
        try:
            check_call(('pgctl-2015', 'start', 'date', 'tail'))

            assert svstat('playground/date') == ['up']
            assert svstat('playground/tail') == ['up']

            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

            assert svstat('playground/date', 'playground/tail') == ['down', 'down']
        finally:
            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

    def it_starts_everything_with_no_arguments_no_config(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start'))

            assert svstat('playground/date') == ['up']
            assert svstat('playground/tail') == ['up']
        finally:
            check_call(('pgctl-2015', 'stop'))
