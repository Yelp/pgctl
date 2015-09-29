# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from collections import namedtuple
from subprocess import check_call
from subprocess import Popen

from cached_property import cached_property

from .daemontools import svc
from .daemontools import SvStat
from .daemontools import svstat
from .debug import debug
from .errors import NoSuchService
from .errors import NotReady
from .flock import flock
from .flock import Locked
from .functions import check_lock
from .functions import exec_


def idempotent_supervise(wrapped):
    """Run supervise(1), but be successful if it's run too many times."""

    def wrapper(self):
        self.ensure_directory_structure()
        try:
            with flock(self.path.strpath):
                return wrapped(self)
        except Locked:
            # if it's already supervised, we're good to go:
            if Popen(('s6-svok', self.path.strpath)).wait() == 0:
                return
            else:
                check_lock(self.path.strpath)  # pragma: no cover, we don't expect to hit this case
                raise AssertionError('locked, but supervise is down, but no processes found, ten times?!')

    return wrapper


class Service(namedtuple('Service', ['path', 'scratch_dir', 'default_timeout'])):
    # TODO-TEST: regression: these cached-properties are actually cached
    __defaults__ = (None,)

    def __str__(self):
        return self.name

    def svstat(self):
        self.assert_exists()
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
        debug('PARSED: %s', result)
        return result

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
        self.assert_exists()
        svc(('-dx', self.path.strpath))

    def __get_timeout(self, name, default):
        timeout = self.path.join(name)
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
        check_lock(self.path.strpath)
        if self.svstat().state != SvStat.UNSUPERVISED:
            raise AssertionError('still supervised?!')

    def assert_ready(self):
        if self.svstat().state != 'ready':
            raise NotReady('not ready')

    def assert_exists(self):
        if not self.path.check(dir=True):
            raise NoSuchService("No such playground service: '%s'" % self.name)

    def ensure_directory_structure(self):
        """Ensure that the scratch directory exists and symlinks supervise.

        Due to quirks in pip and potentially other package managers, we don't
        want named FIFOs on disk inside the project repo (they'll end up in
        tarballs and other junk).

        Instead, we stick them in a scratch directory outside of the repo.
        """
        self.assert_exists()
        self.path.ensure('stdout.log')
        self.path.ensure('stderr.log')
        self.path.ensure('nosetsid')  # see http://skarnet.org/software/s6/servicedir.html
        if self.ready_script.exists() and not self.notification_fd.exists():
            f = self.notification_fd.open('w')
            f.write(str(f.fileno()) + '\n')
        supervise_in_scratch = self.scratch_dir.join('supervise')
        supervise_in_scratch.ensure_dir()

        # ensure symlink {service_dir}/supervise -> {scratch_dir}/supervise
        # TODO-TEST: a test that fails without -n
        check_call((
            'ln', '-sfn', '--',
            supervise_in_scratch.strpath,
            self.path.join('supervise').strpath,
        ))

    @idempotent_supervise
    def background(self):
        """Run supervise(1), while ensuring it is properly symlinked."""
        return Popen(
            ('s6-supervise', self.path.strpath),
            stdin=open(os.devnull, 'w'),
            stdout=self.path.join('stdout.log').open('w'),
            stderr=self.path.join('stderr.log').open('w'),
            env=self.supervise_env,
            close_fds=False,  # we must keep the flock file descriptor opened.
        )

    @idempotent_supervise
    def foreground(self):
        exec_(
            ('s6-supervise', self.path.strpath),
            env=self.supervise_env
        )

    @cached_property
    def name(self):
        return self.path.basename

    @cached_property
    def supervise_env(self):
        """Returns an environment dict to use for running supervise."""
        return dict(os.environ, PGCTL_SCRATCH=str(self.scratch_dir.strpath))
