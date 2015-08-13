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
    # svc never writes to stdout.
    cmd = ('svc',) + tuple(args)
    p = Popen(cmd, stderr=PIPE)
    _, error = p.communicate()
    if 'unable to chdir' in error:
        raise NoSuchService(error)
    if p.returncode:  # pragma: no cover: there's no known way to hit this.
        import sys
        sys.stderr.write(error)
        raise CalledProcessError(p.returncode, cmd)


def svstat(*args):
    # svstat *always* exits with code zero...
    cmd = ('svstat',) + tuple(args)
    p = Popen(cmd, stdout=PIPE)
    status, _ = p.communicate()

    #status is listed per line for each argument
    return [
        get_state(status_line) for status_line in status.splitlines()
    ]


def get_state(status):
    r"""
    Parse a single line of svstat output.

    >>> get_state("date: up (pid 1202562) 1 seconds\n")
    'up'

    >>> get_state("date: down 0 seconds, normally up, want up\n")
    'starting'

    >>> get_state("playground/date: down 0 seconds, normally up\n")
    'down'

    >>> get_state("date: up (pid 1202562) 1 seconds, want down\n")
    'stopping'

    >>> get_state("date: supervise not running\n")
    'unsupervised'

    >>> get_state('playground/greeter: unable to open supervise/ok: file does not exist')
    'unsupervised'
    """
    status = status.rstrip()
    if status.endswith(' want up'):
        state = 'starting'
    elif status.endswith(' want down'):
        state = 'stopping'
    elif (
            status.endswith(': supervise not running') or
            'unable to open supervise/ok' in status
    ):
        state = 'unsupervised'
    else:
        _, status = status.split(':', 1)
        state, _ = status.split(None, 1)
    return str(state)


def exec_(argv):  # pragma: no cover
    """Wrapper to os.execv which runs any atexit handlers (for coverage's sake).
    Like os.execv, this function never returns.
    """
    # in python3, sys.exitfunc has gone away, and atexit._run_exitfuncs seems to be the only pubic-ish interface
    #   https://hg.python.org/cpython/file/3.4/Modules/atexitmodule.c#l289
    import atexit
    atexit._run_exitfuncs()  # pylint:disable=protected-access

    from os import execvp
    execvp(argv[0], argv)  # never returns


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
        import sys
        print(xing, self.services, file=sys.stderr)
        self.idempotent_supervise()
        with self.pgdir.as_cwd():
            # TODO-TEST: it can {start,stop} multiple services at once
            try:
                while True:  # a poor man's do/while
                    svc(opt, *self.services)
                    if all(state == expected_state for state in svstat(*self.services)):
                        break
                    else:
                        time.sleep(.01)
                print(xed, self.services, file=sys.stderr)
            except NoSuchService:
                return "No such playground service: '%s'" % self.services

    def start(self):
        return self.__change_state('-u', 'up', 'Starting:', 'Started:')

    def stop(self):
        return self.__change_state('-d', 'down', 'Stopping:', 'Stopped:')

    def unsupervise(self):
        return self.__change_state(
            '-dx',
            'unsupervised',
            'Stopping supervise:',
            'Stopped supervise:',
        )

    def status(self):
        print('Status:', self.services)

    def restart(self):
        self.stop()
        self.start()

    def reload(self):
        print('reload:', self._config['services'])

    def log(self):
        print('Log:', self._config['services'])

    def debug(self):
        if len(self.services) != 1:
            return 'Must debug exactly one service, not: {0}'.format(
                ', '.join(self.services),
            )

        self.unsupervise()

        # start supervise in the foreground with the service up
        service = self.pgdir.join(self.services[0])
        service.join('down').remove()
        exec_(('supervise', service.strpath))  # pragma:no cover

    def config(self):
        import json
        print(json.dumps(self._config, sort_keys=True, indent=4))

    @cached_property
    def services(self):
        return sum(
            tuple([
                self.aliases.get(service, (service,))
                for service in self._config['services']
            ]),
            (),
        )

    @cached_property
    def all_services(self):
        return tuple([
            service.basename
            for service in self.pgdir.listdir()
            if service.check(dir=True)
        ])

    @cached_property
    def aliases(self):
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
