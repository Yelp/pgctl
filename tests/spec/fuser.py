# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import unicode_literals

from testfixtures import ShouldRaise
from testing.subprocess import assert_command
from testing.subprocess import run


def assert_does_not_find(path):
    assert_command(
        ('pgctl-fuser', path),
        '',
        '',
        0,
        close_fds=True,
    )


def it_can_find_the_user(tmpdir):
    testfile = tmpdir.join('testfile').ensure()
    assert_does_not_find(str(testfile))

    with testfile.open():
        with ShouldRaise(AssertionError):
            assert_does_not_find(str(testfile))

        from os import getpid
        assert_command(
            ('pgctl-fuser', str(testfile)),
            '%i\n' % getpid(),
            '',
            0,
            close_fds=True,
        )

    assert_does_not_find(str(testfile))


def it_can_find_deleted_user(tmpdir):
    testfile = tmpdir.join('testfile').ensure()
    assert_does_not_find(str(testfile))

    with testfile.open():
        testfile.remove()
        assert_does_not_find(str(testfile))

        from os import getpid
        assert_command(
            ('pgctl-fuser', '-d', str(testfile)),
            '%i\n' % getpid(),
            '',
            0,
            close_fds=True,
        )


def it_shows_help_given_no_arguments():
    out, err, returncode = run('pgctl-fuser')
    assert out == ''
    assert 'usage: pgctl-fuser' in err
    assert returncode == 2


def it_properly_ignores_nosuchfile():
    assert_does_not_find('nosuchfile')
