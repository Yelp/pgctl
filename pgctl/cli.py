# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
from time import time as now

import contextlib2
import six
from cached_property import cached_property
from frozendict import frozendict
from py._path.local import LocalPath as Path

from .config import Config
from .configsearch import search_parent_directories
from .debug import debug
from .debug import trace
from .errors import CircularAliases
from .errors import LockHeld
from .errors import NoPlayground
from .errors import PgctlUserMessage
from .errors import reraise
from .errors import Unsupervised
from .functions import bestrelpath
from .functions import commafy
from .functions import exec_
from .functions import JSONEncoder
from .functions import ps
from .functions import unique
from .fuser import fuser
from .service import Service
from pgctl import __version__


XDG_RUNTIME_DIR = os.environ.get('XDG_RUNTIME_DIR') or '~/.run'
ALL_SERVICES = '(all services)'
PGCTL_DEFAULTS = frozendict({
    # TODO-DOC: config
    # where do our services live?
    'pgdir': 'playground',
    # where does pgdir live?
    'pghome': os.path.join(XDG_RUNTIME_DIR, 'pgctl'),
    # which services are we acting on?
    'services': ('default',),
    # how long do we wait for them to come down/up?
    'timeout': '2.0',
    'poll': '.01',
    # what are the named groups of services?
    'aliases': frozendict({
        'default': (ALL_SERVICES,)
    }),
    # output as json?
    'json': False,
})
CHANNEL = '[pgctl]'


class TermStyle(object):

    BOLD = '\033[1m'
    ENDC = '\033[0m'

    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'

    @classmethod
    def wrap(cls, text, style):
        if sys.stdout.isatty():
            return '{}{}{}'.format(style, text, cls.ENDC)
        else:
            return text


class StateChange(object):

    def __init__(self, service):
        self.service = service
        self.name = service.name


class Start(StateChange):

    def change(self):
        return self.service.start()

    def assert_(self):
        return self.service.assert_ready()

    def get_timeout(self):
        return self.service.timeout_ready

    class strings(object):
        change = 'start'
        changing = 'Starting:'
        changed = 'Started:'


class Stop(StateChange):

    def change(self):
        return self.service.stop()

    def assert_(self):
        return self.service.assert_stopped()

    def get_timeout(self):
        return self.service.timeout_stop

    class strings(object):
        change = 'stop'
        changing = 'Stopping:'
        changed = 'Stopped:'


def unbuf_print(*args, **kwargs):
    """Print unbuffered in utf8."""
    kwargs.setdefault('file', sys.stdout)

    buff = getattr(kwargs['file'], 'buffer', kwargs['file'])
    buff.write(' '.join(args).encode('UTF-8') + b'\n')
    buff.flush()


def pgctl_print(*print_args, **print_kwargs):
    """Print to stderr with [pgctl] prepended."""
    print_kwargs.setdefault('file', sys.stderr)
    unbuf_print(CHANNEL, *print_args, **print_kwargs)


def timeout(service_name, error, action_name, start_time, timeout_length, check_time):
    curr_time = now()
    check_length = curr_time - check_time
    next_time = curr_time + check_length
    limit_time = start_time + timeout_length

    # assertion can take a long time. we timeout as close to the limit_time as we can.
    if abs(curr_time - limit_time) < abs(next_time - limit_time):
        actual_timeout_length = curr_time - start_time
        error_message = "ERROR: service '{}' failed to {} after {:.2f} seconds".format(
            service_name,
            action_name,
            actual_timeout_length,
        )
        if actual_timeout_length - timeout_length > 0.1:
            error_message += ' (it took {}s to poll)'.format(
                check_length,
            )  # TODO-TEST: pragma: no cover: we only hit this when lsof is being slow; add a unit test
        error_message += ', ' + str(error)
        pgctl_print(error_message)
        return True
    else:
        trace('service %s still waiting: %.1f seconds.', service_name, limit_time - curr_time)
        return False


