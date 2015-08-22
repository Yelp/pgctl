# -*- coding: utf-8 -*-
# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import unicode_literals

from pytest import yield_fixture as fixture

from pgctl import configsearch


@fixture
def testfile(tmpdir):
    yield tmpdir.join('a', 'b', 'testfile').ensure()


class DescribeAnyInsecurePathSegment(object):

    def it_allows_writable_by_owner(self, testfile):
        testfile.chmod(0o644)
        assert configsearch.any_insecure_path_segment(testfile.strpath) is None

    def it_allows_minimal_permissions(self, testfile):
        testfile.chmod(0o000)
        assert configsearch.any_insecure_path_segment(testfile.strpath) is None

    def it_doesnt_allow_writable_by_group(self, testfile):
        testfile.chmod(0o464)
        assert configsearch.any_insecure_path_segment(testfile.strpath) == testfile.strpath

    def it_doesnt_allow_writable_by_others(self, testfile):
        testfile.chmod(0o446)
        assert configsearch.any_insecure_path_segment(testfile.strpath) == testfile.strpath

    def it_doesnt_allow_directory_writable_by_others(self, testfile):
        parentdir = testfile.join('../..')
        parentdir.chmod(0o757)
        assert configsearch.any_insecure_path_segment(testfile.strpath) == parentdir.strpath

    def it_doesnt_allow_writable_by_wrong_owner(self, testfile):
        import mock
        import os
        with mock.patch.object(os, 'getuid', lambda: None):
            assert configsearch.any_insecure_path_segment(testfile.strpath) == testfile.strpath

    def it_does_allow_readonly_by_wrong_owner(self, testfile):
        import mock
        import os
        with mock.patch.object(os, 'getuid', lambda: None):
            assert configsearch.any_insecure_path_segment(testfile.strpath) == testfile.strpath


class DescribeGlob(object):

    def it_globs_secure_files(self, tmpdir):
        tmpdir.ensure('a/file.1').chmod(0o444)
        tmpdir.ensure('b/file.2').chmod(0o666)
        tmpdir.ensure('c/junk.3').chmod(0o444)
        tmpdir.ensure('d/file.4').chmod(0o644)
        tmpdir.ensure('e/file.4').chmod(0o644)
        tmpdir.join('e').chmod(0o777)
        with tmpdir.as_cwd():
            assert list(configsearch.glob('*/file.*')) == ['a/file.1', 'd/file.4']
