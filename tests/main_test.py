# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import contextlib
import os
import shutil

import pytest

from yelp_playground.main import get_playground_file
from yelp_playground.main import main


@contextlib.contextmanager
def cwd(path):
    pwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(pwd)


@pytest.yield_fixture
def in_sample_service_dir(tmpdir):
    project_dir = tmpdir.join('sample_project')
    shutil.copytree('testing/resources/sample_project', project_dir.strpath)

    with cwd(project_dir.strpath):
        yield project_dir


def test_get_playground_file(tmpdir, in_sample_service_dir):
    parser = argparse.ArgumentParser()

    assert get_playground_file(parser, in_sample_service_dir.strpath) == \
        in_sample_service_dir.join('playground.yaml').strpath

    # tmpdir shouldn't contain a playground.yaml file and crash
    with pytest.raises(SystemExit):
        get_playground_file(parser, tmpdir.strpath)


def test_start(in_sample_service_dir):
    main(['start'])


def test_stop(in_sample_service_dir):
    main(['stop'])


def test_status(in_sample_service_dir):
    main(['status'])


def test_restart(in_sample_service_dir):
    main(['restart'])


def test_debug(in_sample_service_dir):
    main(['debug'])
