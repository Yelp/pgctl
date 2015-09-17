# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from collections import namedtuple
from subprocess import check_call
from subprocess import Popen
from time import time as now

from cached_property import cached_property

from .daemontools import svstat
from .debug import debug
from .errors import LockHeld
from .errors import NoSuchService
from .flock import flock
from .flock import Locked
from .functions import check_lock
from .functions import exec_


def idempotent_supervise(wrapped):
    """Run supervise(1), but be successful if it's run too many times."""

    def wrapper(self):
        race_limit = 10
        self.ensure_directory_structure()
        limit_time = now() + self.wait
        while True:
            try:
                with flock(self.path.strpath):
                    return wrapped(self)
            except Locked:
                # if it's already supervised, we're good to go:
                if Popen(('s6-svok', self.path.strpath)).wait() == 0:
                    return

                check_time = now()
                try:
                    check_lock(self.path.strpath)
                except LockHeld:
                    # lsof can take a long time. we timeout as close to the limit_time as we can.
                    curr_time = now()
                    next_time = curr_time + (curr_time - check_time)
                    if abs(curr_time - limit_time) < abs(next_time - limit_time):
                        raise  # timeout
                    else:
                        pass  # try again TODO: unit test: we dont hit this when lsof is super slow  pragma:no cover
                else:  # race condition: processes dropped lock before we could list them
                    if race_limit > 0:
                        race_limit -= 1
                    else:
                        raise

    return wrapper


class Service(namedtuple('Service', ['path', 'scratch_dir', 'default_wait'])):
    __slots__ = ()
    __defaults__ = (None,)

    def __str__(self):
        return self.name

    def svstat(self):
        self.assert_exists()
        with self.path.dirpath().as_cwd():
            return svstat(self.name)

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

    @idempotent_supervise
    def check_stopped(self):
        pass

    @cached_property
    def wait(self):
        wait = self.path.join('wait')
        if wait.check():
            debug('wait exists')
            return float(wait.read().strip())
        else:
            debug('wait doesn\'t exist')
            return float(self.default_wait)

    @cached_property
    def name(self):
        return self.path.basename

    @cached_property
    def supervise_env(self):
        """Returns an environment dict to use for running supervise."""
        return dict(os.environ, PGCTL_SCRATCH=str(self.scratch_dir.strpath))
