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


def assert_command(cmd, stdout, stderr, returncode, **popen_args):
    # this allows py.test to hide this frame during test debugging
    __tracebackhide__ = True  # pylint:disable=unused-variable
    from subprocess import Popen, PIPE
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, **popen_args)
    actual_out, actual_err = run(p)
    # in order of most-informative error first.
    assert stderr == actual_err
    assert stdout == actual_out
    assert returncode == p.returncode
