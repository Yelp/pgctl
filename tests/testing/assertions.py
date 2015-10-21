"""Helpers for test assertions."""
from __future__ import absolute_import
from __future__ import unicode_literals


def assert_svstat(service, **attrs):
    from testfixtures import Comparison as C
    from pgctl.daemontools import svstat, SvStat
    assert svstat(service) == C(SvStat, attrs, strict=False)


def wait_for(assertion, sleep=.05, limit=10.0):
    """Some flakey assertions need to be retried."""
    # TODO(Yelp/pgctl#28): take this out once we can 'check'
    import time
    start = time.time()
    while True:
        try:
            truth = assertion()
            assert truth is None or truth
            return truth
        except AssertionError:
            if time.time() - start > limit:
                raise
            else:
                time.sleep(sleep)
