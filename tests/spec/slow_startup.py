from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from subprocess import call
from subprocess import check_call

import pytest
from testfixtures import StringComparison as S
from testing import assert_command
from testing.assertions import assert_svstat


pytestmark = pytest.mark.usefixtures('in_example_dir')


@pytest.yield_fixture
def service_name():
    yield 'slow-startup'


def it_reports_ready():
    import mock
    with mock.patch.dict(os.environ, [('SVWAIT', '5')]):
        check_call(('pgctl-2015', 'start'))
        assert_svstat('playground/slow-startup', state='ready')


def it_shuts_down_cleanly():
    check_call(('pgctl-2015', 'start'))
    check_call(('pgctl-2015', 'restart'))
    check_call(('pgctl-2015', 'stop'))


@pytest.mark.skipif(True, reason='')
def it_errors_with_bad_svpoll():
    import mock
    with mock.patch.dict(os.environ, [('SVPOLL', 'watt')]):
        assert call(('pgctl-2015', 'start')) == 1

    assert_command(
        ('pgctl-2015', 'log'),
        '',
        S('''(?s)\
==> playground/slow-startup/stdout\\.log <==

==> playground/slow-startup/stderr\\.log <==
Traceback (most recent call last):
File ".*
.*
ValueError: could not convert string to float: watt
$'''),
        0,
    )


@pytest.mark.skipif(True, reason='')
def it_errors_with_bad_svwait():
    import mock
    with mock.patch.dict(os.environ, [('SVWAIT', 'watt')]):
        assert call(('pgctl-2015', 'start')) == 1

    assert_command(
        ('pgctl-2015', 'log'),
        '',
        S('''(?s)\
==> playground/slow-startup/stdout\\.log <==

==> playground/slow-startup/stderr\\.log <==
Traceback (most recent call last):
File ".*
.*
ValueError: could not convert string to float: watt
$'''),
        0,
    )
