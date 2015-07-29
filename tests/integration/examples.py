# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from subprocess import PIPE
from subprocess import Popen

from pytest import yield_fixture as fixture
from testing import run


class DescribeDateExample(object):

    @fixture
    def service_name(self):
        yield 'date'

    def it_does_start(self, in_example_dir):
        assert not os.path.isfile('now.date')
        p = Popen(('pgctl-2015', 'start', 'date'))
        p.wait()
        assert p.returncode == 0
        assert os.path.isfile('now.date')


class DescribeTailExample(object):

    @fixture
    def service_name(self):
        yield 'tail'

    def it_does_start(self, in_example_dir):
        test_string = 'oh, hi there.\n'
        with open('input', 'w') as input:
            input.write(test_string)
        assert not os.path.isfile('output')

        p = Popen(('pgctl-2015', 'start', 'tail'))
        p.wait()
        assert p.returncode == 0

        assert os.path.isfile('output')
        assert open('output').read() == test_string


class DescribeStart(object):

    def it_fails_given_unknown(self, in_example_dir):
        p = Popen(('pgctl-2015', 'start', 'unknown'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == ''
        assert "No such playground service: 'unknown'" in stderr
        assert p.returncode == 1

    def it_is_idempotent(self, in_example_dir):
        p = Popen(('pgctl-2015', 'start', 'date'))
        p.wait()
        assert p.returncode == 0
        p = Popen(('pgctl-2015', 'start', 'date'))
        p.wait()
        assert p.returncode == 0
