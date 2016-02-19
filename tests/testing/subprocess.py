from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import sys


def show_both(stdout, stderr):
    print(stdout, end='')
    print(stderr, file=sys.stderr, end='')


def run(cmd, **popen_args):
    """run the command, show the output, and return (stdout, stderr, returncode)"""
    from pgctl.subprocess import Popen, PIPE
    process = Popen(cmd, stdout=PIPE, stderr=PIPE, **popen_args)
    stdout, stderr = process.communicate()
    stdout, stderr = stdout.decode('UTF-8'), stderr.decode('UTF-8')
    show_both(stdout, stderr)
    return stdout, stderr, process.returncode


# TODO: move to pgctl.subprocess
def quote(cmd):
    from pipes import quote
    return ' '.join(quote(arg) for arg in cmd)


def _banner(message):
    message = ' %s ' % message
    message = message.center(73, '=')
    message = 'TEST: %s\n' % message
    show_both(message, message)


# TODO: move to testing.subprocess
def assert_command(cmd, stdout, stderr, returncode, norm=None, **popen_args):
    # this allows py.test to hide this frame during test debugging
    #__tracebackhide__ = True  # pylint:disable=unused-variable
    message = 'TEST: assert_command()\t%s\n' % quote(cmd)
    show_both(message, message)
    _banner('actual')
    actual_out, actual_err, returncode = run(cmd, **popen_args)
    if norm:
        actual_out = norm(actual_out)
        actual_err = norm(actual_err)
        _banner('normed')
        show_both(actual_out, actual_err)
    # in order of most-informative error first.
    assert stderr == actual_err
    assert stdout == actual_out
    assert returncode == returncode


def ctrl_c(process):
    from signal import SIGINT
    import os
    os.killpg(os.getpgid(process.pid), SIGINT)
