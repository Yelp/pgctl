# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os
import time
from subprocess import MAXFD
from sys import stderr

from cached_property import cached_property
from frozendict import frozendict
from py._path.local import LocalPath as Path

from .config import Config
from .configsearch import search_parent_directories
from .daemontools import NoSuchService
from .daemontools import svc
from .daemontools import SvStat
from .daemontools import svstat
from .flock import Locked
from .functions import exec_
from .functions import JSONEncoder
from .functions import uniq
from .service import Service


XDG_RUNTIME_DIR = os.environ.get('XDG_RUNTIME_DIR') or '~/.run'
ALL_SERVICES = '(all services)'
PGCTL_DEFAULTS = frozendict({
    'pgdir': 'playground',
    'pghome': os.path.join(XDG_RUNTIME_DIR, 'pgctl'),
    'services': ('default',),
    'aliases': frozendict({
        'default': (ALL_SERVICES,)
    }),
})


class PgctlUserError(Exception):
    pass


class CircularAliases(PgctlUserError):
    pass


class NoPlayground(PgctlUserError):
    pass


class PgctlApp(object):

    def __init__(self, config=PGCTL_DEFAULTS):
        self.pgconf = frozendict(config)

    def idempotent_supervise(self):
        """
        ensure all services are supervised starting in a down state
        by contract, running this method repeatedly should have no negative consequences
        """
        for service in self.all_service_names:
            self.service_by_name(service).idempotent_supervise()

    def app_invariants(self):
        """The are the things we want to be able to say "always" about."""
        # ensure no weird file descriptors are open.
        os.closerange(3, MAXFD)
        self.idempotent_supervise()

    def __call__(self):
        """Run the app."""
        self.app_invariants()
        # config guarantees this is set
        command = self.pgconf['command']
        # argparse guarantees this is an attribute
        command = getattr(self, command)
        try:
            return command()
        except PgctlUserError as error:
            # we don't need or want a stack trace for user errors
            return str(error)

    def is_locked(self, service):
        try:
            self.service_by_name(service).check_lock()
        except Locked:
            time.sleep(.1)
            return True

    def __change_state(self, opt, expected_state, xing, xed):
        """Changes the state of a supervised service using the svc command"""
        print(xing, self.service_names_string, file=stderr)
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
                if opt == '-d':
                    svc(('-dx',) + tuple(self.service_names))
                    for service in self.service_names:
                        while self.is_locked(service):
                            print('.', end='')
                            import sys
                            sys.stdout.flush()
                        print('')
                print(xed, self.service_names_string, file=stderr)
            except NoSuchService:
                return "No such playground service: '%s'" % self.service_names_string

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

    def has_status(self):
        """Wait until the process is supervised to show status."""
        for status in svstat(*self.service_names):
            if SvStat.UNSUPERVISED in status:
                return False  # pragma: no cover expect to hit this minimally
        return True

    def status(self):
        """Retrieve the PID and state of a service or group of services"""
        with self.pgdir.as_cwd():
            while not self.has_status():
                pass  # pragma: no cover expect to hit this minimally
            for status in svstat(*self.service_names):
                print(status)

    def restart(self):
        """Starts and stops a service"""
        self.stop()
        self.app_invariants()
        self.start()

    def reload(self):
        """Reloads the configuration for a service"""
        print('reload:', self.service_names_string, file=stderr)
        return 'reloading is not yet implemented.'

    def log(self):
        """Displays the stdout and stderr for a service or group of services"""
        # TODO(p3): -n: send the value to tail -n
        # TODO(p3): -f: force iteractive behavior
        # TODO(p3): -F: force iteractive behavior off
        cmd = ('tail', '--verbose')  # show file headers
        import sys
        if sys.stdout.isatty():
            # we're interactive; give a continuous log
            # TODO-TEST: pgctl log | pb should be non-interactive
            cmd += ('--follow=name', '--retry')

        logfiles = [
            (
                service.path.join('stdout.log').relto(self.pgdir),
                service.path.join('stderr.log').relto(self.pgdir),
            )
            for service in self.services
        ]
        with self.pgdir.as_cwd():
            exec_(sum(logfiles, cmd))  # pragma: no cover

    def debug(self):
        """Allow a service to run in the foreground"""
        if len(self.services) != 1:
            return 'Must debug exactly one service, not: {0}'.format(
                self.service_names_string,
            )

        self.unsupervise()

        # start supervise in the foreground with the service up
        service = self.services[0]
        service.path.join('down').remove()
        exec_(('supervise', service.path.strpath), env=service.supervise_env)  # pragma: no cover

    def config(self):
        """Print the configuration for a service"""
        print(JSONEncoder(sort_keys=True, indent=4).encode(self.pgconf))

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
        services = [
            self.service_by_name(service_name)
            for alias in self.pgconf['services']
            for service_name in self._expand_aliases(alias)
        ]
        return uniq(services)

    def _expand_aliases(self, name):
        aliases = self.pgconf['aliases']
        visited = set()
        stack = [name]
        result = []

        while stack:
            name = stack.pop()
            if name == ALL_SERVICES:
                result.extend(self.all_service_names)
            elif name in visited:
                raise CircularAliases("Circular aliases! Visited twice during alias expansion: '%s'" % name)
            else:
                visited.add(name)
                if name in aliases:
                    stack.extend(reversed(aliases[name]))
                else:
                    result.append(name)

        return result

    @cached_property
    def all_service_names(self):
        """Return a tuple of all of the Services.

        :return: tuple of strings -- the service names
        """
        try:
            pgdir = self.pgdir.listdir(sort=True)
        except NoPlayground:
            # there's no pgdir
            pgdir = []

        return tuple([
            service_path.basename
            for service_path in pgdir
            if service_path.check(dir=True)
        ])

    @cached_property
    def service_names_string(self):
        return ', '.join(self.service_names)

    @cached_property
    def service_names(self):
        return tuple([service.name for service in self.services])

    @cached_property
    def pgdir(self):
        """Retrieve the set playground directory"""
        for parent in search_parent_directories():
            pgdir = Path(parent).join(self.pgconf['pgdir'])
            if pgdir.check(dir=True):
                return pgdir
        raise NoPlayground("Could not find a pgdir for: '{0}' in {1}".format(self.pgconf['pgdir'], os.getcwd()))

    @cached_property
    def pghome(self):
        """Retrieve the set pgctl home directory.

        By default, this is "$XDG_RUNTIME_DIR/pgctl".
        """
        return Path(self.pgconf['pghome'], expanduser=True)

    commands = (start, stop, status, restart, reload, log, debug, config)


def parser():
    commands = [command.__name__ for command in PgctlApp.commands]
    parser = argparse.ArgumentParser()
    parser.add_argument('--pgdir', help='name the playground directory', default=argparse.SUPPRESS)
    parser.add_argument('--pghome', help='directory to keep user-level playground state', default=argparse.SUPPRESS)
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
