# -*- coding: utf-8 -*-
# pylint:disable=redefined-outer-name,unused-argument
from __future__ import absolute_import
from __future__ import unicode_literals

from testfixtures import ShouldRaise

from pgctl.cli import main


def test_start(in_example_dir):
    main(['start'])


def test_stop(in_example_dir):
    main(['stop'])


def test_status(in_example_dir):
    main(['status'])


def test_restart(in_example_dir):
    main(['restart'])


def test_reload(in_example_dir):
    main(['reload'])


def test_log(in_example_dir):
    main(['log'])


def test_debug(in_example_dir):
    main(['debug'])


def test_config(in_example_dir):
    main(['config'])


def test_nonsense(in_example_dir):
    with ShouldRaise(SystemExit(2)):
        main(['nonsense'])
