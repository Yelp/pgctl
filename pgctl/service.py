# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from collections import namedtuple
from subprocess import check_call
from subprocess import Popen

from cached_property import cached_property

from .errors import LockHeld
from .errors import NoSuchService
from .flock import flock
from .flock import Locked
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
            if Popen(('svok', self.path.strpath)).wait() == 0:
                return
            else:
                raise LockHeld(self.path.strpath)
    return wrapper


class Service(namedtuple('Service', ['path', 'scratch_dir'])):
    __slots__ = ()

    def __str__(self):
        return self.name

    def ensure_directory_structure(self):
        """Ensure that the scratch directory exists and symlinks supervise.

        Due to quirks in pip and potentially other package managers, we don't
        want named FIFOs on disk inside the project repo (they'll end up in
        tarballs and other junk).

        Instead, we stick them in a scratch directory outside of the repo.
        """
        if not self.path.check(dir=True):
            raise NoSuchService("No such playground service: '%s'" % self.name)
        self.path.ensure('stdout.log')
        self.path.ensure('stderr.log')
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
        """Run supervise(1), while ensuring it starts down and is properly symlinked."""
        return Popen(
            ('supervise', self.path.strpath),
            stdout=self.path.join('stdout.log').open('w'),
            stderr=self.path.join('stderr.log').open('w'),
            env=self.supervise_env,
            close_fds=False,  # we must keep the flock file descriptor opened.
        )

    @idempotent_supervise
    def foreground(self):
        exec_(
            ('supervise', self.path.strpath),
            env=self.supervise_env
        )

    @idempotent_supervise
    def check_stopped(self):
        pass

    @cached_property
    def name(self):
        return self.path.basename

    @cached_property
    def supervise_env(self):
        """Returns an environment dict to use for running supervise."""
        return dict(os.environ, PGCTL_SCRATCH=str(self.scratch_dir.strpath))
