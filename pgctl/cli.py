# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import time
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import Popen

from cached_property import cached_property
from frozendict import frozendict
from py._path.local import LocalPath as Path

from .config import Config

PGCTL_DEFAULTS = frozendict({
    'pgdir': 'playground',
    'pgconf': 'conf.yaml',
    'services': ('default',),
})


class NoSuchService(Exception):
    pass


def svc(*args):
    """Wrapper for daemontools svc cmd"""
    # svc never writes to stdout.
    cmd = ('svc',) + tuple(args)
    process = Popen(cmd, stderr=PIPE)
    _, error = process.communicate()
    if 'unable to chdir' in error:
        raise NoSuchService(error)
    if process.returncode:  # pragma: no cover: there's no known way to hit this.
        import sys
        sys.stderr.write(error)
        raise CalledProcessError(process.returncode, cmd)


def svstat(*args):
    """Wrapper for daemon tools svstat cmd"""
    # svstat *always* exits with code zero...
    cmd = ('svstat',) + tuple(args)
    process = Popen(cmd, stdout=PIPE)
    status, _ = process.communicate()

    #status is listed per line for each argument
    return [
        get_state(status_line) for status_line in status.splitlines()
    ]


def get_state(status):
    r"""
    Parse a single line of svstat output.

    >>> get_state("date: up (pid 1202562) 1 seconds\n")
    'up'

    >>> get_state("date: down 0 seconds, normally up, want up")
    'starting'

    >>> get_state("playground/date: down 0 seconds, normally up")
    'down'

    >>> get_state("date: up (pid 1202562) 1 seconds, want down\n")
    'stopping'
    """
    status = status.rstrip()
    if status.endswith(' want up'):
        state = 'starting'
    elif status.endswith(' want down'):
        state = 'stopping'
    else:
        _, status = status.split(':', 1)
        state, _ = status.split(None, 1)
    return str(state)


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
        print(xing, self.services)
        self.idempotent_supervise()
        with self.pgdir.as_cwd():
            try:
                while True:  # a poor man's do/while
                    svc(opt, *self.services)
                    if all(state == expected_state for state in svstat(*self.services)):
                        break
                    else:
                        time.sleep(.01)
                print(xed, self.services)
            except NoSuchService:
                return "No such playground service: '%s'" % self.services

    def start(self):
        """Idempotent start of a service or group of services"""
        return self.__change_state('-u', 'up', 'Starting:', 'Started:')

    def stop(self):
        """Idempotent stop of a service or group of services"""
        return self.__change_state('-d', 'down', 'Stopping:', 'Stopped:')

    def status(self):
        """Retrieve the PID and state of a service or group of services"""
        print('Status:', self.services)

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
        print('Debugging:', self._config['services'])

    def config(self):
        """Print the configuration for a service"""
        import json
        print(json.dumps(self._config, sort_keys=True, indent=4))

    @cached_property
    def services(self):
        """Return a tuple of the services for a command"""
        return sum(
            tuple([
                self.aliases.get(service, (service,))
                for service in self._config['services']
            ]),
            (),
        )

    @cached_property
    def all_services(self):
        """Return a tuple of all of the services"""
        return tuple([
            service.basename
            for service in self.pgdir.listdir()
            if service.check(dir=True)
        ])

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
            service = self.pgdir.join(service)
            service.ensure('down')
            # supervise is already essentially idempotent
            # it dies with code 111 and a single line printed to stderr
            Popen(
                ('supervise', service.strpath),
                stdout=service.join('stdout.log').open('w'),
                stderr=service.join('stderr.log').open('w'),
            )  # pragma: no branch
            # (see https://bitbucket.org/ned/coveragepy/issues/146)

    @cached_property
    def pgdir(self):
        """Retrieve the set playground directory"""
        return Path(self._config['pgdir'])

    commands = (start, stop, status, restart, reload, log, debug, config)


def parser():
    commands = [command.__name__ for command in PgctlApp.commands]
    parser = argparse.ArgumentParser()
    parser.add_argument('--pgdir', help='name the playground directory', default=argparse.SUPPRESS)
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