class PgctlApp(object):

    def __init__(self, config=PGCTL_DEFAULTS):
        self.pgconf = frozendict(config)

    def __call__(self):
        """Run the app."""
        # config guarantees this is set
        command = self.pgconf['command']
        # argparse guarantees this is an attribute
        command = getattr(self, command)
        try:
            result = command()
        except PgctlUserMessage as error:
            # we don't need or want a stack trace for user errors
            result = str(error)

        if isinstance(result, six.string_types):
            return CHANNEL + ' ERROR: ' + result
        else:
            return result

    @contextlib.contextmanager
    def playground_locked(self):
        """Lock the entire playground."""
        def on_lock_held(path):
            reraise(LockHeld(
                'another pgctl command is currently managing this service: (%s)\n%s' %
                (bestrelpath(path), ps(fuser(path)))
            ))

        with contextlib2.ExitStack() as context:
            for service in self.services:
                service.ensure_exists()

                # This lock represents a pgctl cli interacting with the service.
                from .flock import flock
                lock = context.enter_context(flock(
                    service.path.join('.pgctl.lock').strpath,
                    on_fail=on_lock_held,
                ))
                from .flock import set_fd_inheritable
                set_fd_inheritable(lock, False)

            yield

    def __change_state(self, state):
        """Changes the state of a supervised service using the svc command"""
        with self.playground_locked():
            for service in self.services:
                try:
                    state(service).assert_()
                except PgctlUserMessage:
                    break
            else:
                # Short-circuit, everything is in the correct state.
                pgctl_print('Already {} {}'.format(
                    state.strings.changed.lower(),
                    commafy(self.service_names)),
                )
                return

        # If we're starting a service, run the playground-wide "pre-start" hook (if it exists).
        # This is intentionally done without holding a lock, since this might be very slow.
        if state is Start:
            self._run_playground_wide_hook('pre-start')

        run_post_stop_hook = False
        with self.playground_locked():
            failures = self.__locked_change_state(state)
            if state is Stop:
                run_post_stop_hook = all(
                    service.state['state'] == 'down'
                    for service in self.all_services
                )

        # If the playground is in a fully stopped state, run the playground wide
        # post-stop hook. As with pre-start, this is done without holding a lock.
        if run_post_stop_hook:
            self._run_playground_wide_hook('post-stop')

        return failures

    def __locked_change_state(self, state):
        """the critical section of __change_state"""
        pgctl_print(state.strings.changing, commafy(self.service_names))
        services = [state(service) for service in self.services]
        failed = []
        start_time = now()
        while services:
            for service in services:
                try:
                    service.change()
                except Unsupervised:
                    pass  # handled in state assertion, below
            for service in tuple(services):
                check_time = now()
                try:
                    service.assert_()
                except PgctlUserMessage as error:
                    if timeout(service.name, error, state.strings.change, start_time, service.get_timeout(), check_time):
                        services.remove(service)
                        failed.append(service.name)
                else:
                    # TODO: debug() takes a lambda
                    debug('loop: check_time %.3f', now() - check_time)
                    pgctl_print(state.strings.changed, service.name)
                    service.service.message(state)
                    services.remove(service)

            time.sleep(float(self.pgconf['poll']))

        return failed

    def _run_playground_wide_hook(self, hook_name):
        """Runs the given playground-wide hook, if it exists."""
        try:
            path = self.pgdir.join(hook_name)
            if path.exists():
                subprocess.check_call(
                    (path.strpath,),
                    cwd=self.pgdir.dirname,
                )
        except NoPlayground:
            # services can exist without a playground;
            # that's fine, but they can't have pre-start hooks
            pass

    def with_services(self, services):
        """return a similar PgctlApp, but with a different set of services"""
        newconf = dict(self.pgconf)
        newconf['services'] = services
        return PgctlApp(newconf)

    def __show_failure(self, state, failed):
        if not failed:
            return

        failapp = self.with_services(failed)
        childpid = os.fork()
        if childpid:
            os.waitpid(childpid, 0)
        else:
            os.dup2(2, 1)  # send log to stderr
            failapp.log(interactive=False)  # doesn't return
        if state == 'start':
            # we don't want services that failed to start to be 'up'
            failapp.stop()

        pgctl_print()
        pgctl_print('There might be useful information further up in the log; you can view it by running:')
        for service in failapp.services:
            pgctl_print('    less +G {}'.format(bestrelpath(service.path.join('log').strpath)))

        raise PgctlUserMessage('Some services failed to %s: %s' % (state, commafy(failed)))

    def start(self):
        """Idempotent start of a service or group of services"""
        failed = self.__change_state(Start)
        return self.__show_failure('start', failed)

    def stop(self):
        """Idempotent stop of a service or group of services"""
        failed = self.__change_state(Stop)
        return self.__show_failure('stop', failed)

    def status(self):
        """Retrieve the PID and state of a service or group of services"""
        status = {}
        for service in self.services:
            status[service.name] = service.state

        if self.pgconf['json']:
            print(json.dumps(
                status,
                sort_keys=True,
                indent=4,
            ))
        else:
            for service_name, state in sorted(status.items()):
                color = {
                    'ready': TermStyle.GREEN,
                    'up': TermStyle.YELLOW,
                    'down': TermStyle.RED,
                }[state['state']]

                unbuf_print(' {} {}: {}'.format(
                    TermStyle.wrap('●', color),
                    TermStyle.wrap(service_name, TermStyle.BOLD),
                    TermStyle.wrap(state['state'], TermStyle.BOLD + color),
                ))

                # state, pid/exit code
                components = []
                if state['pid'] is not None:
                    components.append('pid: {}'.format(state['pid']))
                if state['exitcode'] is not None:
                    components.append('exitcode: {}'.format(state['exitcode']))
                if state['seconds'] is not None:
                    components.append('{}'.format(_humanize_seconds(state['seconds'])))
                if state['process'] is not None:
                    components.append(state['process'])

                if components:
                    unbuf_print('   └─ {}'.format(', '.join(components)))

    def restart(self):
        """Starts and stops a service"""
        self.stop()
        self.start()

    def reload(self):
        """Reloads the configuration for a service"""
        pgctl_print('reload:', commafy(self.service_names))
        raise PgctlUserMessage('reloading is not yet implemented.')

    def log(self, interactive=None):
        """Displays the stdout and stderr for a service or group of services"""
        # TODO(p3): -n: send the value to tail -n
        # TODO(p3): -f: force iteractive behavior
        # TODO(p3): -F: force iteractive behavior off
        tail = ('tail', '-n', '30', '--verbose')  # show file headers

        if interactive is None:
            interactive = sys.stdout.isatty()
        if interactive:
            # we're interactive; give a continuous log
            # TODO-TEST: pgctl log | pb should be non-interactive
            tail += ('--follow=name', '--retry')

        logfiles = []
        for service in self.services:
            service.ensure_logs()
            logfile = service.path.join('log')
            logfile = bestrelpath(str(logfile))
            logfiles.append(logfile)
        exec_(tail + tuple(logfiles))  # never returns

    def debug(self):
        """Allow a service to run in the foreground"""
        try:
            # start supervise in the foreground with the service up
            service, = self.services  # pylint:disable=unpacking-non-sequence
        except ValueError:
            raise PgctlUserMessage(
                'Must debug exactly one service, not: ' + commafy(self.service_names),
            )

        self.stop()
        service.foreground()  # never returns

    def config(self):
        """Print the configuration for a service"""
        print(JSONEncoder(sort_keys=True, indent=4).encode(self.pgconf))

    def service_by_name(self, service_name):
        """Return an instantiated Service, by name."""
        if os.path.isabs(service_name):
            path = Path(service_name)
        else:
            path = self.pgdir.join(service_name, abs=1)
        return Service(
            path,
            self.pghome.join(path.relto(str('/')), abs=1),
            self.pgconf['timeout'],
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
        return unique(services)

    def _expand_aliases(self, name):
        aliases = self.pgconf['aliases']
        visited = set()
        stack = [name]
        result = []

        while stack:
            name = stack.pop()
            if name == ALL_SERVICES:
                result.extend([service.name for service in self.all_services])
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
    def all_services(self):
        """Return a list of all services.

        :return: list of Service objects
        :rtype: list
        """
        pgdir = self.pgdir.listdir(sort=True)

        return tuple(
            self.service_by_name(service_path.basename)
            for service_path in pgdir
            if service_path.check(dir=True)
        )

    @cached_property
    def service_names(self):
        return tuple([service.name for service in self.services])

    @cached_property
    def pgdir(self):
        """Retrieve the set playground directory"""
        for parent in search_parent_directories():
            pgdir = Path(parent).join(self.pgconf['pgdir'], abs=1)
            if pgdir.check(dir=True):
                return pgdir
        raise NoPlayground(
            "could not find any directory named '%s'" % self.pgconf['pgdir']
        )

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
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--pgdir', help='name the playground directory', default=argparse.SUPPRESS)
    parser.add_argument('--pghome', help='directory to keep user-level playground state', default=argparse.SUPPRESS)
    parser.add_argument(
        '--json', action='store_true', default=False,
        help='output in JSON (only supported by some commands)',
    )
    parser.add_argument('command', help='specify what action to take', choices=commands, default=argparse.SUPPRESS)

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--all', '-a',
        action='store_const', const=(ALL_SERVICES,),
        dest='services',
        help='act upon all services',
        default=argparse.SUPPRESS,
    )
    group.add_argument('services', nargs='*', help='specify which services to act upon', default=argparse.SUPPRESS)

    return parser


def _humanize_seconds(seconds):
    for period_name, period_length in (
            ('days', 24 * 60 * 60),
            ('hours', 60 * 60),
            ('minutes', 60),
    ):
        if seconds >= period_length:
            return '{:.1f} {}'.format(
                seconds / period_length,
                period_name,
            )
    else:
        return '{} seconds'.format(seconds)


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    config = Config('pgctl')
    config = config.combined(PGCTL_DEFAULTS, args)
    app = PgctlApp(config)

    return app()


if __name__ == '__main__':
    exit(main())
