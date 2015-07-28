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


def svstat_stdout_check(service, state):
    p = Popen(('svstat', 'playground/{}'.format(service)), stdout=PIPE, stderr=PIPE)
    stdout, stderr = run(p)
    assert stderr == ''
    assert 'playground/{0}: {1}'.format(service, state) in stdout


class DescribeDateExample(object):

    @fixture
    def service_name(self):
        yield 'date'

    def it_does_start(self, in_example_dir, request):
        assert not os.path.isfile('now.date')
        check_call(('pgctl-2015', 'start', 'date'))

        assert os.path.isfile('now.date')

        def fin():
            check_call(('pgctl-2015', 'stop', 'date'))
        request.addfinalizer(fin)


class DescribeTailExample(object):

    @fixture
    def service_name(self):
        yield 'tail'

    def it_does_start(self, in_example_dir, request):
        test_string = 'oh, hi there.\n'
        with open('input', 'w') as input:
            input.write(test_string)
        assert not os.path.isfile('output')

        check_call(('pgctl-2015', 'start', 'tail'))

        assert os.path.isfile('output')
        assert open('output').read() == test_string

        def fin():
            check_call(('pgctl-2015', 'stop', 'tail'))
        request.addfinalizer(fin)


class DescribeStart(object):

    def it_fails_given_unknown(self, in_example_dir):
        p = Popen(('pgctl-2015', 'start', 'unknown'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == ''
        assert "No such playground service: 'unknown'" in stderr
        assert p.returncode == 1

    def it_is_idempotent(self, in_example_dir, request):
        check_call(('pgctl-2015', 'start', 'date'))
        check_call(('pgctl-2015', 'start', 'date'))

        def fin():
            check_call(('pgctl-2015', 'stop', 'date'))
        request.addfinalizer(fin)


class DescribeStop(object):

    def it_does_stop(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        check_call(('pgctl-2015', 'stop', 'date'))

        svstat_stdout_check('date', 'down')

    def it_is_successful_before_start(self, in_example_dir):
        check_call(('pgctl-2015', 'stop', 'date'))
