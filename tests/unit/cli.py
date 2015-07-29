# -*- coding: utf-8 -*-
# pylint:disable=redefined-outer-name,unused-argument
from __future__ import absolute_import
from __future__ import unicode_literals

from testfixtures import ShouldRaise

from pgctl.cli import main


def test_start(in_example_dir):
    assert main(['start']) == "No such playground service: 'default'"


def test_stop(in_example_dir):
    assert main(['stop']) is None


def test_status(in_example_dir):
    assert main(['status']) is None


def test_restart(in_example_dir):
    assert main(['restart']) is None


def test_reload(in_example_dir):
    assert main(['reload']) is None


def test_log(in_example_dir):
    assert main(['log']) is None


def test_debug(in_example_dir):
    assert main(['debug']) is None


def test_config(in_example_dir):
    assert main(['config']) is None


def test_nonsense(in_example_dir):
    with ShouldRaise(SystemExit(2)):
        main(['nonsense'])
