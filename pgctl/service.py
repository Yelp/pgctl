# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from subprocess import check_call

from cached_property import cached_property


class Service(object):

    def __init__(self, path, pgctl_app):
        self.path = path
        self._pgctl_app = pgctl_app

    def __repr__(self):
        return "Service('{path}')".format(path=self.path.strpath)

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

    @cached_property
    def scratch_dir(self):
        """Return the scratch path for a service.

        Scratch directories are located at
           {pghome}/{absolute path of service}/
        """
        return self._pgctl_app.pghome.join(self.path.relto(str('/')))
