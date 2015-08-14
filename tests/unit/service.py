# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from py._path.local import LocalPath as Path

from pgctl.service import Service


def test_str_and_repr():
    service = Service(Path('/tmp/magic-service'), Path('/tmp/magic-service-scratch'))
    assert str(service) == 'magic-service'
