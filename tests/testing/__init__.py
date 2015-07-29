# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import sys


def run(process, input=None):
    """like Popen.communicate, but still show the output"""
    stdout, stderr = process.communicate()
    print(stdout)
    print(stderr, file=sys.stderr)
    return stdout, stderr
