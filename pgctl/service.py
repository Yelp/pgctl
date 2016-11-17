# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from collections import namedtuple
from contextlib import contextmanager

from cached_property import cached_property
from frozendict import frozendict

from .daemontools import prepend_timestamps_to
from .daemontools import svc
from .daemontools import SvStat
from .daemontools import svstat
from .debug import debug
from .debug import trace
from .errors import Impossible
from .errors import NoSuchService
from .errors import NotReady
from .errors import reraise
from .functions import bestrelpath
from .functions import exec_
from .functions import show_runaway_processes
from .functions import symlink_if_necessary
from .subprocess import check_call
from .subprocess import Popen


def flock(path):
    """attempt to show the user a better message on failure, and handle the race condition"""
    def handle_race(path):
        show_runaway_processes(path)
        if handle_race.limit > 0:
            handle_race.limit -= 1
        else:
            reraise(Impossible('lock is held, but not by any process, ten times'))
    handle_race.limit = 10

    from .flock import flock
    return flock(path, on_fail=handle_race)


class Service(namedtuple('Service', ['path', 'scratch_dir', 'default_timeout'])):
    # TODO-TEST: regression: these cached-properties are actually cached
    __exists = False

    def __str__(self):
        return self.name

    def supervised(self):
        # TODO-TEST: bring service up, clean symlink, run Service.supervised()
        self.ensure_exists()
        from .daemontools import svok
        return svok(self.path.strpath)

    def svstat(self):
        self.ensure_exists()
        with self.path.dirpath().as_cwd():
            result = svstat(self.name)
        if not self.notification_fd.exists():
            # services without notification need to be considered ready sometimes
            if (
                    # an 'up' service is always ready
                    (result.state == 'up' and result.process is None) or
                    # restarting continuously and successfully can/should be considered 'ready'
                    (result.process == 'starting' and result.exitcode == 0 and result.seconds == 0)
            ):
                result = result._replace(state='ready')
        trace('PARSED: %s', result)
        return result

    @property
    def state(self):
        svstat = self.svstat()
        state = {
            key: getattr(svstat, key)
            for key in svstat._fields
        }
        if state['state'] == SvStat.UNSUPERVISED:
            # this is the expected state for down services.
            state['state'] = 'down'
        return state

    def message(self, state):
        script = self.path.join(state.strings.change + '-msg')
        if script.exists():
            check_call((script.strpath,))

    @cached_property
    def ready_script(self):
        return self.path.join('ready')

    @cached_property
    def notification_fd(self):
        return self.path.join('notification-fd')

    def start(self):
        """Idempotent start of a service or group of services"""
        self.background()
        svc(('-u', self.path.strpath))

    def stop(self):
        """Idempotent stop of a service or group of services"""
        self.ensure_exists()
        svc(('-dx', self.path.strpath))

    def __get_timeout(self, name, default):
        timeout = self.path.join(name, abs=1)
        if timeout.check():
            debug('%s exists', name)
            return float(timeout.read().strip())
        else:
            debug('%s doesn\'t exist', name)
            return float(default)

    @cached_property
    def timeout_stop(self):
        return self.__get_timeout('timeout-stop', self.default_timeout)

    @cached_property
    def timeout_ready(self):
        return self.__get_timeout('timeout-ready', self.default_timeout)

    def assert_stopped(self):
        status = self.svstat()
        if status.state != SvStat.UNSUPERVISED:
            raise NotReady('its status is ' + str(status))

        with self.flock():
            return  # assertion success; nothing is running

    def assert_ready(self):
        status = self.svstat()
        if status.state != 'ready':
            raise NotReady('its status is ' + str(status))

    def ensure_exists(self):
        if self.__exists:
            return

        if not self.path.check(dir=True):
            raise NoSuchService("No such service: '%s'" % bestrelpath(str(self.path)))

        # ensure symlink {service_dir}/supervise -> {scratch_dir}/supervise
        # this will re-connect the service to its state descriptors if the symlinks have been deleted or moved
        supervise_in_scratch = self.scratch_dir.join('supervise')
        supervise_in_scratch.ensure_dir()
        symlink_if_necessary(supervise_in_scratch, self.path.join('supervise'))
        self.__exists = True

    def ensure_logs(self):
        self.ensure_exists()
        self.path.ensure('log')

    def ensure_directory_structure(self):
        """Ensure that the scratch directory exists and symlinks supervise.

        Due to quirks in pip and potentially other package managers, we don't
        want named FIFOs on disk inside the project repo (they'll end up in
        tarballs and other junk).

        Instead, we stick them in a scratch directory outside of the repo.
        """
        # TODO: enforce that we have the supervise lock when this is called, somehow
        self.ensure_exists()
        self.ensure_logs()
        self.path.ensure('nosetsid')  # see http://skarnet.org/software/s6/servicedir.html
        from py._error import error as pylib_error
        try:
            self.path.join('down').remove()  # pgctl doesn't support the s6 down file
        except pylib_error.ENOENT:
            pass

        if self.ready_script.exists():
            with self.notification_fd.open('w') as f:
                f.write('%i\n' % f.fileno())

    @contextmanager
    def flock(self):
        # if we already have the lock, from a parent process, use it.
        parent_service = os.environ.pop('PGCTL_SERVICE', None)
        lock = os.environ.pop('PGCTL_SERVICE_LOCK', None)
        debug('parentlock: %r', parent_service)
        if lock:
            lock = int(lock)
            if parent_service == self.path:
                debug('retrieved parent lock! %i', lock)
                try:
                    yield lock
                finally:
                    os.close(lock)
                return
            else:
                from .flock import release
                release(lock)

        with flock(self.path.strpath) as lock:
            debug('LOCK: %i', lock)
            self.ensure_directory_structure()
            with self.path.as_cwd():
                yield lock

    def background(self):
        """Run supervise(1), while ensuring it is properly symlinked."""
        if self.supervised():
            return

        with self.flock() as lock:
            log = self.path.join('log').open('a')
            log = prepend_timestamps_to(log)
            Popen(
                ('s6-supervise', self.path.strpath),
                stdin=open(os.devnull, 'w'),
                stdout=log.fileno(),
                stderr=log.fileno(),
                env=self.supervise_env(lock, debug=False),
                close_fds=False,  # we must keep the flock file descriptor opened.
            )
            log.close()

    def foreground(self):
        with self.flock() as lock:
            exec_(
                (str(self.path.join('run')),),
                env=self.supervise_env(lock, debug=True),
            )  # never returns

    @cached_property
    def name(self):
        return self.path.basename

    def supervise_env(self, lock, debug):
        """Returns an environment dict to use for running supervise."""
        env = dict(
            os.environ,
            PGCTL_SCRATCH=str(self.scratch_dir),
            # TODO-TEST: assert this env var is available and correct
            PGCTL_SERVICE=str(self.path),
            PGCTL_SERVICE_LOCK=str(lock),
        )
        if debug:
            env['PGCTL_DEBUG'] = 'true'
        else:
            env.pop('PGCTL_DEBUG', None)
        return frozendict(env)
