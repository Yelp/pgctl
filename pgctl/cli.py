# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os
import time
from subprocess import MAXFD
from subprocess import Popen

from cached_property import cached_property
from frozendict import frozendict
from py._path.local import LocalPath as Path

from .config import Config
from pgctl.daemontools import NoSuchService
from pgctl.daemontools import svc
from pgctl.daemontools import SvStat
from pgctl.daemontools import svstat
from pgctl.service import Service


XDG_RUNTIME_DIR = os.environ.get('XDG_RUNTIME_DIR') or '~/.run'
PGCTL_DEFAULTS = frozendict({
    'pgdir': 'playground',
    'pgconf': 'conf.yaml',
    'pghome': os.path.join(XDG_RUNTIME_DIR, 'pgctl'),
    'services': ('default',),
})


def exec_(argv, env=None):  # pragma: no cover
    """Wrapper to os.execv which runs any atexit handlers (for coverage's sake).
    Like os.execv, this function never returns.
    """
    if env is None:
        env = os.environ

    # in python3, sys.exitfunc has gone away, and atexit._run_exitfuncs seems to be the only pubic-ish interface
    #   https://hg.python.org/cpython/file/3.4/Modules/atexitmodule.c#l289
    import atexit
    atexit._run_exitfuncs()  # pylint:disable=protected-access

    from os import execvpe, closerange
    closerange(3, MAXFD)
    execvpe(argv[0], argv, env)  # never returns


class PgctlApp(object):

    def __init__(self, config=PGCTL_DEFAULTS):
        self._config = config

    def __call__(self):
        # config guarantees this is set
        command = self._config['command']
        # argparse guarantees this is an attribute
        command = getattr(self, command)
        return command()

    def __change_state(self, opt, expected_state, xing, xed):
        """Changes the state of a supervised service using the svc command"""
        import sys
        print(xing, self.services_string, file=sys.stderr)
        self.idempotent_supervise()
        with self.pgdir.as_cwd():
            try:
                while True:  # a poor man's do/while
                    svc((opt,) + tuple(self.service_names))
                    status_list = svstat(*self.service_names)
                    if all(
                            status.process is None and status.state == expected_state
                            for status in status_list
                    ):
                        break
                    else:
                        time.sleep(.01)
                print(xed, self.services_string, file=sys.stderr)
            except NoSuchService:
                return "No such playground service: '%s'" % self.services

    def start(self):
        """Idempotent start of a service or group of services"""
        return self.__change_state('-u', 'up', 'Starting:', 'Started:')

    def stop(self):
        """Idempotent stop of a service or group of services"""
        return self.__change_state('-d', 'down', 'Stopping:', 'Stopped:')

    def unsupervise(self):
        return self.__change_state(
            '-dx',
            SvStat.UNSUPERVISED,
            'Stopping supervise:',
            'Stopped supervise:',
        )

    def status(self):
        """Retrieve the PID and state of a service or group of services"""
        with self.pgdir.as_cwd():
            for status in svstat(*self.service_names):
                print(status)

    def restart(self):
        """Starts and stops a service"""
        self.stop()
        self.start()

    def reload(self):
        """Reloads the configuration for a service"""
        print('reload:', self._config['services'])

    def log(self):
        """Displays the stdout and stderr for a service or group of services"""
        print('Log:', self._config['services'])

    def debug(self):
        """Allow a service to run in the foreground"""
        if len(self.services) != 1:
            return 'Must debug exactly one service, not: {0}'.format(
                self.services_string,
            )

        self.unsupervise()

        # start supervise in the foreground with the service up
        service = self.services[0]
        service.path.join('down').remove()
        exec_(('supervise', service.path.strpath), env=service.supervise_env)  # pragma: no cover

    def config(self):
        """Print the configuration for a service"""
        import json
        print(json.dumps(self._config, sort_keys=True, indent=4))

    def service_by_name(self, service_name):
        """Return an instantiated Service, by name."""
        path = self.pgdir.join(service_name)
        return Service(
            path=path,
            scratch_dir=self.pghome.join(path.relto(str('/'))),
        )

    @cached_property
    def services(self):
        """Return a tuple of the services for a command

        :return: tuple of Service objects
        """
        return sum(
            tuple([
                self.aliases.get(service_name, (self.service_by_name(service_name),))
                for service_name in self._config['services']
            ]),
            (),
        )

    @cached_property
    def all_services(self):
        """Return a tuple of all of the Services.

        :return: tuple of Service objects
        """
        return tuple(sorted(
            self.service_by_name(service_path.basename)
            for service_path in self.pgdir.listdir()
            if service_path.check(dir=True)
        ))

    @cached_property
    def aliases(self):
        """A dictionary of aliases that can be expanded to services"""
        ## for now don't worry about config file
        return frozendict({
            'default': self.all_services
        })

    def idempotent_supervise(self):
        """
        ensure all services are supervised starting in a down state
        by contract, running this method repeatedly should have no negative consequences
        """
        for service in self.all_services:
            service.ensure_correct_directory_structure()

            # supervise is already essentially idempotent
            # it dies with code 111 and a single line printed to stderr
            Popen(
                ('supervise', service.path.strpath),
                stdout=service.path.join('stdout.log').open('w'),
                stderr=service.path.join('stderr.log').open('w'),
                env=service.supervise_env,
                close_fds=True,
            )  # pragma: no branch
            # (see https://bitbucket.org/ned/coveragepy/issues/146)

    @cached_property
    def services_string(self):
        return ', '.join(self.service_names)

    @cached_property
    def service_names(self):
        return [service.name for service in self.services]

    @cached_property
    def pgdir(self):
        """Retrieve the set playground directory"""
        return Path(self._config['pgdir'])

    @cached_property
    def pghome(self):
        """Retrieve the set pgctl home directory.

        By default, this is "$XDG_RUNTIME_DIR/pgctl".
        """
        return Path(self._config['pghome'], expanduser=True)

    commands = (start, stop, status, restart, reload, log, debug, config)


def parser():
    commands = [command.__name__ for command in PgctlApp.commands]
    parser = argparse.ArgumentParser()
    parser.add_argument('--pgdir', help='name the playground directory', default=argparse.SUPPRESS)
    parser.add_argument('--pghome', help='directory to keep user-level playground state', default=argparse.SUPPRESS)
    parser.add_argument('--pgconf', help='name the playground config file', default=argparse.SUPPRESS)
    parser.add_argument('command', help='specify what action to take', choices=commands, default=argparse.SUPPRESS)
    parser.add_argument('services', nargs='*', help='specify which services to act upon', default=argparse.SUPPRESS)

    return parser


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    config = Config('pgctl')
    config = config.combined(PGCTL_DEFAULTS, args)
    app = PgctlApp(config)

    return app()


if __name__ == '__main__':
    exit(main())
