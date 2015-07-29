# -*- coding: utf-8 -*-
# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from pytest import yield_fixture as fixture
from testfixtures import ShouldRaise

from pgctl.flock import flock
from pgctl.flock import Locked


@fixture
def tmpfile(tmpdir):
    tmpfile = tmpdir.join('tmpfile')
    assert not tmpfile.exists()
    yield tmpfile.strpath


def assert_locked(tmpfile):
    with ShouldRaise(Locked(11)):
        with flock(tmpfile):
            raise AssertionError('this should not work')


class DescribeFlock(object):

    def it_allows_first_caller(self, tmpfile):
        with flock(tmpfile):
            print('oh, hi!')

    def it_disallows_subsequent_callers(self, tmpfile):
        with flock(tmpfile):
            print('oh, hi!')

            assert_locked(tmpfile)

    def it_releases_lock_on_exit(self, tmpfile):
        with flock(tmpfile):
            print('oh, hi!')

        with flock(tmpfile):
            print('oh, hi!')

    def it_creates_a_file_if_it_didnt_exist(self, tmpfile):
        from os.path import exists
        assert not exists(tmpfile)
        with flock(tmpfile):
            print('oh, hi!')
        assert exists(tmpfile)

    def it_works_fine_with_a_directory(self, tmpfile):
        import os.path

        assert not os.path.isdir(tmpfile)
        os.mkdir(tmpfile)

        with flock(tmpfile):
            print('oh, hi!')

        assert os.path.isdir(tmpfile)

    def it_stays_locked_for_the_lifetime_of_subprocesses(self, tmpfile):
        from subprocess import Popen

        with flock(tmpfile):
            p = Popen(('sleep', '99999'))
            assert p.poll() is None

            assert_locked(tmpfile)

        assert_locked(tmpfile)

        p.terminate()
        assert p.wait() == -15

        with flock(tmpfile):
            print('oh hi there!')
