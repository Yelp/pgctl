# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from collections import namedtuple
from subprocess import check_call
from subprocess import Popen

from cached_property import cached_property

from .flock import flock
from .flock import Locked


class Service(namedtuple('Service', ['path', 'scratch_dir'])):
    __slots__ = ()

    def __str__(self):
        return self.name

    def ensure_correct_directory_structure(self):
        """Ensure that the services' directory structure is correct."""
        self.ensure_scratch_dir_exists()
        self.path.ensure('down')

    def ensure_scratch_dir_exists(self):
        """Ensure that the scratch directory exists and symlinks supervise.

        Due to quirks in pip and potentially other package managers, we don't
        want named FIFOs on disk inside the project repo (they'll end up in
        tarballs and other junk).

        Instead, we stick them in a scratch directory outside of the repo.
        """
        supervise_in_scratch = self.scratch_dir.join('supervise')
        supervise_in_scratch.ensure_dir()

        # ensure symlink {service_dir}/supervise -> {scratch_dir}/supervise
        check_call((
            'ln', '-sf', '--',
            supervise_in_scratch.strpath,
            self.path.join('supervise').strpath,
        ))

    def supervise(self):
        """Run supervise(1), while ensuring it starts down and is properly symlinked."""
        self.ensure_correct_directory_structure()
        return Popen(
            ('supervise', self.path.strpath),
            stdout=self.path.join('stdout.log').open('w'),
            stderr=self.path.join('stderr.log').open('w'),
            env=self.supervise_env,
            close_fds=False,  # we must keep the flock file descriptor opened.
        )

    def idempotent_supervise(self):
        """Run supervise(1), but be successful if it's run too many times."""
        try:
            with flock(self.path.strpath):
                self.supervise()  # pragma: no branch
                # (see https://bitbucket.org/ned/coveragepy/issues/146)
        except Locked:
            # the fact that the directory is already locked indicates
            # that it's already supervised: success
            return

    @cached_property
    def name(self):
        return self.path.basename

    @cached_property
    def supervise_env(self):
        """Returns an environment dict to use for running supervise."""
        return dict(
            os.environ,
            PGCTL_SCRATCH=str(self.scratch_dir.strpath),
        )
