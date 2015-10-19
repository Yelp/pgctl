# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import unicode_literals

from sys import executable

from testfixtures import ShouldRaise
from testing.subprocess import assert_command


def assert_does_not_find(path):
    assert_command(
        (executable, '-m', 'pgctl.fuser', path),
        '',
        '',
        0,
    )


def it_can_find_the_user(tmpdir):
    testfile = tmpdir.join('testfile').ensure()
    assert_does_not_find(str(testfile))

    with testfile.open():
        with ShouldRaise(AssertionError):
            assert_does_not_find(str(testfile))

        from os import getpid
        assert_command(
            (executable, '-m', 'pgctl.fuser', str(testfile)),
            '%i\n' % getpid(),
            '',
            0,
            close_fds=True,
        )

    assert_does_not_find(str(testfile))


def it_properly_ignores_nosuchfile():
    assert_does_not_find('nosuchfile')
