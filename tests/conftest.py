# -*- coding: utf-8 -*-
# pylint:disable=redefined-outer-name,unused-argument
from __future__ import absolute_import
from __future__ import unicode_literals

import contextlib
import os
import shutil

import pytest
TOP = os.path.dirname(os.path.abspath(__file__))


@contextlib.contextmanager
def cwd(path):
    pwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(pwd)


@pytest.yield_fixture
def in_example_dir(tmpdir):
    template_dir = os.path.join(TOP, 'examples/sample_project')
    project_dir = tmpdir.join('sample_project')
    shutil.copytree(template_dir, project_dir.strpath)

    with cwd(project_dir.strpath):
        yield project_dir
