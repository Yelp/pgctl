# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os
import time
from collections import namedtuple
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
    'pghome': os.path.join(os.environ.get('XDG_RUNTIME_DIR') or os.path.expanduser('~/.run'), 'pgctl'),
    'services': ('default',),
})


class NoSuchService(Exception):
    pass


def svc(args):
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


class SvStat(
        namedtuple('SvStat', ['name', 'state', 'pid', 'seconds', 'process'])
):
    UNSUPERVISED = 'could not get status, supervisor is down'
    INVALID = 'no such service'

    def __repr__(self):
        format = '{0.name}: {0.state}'
        if self.pid is not None:
            format += ' (pid {0.pid})'
        if self.seconds is not None:
            format += ' {0.seconds} seconds'
        if self.process is not None:
            format += ', {0.process}'

        return format.format(self)


def svstat_string(args):
    """Wrapper for daemon tools svstat cmd"""
    # svstat *always* exits with code zero...
    cmd = ('svstat',) + tuple(args)
    process = Popen(cmd, stdout=PIPE)
    status, _ = process.communicate()

    #status is listed per line for each argument
    return status


def svstat_parse(svstat_string):
    r'''
    >>> svstat_parse('date: up (pid 1202562) 100 seconds\n')
    date: up (pid 1202562) 100 seconds

    >>> svstat_parse('date: down 4334 seconds, normally up, want up')
    date: down 4334 seconds, starting

    >>> svstat_parse('playground/date: down 0 seconds, normally up')
    playground/date: down 0 seconds

    >>> svstat_parse('date: up (pid 1202) 1 seconds, want down\n')
    date: up (pid 1202) 1 seconds, stopping

    >>> svstat_parse('playground/date: down 0 seconds, normally up')
    playground/date: down 0 seconds

    >>> svstat_parse('playground/date: down 0 seconds, normally up')
    playground/date: down 0 seconds

    >>> svstat_parse('docs: unable to open supervise/ok: file does not exist')
    docs: could not get status, supervisor is down

    >>> svstat_parse("date: supervise not running\n")
    date: could not get status, supervisor is down

    >>> svstat_parse('d: unable to chdir: file does not exist')
    d: no such service

    >>> svstat_parse('d: totally unpredictable error message')
    d: totally unpredictable error message
    '''
    status = svstat_string.strip()
    name, status = status.split(': ', 1)

    first, rest = status.split(None, 1)
    if first in ('up', 'down'):
        state, status = first, rest
    elif status.startswith('unable to chdir:'):
        state, status = SvStat.INVALID, rest
    elif status.startswith((
            'unable to open supervise/ok:',
            'supervise not running',
    )):
        state, status = SvStat.UNSUPERVISED, rest
    else:  # unknown errors
        state, status = status, ''

    if status.startswith('(pid '):
        pid, status = status[4:].rsplit(') ', 1)
        pid = int(pid)
    else:
        pid = None

    try:
        seconds, status = status.split(' seconds', 1)
        seconds = int(seconds)
    except ValueError:
        seconds = None

    if status.endswith(', want up'):
        process = 'starting'
    elif status.endswith(', want down'):
        process = 'stopping'
    else:
        process = None

    return SvStat(name, state, pid, seconds, process)


def svstat(*services):
    return [
        svstat_parse(line)
        for line in svstat_string(services).splitlines()
    ]


def exec_(argv, env=os.environ):  # pragma: no cover, pylint:disable=dangerous-default-value
    """Wrapper to os.execv which runs any atexit handlers (for coverage's sake).
    Like os.execv, this function never returns.
    """
    # in python3, sys.exitfunc has gone away, and atexit._run_exitfuncs seems to be the only pubic-ish interface
    #   https://hg.python.org/cpython/file/3.4/Modules/atexitmodule.c#l289
    import atexit
    atexit._run_exitfuncs()  # pylint:disable=protected-access

    from os import execvpe
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
        print(xing, self.services, file=sys.stderr)
        self.idempotent_supervise()
        with self.pgdir.as_cwd():
            try:
                while True:  # a poor man's do/while
                    svc((opt,) + self.services)
                    status_list = svstat(*self.services)
                    if all(
                            status.process is None and status.state == expected_state
                            for status in status_list
                    ):
                        break
                    else:
                        time.sleep(.01)
                print(xed, self.services, file=sys.stderr)
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
            for status in svstat(*self.services):
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
                ', '.join(self.services),
            )

        self.unsupervise()

        # start supervise in the foreground with the service up
        service = self.pgdir.join(self.services[0])
        service.join('down').remove()
        exec_(('supervise', service.strpath), env=self.supervise_env(service))  # pragma:no cover

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
        return tuple(sorted(
            service.basename
            for service in self.pgdir.listdir()
            if service.check(dir=True)
        ))

    @cached_property
    def aliases(self):
        """A dictionary of aliases that can be expanded to services"""
        ## for now don't worry about config file
        return frozendict({
            'default': self.all_services
        })

    def ensure_scratch_dir_exists(self, service_path):
        """Ensure that the scratch directory exists and symlinks supervise.

        Due to quirks in pip and potentially other package managers, we don't
        want named FIFOs on disk inside the project repo (they'll end up in
        tarballs and other junk).

        Instead, we stick them in a scratch directory outside of the repo.
        """
        home_path = self.scratch_dir(service_path)

        # ensure symlink {service_dir}/supervise -> {scratch_dir}/supervise
        supervise_in_scratch = home_path.join('supervise')
        supervise_in_scratch.ensure_dir()

        supervise_in_repo = service_path.join('supervise')
        if supervise_in_repo.exists():
            if supervise_in_repo.islink():
                # The user probably moved the repo, relinking is pretty safe.
                if supervise_in_repo.readlink() != supervise_in_scratch.strpath:
                    supervise_in_repo.remove()
            else:
                raise ValueError('{} exists and is not a symlink, please remove it!'.format(
                    supervise_in_repo.strpath,
                ))

        if not supervise_in_repo.exists():
            service_path.join('supervise').mksymlinkto(supervise_in_scratch)

    def idempotent_supervise(self):
        """
        ensure all services are supervised starting in a down state
        by contract, running this method repeatedly should have no negative consequences
        """
        for service in self.all_services:
            service = self.pgdir.join(service)
            self.ensure_scratch_dir_exists(service)

            service.ensure('down')
            # supervise is already essentially idempotent
            # it dies with code 111 and a single line printed to stderr
            Popen(
                ('supervise', service.strpath),
                stdout=service.join('stdout.log').open('w'),
                stderr=service.join('stderr.log').open('w'),
                env=self.supervise_env(service),
            )  # pragma: no branch
            # (see https://bitbucket.org/ned/coveragepy/issues/146)

    def supervise_env(self, service_path):
        """Returns an environment dict to use for running supervise."""
        return dict(
            os.environ,
            PGCTL_SCRATCH=self.scratch_dir(service_path).realpath().strpath,
        )

    def scratch_dir(self, service_path):
        """Return the scratch path for a service.

        Scratch directories are located at
           {pghome}/{absolute path of service}/
        """
        return self.pghome.join(
            # chop the leading `/` off of the absolute path
            service_path.realpath().strpath[1:],
        )

    @cached_property
    def pgdir(self):
        """Retrieve the set playground directory"""
        return Path(self._config['pgdir'])

    @cached_property
    def pghome(self):
        """Retrieve the set pgctl home directory.

        By default, this is "$XDG_RUNTIME_DIR/pgctl".
        """
        return Path(self._config['pghome'])

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
