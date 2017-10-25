# -*- coding: utf-8 -*-
# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import unicode_literals

from pgctl import configsearch


class DescribeGlob(object):

    def it_globs_files(self, tmpdir):
        tmpdir.ensure('a/file.1')
        tmpdir.ensure('d/file.4')
        with tmpdir.as_cwd():
            assert list(configsearch.glob('*/file.*')) == ['a/file.1', 'd/file.4']
