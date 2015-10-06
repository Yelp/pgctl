"""
usage: s6-check-poll my-server --option ...

spawn a background process that writes to a file descriptor indicated
by ./notification-fd when a ./ready script runs successfully.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
import os.path
import sys

from .functions import exec_


def floatfile(filename):
    with open(filename) as f:
        return float(f.read())


def getval(filename, envname, default):
    try:
        return floatfile(filename)
    except IOError as err:
        if err.errno == 2:  # doesn't exist
            pass
        else:
            raise

    return float(os.environ.get(envname, default))


def check_ready():
    from subprocess import call
    return call('./ready')


def pgctl_poll_ready(downevent, notification_fd, timeout, poll_ready, poll_down, check_ready=check_ready):
    from time import sleep
    while True:
        if check_ready() == 0:
            print('pgctl-poll-ready: service\'s ready check succeeded', file=sys.stderr)
            os.write(notification_fd, 'ready\n')
            break

        if timeout <= 0:
            return 'pgctl-poll-ready: timeout while waiting for ready'
        else:
            sleep(poll_ready)
            timeout -= poll_ready

    # heartbeat, continue to check if the service is up. if it becomes down, terminate it.
    while True:
        if downevent.poll() is not None:
            print('pgctl-poll-ready: service is stopping -- quitting the poll', file=sys.stderr)
            break
        elif check_ready() == 0:
            sleep(poll_down)
        else:
            downevent.terminate()
            service = os.path.basename(os.getcwd())
            # TODO: Add support for directories
            print('pgctl-poll-ready: service\'s ready check failed -- we are restarting it for you', file=sys.stderr)
            # we chdir to avoid holding the service-is-up lock.
            os.chdir(os.path.join(os.environ.get('PGCTL_SERVICE', '.'), '..'))
            exec_(('pgctl-2015', 'restart', service))  # doesn't return


def main():
    # TODO-TEST: fail if notification-fd doesn't exist
    # TODO-TEST: echo 4 > notification-fd
    notification_fd = int(floatfile('notification-fd'))

    if os.fork():  # parent
        # run the wrapped command in the main process
        from sys import argv
        exec_(argv[1:])  # never returns
    else:  # child
        timeout = getval('timeout-ready', 'PGCTL_TIMEOUT', '2.0')
        poll_ready = getval('poll-ready', 'PGCTL_POLL', '0.15')
        poll_down = getval('poll-down', 'PGCTL_POLL', '10.0')
        # this subprocess listens for the s6 down event: http://skarnet.org/software/s6/s6-supervise.html
        from subprocess import Popen
        downevent = Popen(
            ('s6-ftrig-wait', 'event', 'd'),
            stdout=open(os.devnull, 'w'),  # this prints 'd' otherwise
        )
        return pgctl_poll_ready(downevent, notification_fd, timeout, poll_ready, poll_down)


if __name__ == '__main__':
    exit(main())  # never returns
