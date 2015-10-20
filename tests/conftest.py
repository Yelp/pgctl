# -*- coding: utf-8 -*-
# pylint:disable=redefined-outer-name,unused-argument
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil

from py._path.local import LocalPath as Path
from pytest import yield_fixture as fixture

TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from pgctl.cli import PgctlApp


@fixture
def in_example_dir(tmpdir, homedir, service_name):
    os.environ['HOME'] = homedir.strpath
    os.environ.pop('XDG_RUNTIME_DIR', None)

    template_dir = os.path.join(TOP, 'tests/examples', service_name)
    tmpdir = tmpdir.join(service_name)
    shutil.copytree(template_dir, tmpdir.strpath)

    with tmpdir.as_cwd():
        try:
            yield tmpdir
        finally:
            #  pytest does a chdir before calling cleanup handlers
            with tmpdir.as_cwd():
                PgctlApp().stop()


@fixture
def scratch_dir(pghome_dir, service_name, in_example_dir):
    yield pghome_dir.join(Path().join('playground', service_name).relto(str('/')))


@fixture
def pghome_dir(homedir):
    yield homedir.join('.run', 'pgctl')


@fixture
def homedir(tmpdir):
    yield tmpdir.join('home')


@fixture
def service_name():
    # this fixture will be overridden by some tests
    yield 'sleep'


@fixture(autouse=True)
def wait4():
    """wait for all subprocesses to finish."""
    yield
    i = 0
    try:
        while i < 1000:
            os.wait3(os.WNOHANG)
            i += 1  # we only hit this when tests are broken. pragma: no cover
        raise AssertionError("there's a subprocess that's still running")
    except OSError as error:
        if error.errno == 10:  # no child processes
            return
        else:
            raise
    raise AssertionError('Should never get here.')
