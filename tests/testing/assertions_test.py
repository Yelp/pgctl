# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import unicode_literals

from testfixtures import ShouldRaise

from .assertions import retry


class DescribeRetry(object):

    def it_can_succeed(self):
        assert retry(lambda: True) is True

    def it_can_fail(self):
        with ShouldRaise(AssertionError('assert (False is None or False)')):
            retry(lambda: False)

    def it_can_succeed_flakily(self):
        class notlocal(object):
            count = 0

        def assertion():
            notlocal.count += 1
            assert notlocal.count > 3
            return notlocal.count

        assert retry(assertion) == 4
