from __future__ import absolute_import
from __future__ import unicode_literals

import os
from contextlib import contextmanager


@contextmanager
def set_slow_shutdown_sleeptime(background, foreground):
    os.environ['BACKGROUND_SLEEP'] = 'infinity' if background == -1 else str(background)
    os.environ['FOREGROUND_SLEEP'] = 'infinity' if foreground == -1 else str(foreground)

    yield

    del os.environ['BACKGROUND_SLEEP']
    del os.environ['FOREGROUND_SLEEP']
