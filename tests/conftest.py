# -*- coding: utf-8 -*-
# pylint:disable=redefined-outer-name,unused-argument
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import shutil

from py._path.local import LocalPath as Path
from pytest import yield_fixture as fixture

TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@fixture
def in_example_dir(tmpdir, service_name):
    os.environ['XDG_RUNTIME_DIR'] = tmpdir.join('.run').strpath

    template_dir = os.path.join(TOP, 'tests/examples', service_name)
    tmpdir = tmpdir.join(service_name)
    shutil.copytree(template_dir, tmpdir.strpath)

    with tmpdir.as_cwd():
        yield tmpdir


@fixture
def scratch_dir(pghome_dir, service_name, in_example_dir):
    yield pghome_dir.join(Path().join('playground', service_name).relto(str('/')))


@fixture
def pghome_dir(tmpdir):
    yield tmpdir.join('.run', 'pgctl')


@fixture
def service_name():
    # this fixture will be overridden by some tests
    yield 'date'
