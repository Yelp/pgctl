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

from .functions import exec_
from .functions import print_stderr


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
    from .subprocess import call
    return call('./ready')


def pgctl_poll_ready(down_event, notification_fd, timeout, poll_ready, poll_down, check_ready=check_ready):
    from time import sleep
    while True:  # waiting for the service to come up.
        if down_event.poll() is not None:
            print_stderr('pgctl-poll-ready: service is stopping -- quitting the poll')
            return
        elif check_ready() == 0:
            print_stderr('pgctl-poll-ready: service\'s ready check succeeded')
            os.write(notification_fd, b'ready\n')
            break
        else:
            sleep(poll_ready)

    if os.environ.get('PGCTL_DEBUG', ''):
        print_stderr('pgctl-poll-ready: heartbeat is disabled during debug -- quitting')
        return

    timeout_unready = timeout
    while True:  # heartbeat, continue to check if the service is up. if it becomes down, terminate it.
        if down_event.poll() is not None:
            print_stderr('pgctl-poll-ready: service is stopping -- quitting the poll')
            return
        elif check_ready() == 0:
            timeout_unready = timeout
            sleep(poll_down)
        elif timeout_unready > 0:
            print_stderr('pgctl-poll-ready: failed (restarting in {0:.2f} seconds)'.format(timeout_unready))
            sleep(poll_down)
            timeout_unready -= poll_down
        else:
            down_event.terminate()
            service = os.path.basename(os.getcwd())
            # TODO: Add support for directories
            print_stderr(
                'pgctl-poll-ready: failed for more than {0:.2f} seconds -- we are restarting this service for you'.format(timeout)
            )
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
        from .subprocess import Popen
        down_event = Popen(
            ('s6-ftrig-wait', 'event', 'd'),
            stdout=open(os.devnull, 'w'),  # this prints 'd' otherwise
        )

        return pgctl_poll_ready(down_event, notification_fd, timeout, poll_ready, poll_down)


if __name__ == '__main__':
    exit(main())  # never returns
