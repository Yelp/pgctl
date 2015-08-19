"""Helpers for test assertions."""
from __future__ import absolute_import
from __future__ import unicode_literals


def retry(assertion, repeat=10, sleep=.05):
    """Some flakey assertions need to be retried."""
    # TODO(Yelp/pgctl#28): take this out once we can 'check'
    import time
    i = 0
    while True:
        try:
            truth = assertion()
            assert truth is None or truth
            return truth
        except AssertionError:
            if i < repeat:
                i += 1
                time.sleep(sleep)
            else:
                raise
