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
import select
import time
from sys import argv

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


def wait_for_down_signal(down_fifo, seconds):
    """Waits at most "seconds" for down_fifo to have data on it, and returns
    True if the first byte from the FIFO is 'd'. Returns False if there is no
    data on the FIFO or the first byte is not a 'd'.

    :param seconds: time to wait for the fifo to have data on it. Zero specifies
    a poll and never blocks.
    :type seconds: float
    :rtype: bool
    :return: if a 'd' was available on the FIFO before the timeout expired.
    """
    rlist, _, _ = select.select([down_fifo], [], [], seconds)
    if rlist:
        fifo_data = os.read(down_fifo, 1)
        if fifo_data == b'd':
            return True

    return False


def pgctl_poll_ready(down_fifo, notification_fd, timeout, poll_ready, poll_down, check_ready=check_ready):

    is_service_down = wait_for_down_signal(down_fifo, 0)
    while True:  # waiting for the service to come up.
        if is_service_down:
            print_stderr('pgctl-poll-ready: service is stopping -- quitting the poll')
            return
        elif check_ready() == 0:
            print_stderr('pgctl-poll-ready: service\'s ready check succeeded')
            os.write(notification_fd, b'ready\n')
            break
        else:
            is_service_down = wait_for_down_signal(down_fifo, poll_ready)

    is_service_down = wait_for_down_signal(down_fifo, 0)
    start = time.time()
    while True:  # heartbeat, continue to check if the service is up. if it becomes down, terminate it.
        elapsed = time.time() - start
        if is_service_down:
            print_stderr('pgctl-poll-ready: service is stopping -- quitting the poll')
            return
        elif check_ready() == 0:
            start = time.time()
            is_service_down = wait_for_down_signal(down_fifo, poll_down)
        elif elapsed < timeout:
            print_stderr('pgctl-poll-ready: failed (restarting in {0:.2f} seconds)'.format(timeout - elapsed))
            is_service_down = wait_for_down_signal(down_fifo, poll_down)
        else:
            service = os.path.basename(os.getcwd())
            # TODO: Add support for directories
            print_stderr(
                'pgctl-poll-ready: failed for more than {0:.2f} seconds -- we are restarting this service for you'.format(timeout)
            )
            exec_(('pgctl', 'restart', service))  # doesn't return


def main():
    if os.environ.get('PGCTL_DEBUG'):
        print_stderr('pgctl-poll-ready: disabled during debug -- quitting')
        exec_(argv[1:])  # never returns

    # TODO-TEST: fail if notification-fd doesn't exist
    # TODO-TEST: echo 4 > notification-fd
    notification_fd = int(floatfile('notification-fd'))

    # Create a FIFO to listen for the s6 down event
    #
    # Set up the FIFO in the parent before forking because the process we exec
    # might die immediately (and the child wouldn't receive the "down" event).
    #
    # The name of the FIFO created in S6's FIFO dir must comply with certain
    # naming conventions. See the link below for more information.
    # https://github.com/skarnet/s6/blob/v2.2.2.0/src/libs6/ftrigw_notifyb_nosig.c#L29,L30
    down_fifo_path = os.path.join(
        'event', 'ftrig1' + 'poll_ready_{}'.format(os.getpid()).ljust(43, '_'),
    )

    # Don't reuse an old FIFO
    try:
        os.remove(down_fifo_path)
    except OSError:
        # If it doesn't exist that's fine
        pass

    # Even though the FIFO is effectively RO, it is opened as RW because
    # opening as RO blocks until the other side of the FIFO is opened.
    os.mkfifo(down_fifo_path)
    down_fifo = os.open(down_fifo_path, os.O_RDWR)

    if os.fork():  # parent
        os.close(down_fifo)  # we don't need this in the parent
        # run the wrapped command in the main process
        exec_(argv[1:])  # never returns
    else:  # child
        timeout = getval('timeout-ready', 'PGCTL_TIMEOUT', '2.0')
        poll_ready = getval('poll-ready', 'PGCTL_POLL', '0.15')
        poll_down = getval('poll-down', 'PGCTL_POLL', '10.0')

        try:
            pgctl_poll_ready(down_fifo, notification_fd, timeout, poll_ready, poll_down)
        finally:
            os.close(down_fifo)
            os.remove(down_fifo_path)


if __name__ == '__main__':
    exit(main())  # never returns
