# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from collections import namedtuple
from subprocess import check_call

from cached_property import cached_property


class Service(namedtuple('Service', ['path', 'scratch_dir'])):

    def __repr__(self):
        return "Service(path='{path}', scratch_dir='{scratch_dir}')".format(
            path=self.path.strpath,
            scratch_dir=self.scratch_dir.strpath,
        )

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
