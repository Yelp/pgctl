import argparse
import contextlib
import enum
import json
import os
import subprocess
import sys
import time
import typing
from time import time as now

import contextlib2
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
from pgctl import telemetry
from pgctl.log_viewer import LogViewer


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
    # do not kill bad service processes?
    'no_force': False,
    # extra state change output?
    'verbose': False,
    # telemetry enabled?
    'telemetry': False,
    # path to clog config file (YAML format) for telemetry
    'telemetry_clog_config_path': None,
    # process tracing by environment variables enabled?
    'environment_process_tracing': True,
    # enable embedded log viewer during start/stop?
    'embedded_log_viewer': True,
})
CHANNEL = '[pgctl]'


class StateChangeOutcome(enum.Enum):
    SUCCESS = enum.auto()
    FAILURE = enum.auto()
    RECHECK_NEEDED = enum.auto()


class StateChangeResult(typing.NamedTuple):
    outcome: StateChangeOutcome
    output_message: typing.Optional[str]


class TermStyle:

    BOLD = '\033[1m'
    ENDC = '\033[0m'

    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'

    @classmethod
    def wrap(cls, text, style):
        if sys.stdout.isatty():
            return f'{style}{text}{cls.ENDC}'
        else:
            return text


class StateChange:

    def __init__(self, service):
        self.service = service
        self.name = service.name


class Start(StateChange):

    has_cleaned_up_processes: bool = False

    def change(self) -> typing.Optional[str]:
        # On the first change() call, clean up any lingering processes.
        # This is usually a no-op because we already verified that the service
        # is down according to s6, but this can catch processes which are still
        # running even though s6-supervise was killed.
        if not self.has_cleaned_up_processes:
            status_change_message = self.service.force_cleanup(is_stop=False)
            self.has_cleaned_up_processes = True
        else:
            status_change_message = None

        self.service.start()
        return status_change_message

    def assert_(self):
        return self.service.assert_ready()

    def get_timeout(self):
        return self.service.timeout_ready

    def fail(self):
        raise NotImplementedError

    is_user_facing = True

    class strings:
        change = 'start'
        changing = 'Starting:'
        changed = 'started'


class Stop(StateChange):

    def change(self) -> typing.Optional[str]:
        return self.service.stop()

    def assert_(self):
        return self.service.assert_stopped(with_log_running=True)

    def get_timeout(self):
        return self.service.timeout_stop

    def fail(self):
        return self.service.force_cleanup()

    is_user_facing = True

    class strings:
        change = 'stop'
        changing = 'Stopping:'
        changed = 'stopped'


class StopLogs(StateChange):
    def change(self) -> typing.Optional[str]:
        return self.service.stop_logs()

    def assert_(self):
        return self.service.assert_stopped(with_log_running=False)

    def fail(self):
        raise NotImplementedError

    def get_timeout(self):
        return self.service.timeout_stop

    is_user_facing = False

    class strings:
        change = 'stop'
        changing = 'Stopping logger for:'
        changed = 'stopped logger for'


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


def timeout(service, start_time, check_time, curr_time):
    limit_time = start_time + service.get_timeout()
    next_time = curr_time + (curr_time - check_time)

    # assertion can take a long time. we timeout as close to the limit_time as we can.
    if abs(curr_time - limit_time) < abs(next_time - limit_time):
        return True
    else:
        trace('service %s still waiting: %.1f seconds.', service.name, limit_time - curr_time)
        return False


def error_message_on_timeout(service, error, action_name, actual_timeout_length, check_length):
    error_message = "ERROR: service '{}' failed to {} after {:.2f} seconds".format(
        service.name,
        action_name,
        actual_timeout_length,
    )
    if actual_timeout_length - service.get_timeout() > 0.1:
        error_message += ' (it took {}s to poll)'.format(
            check_length,
        )  # TODO-TEST: pragma: no cover: we only hit this when lsof is being slow; add a unit test
    error_message += ', ' + str(error)
    return '[pgctl] ' + error_message


class PgctlApp:

    def __init__(self, config=PGCTL_DEFAULTS):
        self.pgconf = frozendict(config)

    def __call__(self):
        """Run the app."""
        # config guarantees this is set
        command = self.pgconf['command']
        # argparse guarantees this is an attribute
        command = getattr(self, command)

        start = time.time()
        telemetry.emit_event('command_run', {'command': self.pgconf['command'], 'config': dict(self.pgconf)})

        try:
            result = command()
        except PgctlUserMessage as error:
            # we don't need or want a stack trace for user errors
            result = str(error)

        if isinstance(result, str):
            telemetry.emit_event(
                'command_errored',
                {
                    'command': self.pgconf['command'],
                    'config': dict(self.pgconf),
                    'result': result,
                    'elapsed_s': time.time() - start,
                }
            )
            return CHANNEL + ' ERROR: ' + result
        else:
            telemetry.emit_event(
                'command_succeeded',
                {
                    'command': self.pgconf['command'],
                    'config': dict(self.pgconf),
                    'result': result,
                    'elapsed_s': time.time() - start,
                }
            )
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

    @property
    def log_viewer_enabled(self):
        return (
            self.pgconf.get('force_enable_log_viewer') == '1' or
            (self.pgconf['embedded_log_viewer'] and sys.stdin.isatty() and not os.environ.get('CI'))
        )

    def __change_state(self, state, services):
        """Changes the state of a supervised service using the svc command"""
        with self.playground_locked():
            for service in services:
                try:
                    state(service).assert_()
                except PgctlUserMessage:
                    break
            else:
                # Short-circuit, everything is in the correct state.
                if self._should_display_state(state):
                    pgctl_print('Already {}: {}'.format(
                        state.strings.changed,
                        commafy(_services_to_names(services))),
                    )
                return []

        # If we're starting a service, run the playground-wide "pre-start" hook (if it exists).
        # This is intentionally done without holding a lock, since this might be very slow.
        if state is Start:
            self._run_playground_wide_hook('pre-start')

        run_post_stop_hook = False
        with self.playground_locked():
            failures = self.__locked_change_state(state, services)
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

    def __locked_change_state(self, state, services):
        """the critical section of __change_state"""
        log_viewer = None
        if self._should_display_state(state):
            pgctl_print(
                state.strings.changing,
                commafy(_services_to_names(services)),
            )
            if self.log_viewer_enabled:
                log_viewer = LogViewer(20, {service.name: service.logfile_path for service in services})

        try:
            services = [state(service) for service in services]
            failed = []
            start_time = now()
            while services:
                for service in services:
                    try:
                        message = service.change()
                    except Unsupervised:
                        pass  # handled in state assertion, below
                    else:
                        if message:
                            pgctl_print(message)

                changes_to_print = []

                services_to_change = tuple(services)
                for service in services_to_change:
                    state_change_result = self.__locked_handle_service_change_state(
                        state,
                        service,
                        start_time,
                    )

                    if state_change_result.outcome is StateChangeOutcome.RECHECK_NEEDED:
                        # This service should be rechecked by the next iteration
                        # of the outer loop
                        pass
                    elif state_change_result.outcome is StateChangeOutcome.SUCCESS:
                        services.remove(service)
                        if log_viewer is not None:
                            log_viewer.stop_tailing(service.name)
                        if self._should_display_state(state):
                            changes_to_print.append(f'[pgctl] {state.strings.changed.capitalize()}: {service.name}')
                            state_change_message = (service.service.message(state) or '').strip()
                            if state_change_message:
                                changes_to_print.append(state_change_message)
                    else:
                        # StateChangeOutcome.FAILURE
                        failed.append(service.name)
                        services.remove(service)
                        if log_viewer is not None:
                            log_viewer.stop_tailing(service.name)

                    if state_change_result.output_message:
                        changes_to_print.append(state_change_result.output_message)

                if log_viewer is not None:
                    if len(changes_to_print) > 0 or log_viewer.redraw_needed():
                        # It's a bit awkward to build up strings like this but printing just a single
                        # time greatly improves the user experience by reducing flashing when the
                        # screen is cleared.
                        to_print = log_viewer.move_cursor_to_top()
                        to_print += log_viewer.clear_below()

                        for change in changes_to_print:
                            to_print += change + '\n'

                        if services:
                            to_print += log_viewer.draw_logs(
                                'Still {} {}'.format(
                                    state.strings.changing.lower(),
                                    ', '.join(sorted(service.name for service in services)),
                                ),
                            )

                        print(to_print, flush=True, end='', file=sys.stderr)

                    if not services:
                        pgctl_print(f'All services have {state.strings.changed}')
                else:
                    for change in changes_to_print:
                        unbuf_print(change, file=sys.stderr)

                time.sleep(float(self.pgconf['poll']))
        finally:
            if log_viewer is not None:
                log_viewer.cleanup()

        return failed

    def __locked_handle_service_change_state(
        self,
        state,
        service,
        start_time,
    ):
        """Handles a state change for a service and returns whether
        the state change was successful,
        """
        check_time = now()
        try:
            service.assert_()
        except PgctlUserMessage as error:
            state_change_result = self.__locked_handle_state_change_exception(
                state,
                service,
                error,
                start_time,
                check_time,
            )
            return state_change_result
        else:
            # TODO: debug() takes a lambda
            debug('loop: check_time %.3f', now() - check_time)
            return StateChangeResult(StateChangeOutcome.SUCCESS, None)

    def __locked_handle_state_change_exception(
        self,
        state,
        service,
        error,
        start_time,
        check_time,
    ) -> StateChangeResult:
        """Handles a state change timeout for a service and returns whether
        the service unrecoverably failed its state change.
        """
        curr_time = now()
        if timeout(service, start_time, check_time, curr_time):
            if not self.pgconf['no_force']:
                try:
                    message = service.fail()
                    if message:
                        message = f'[pgctl] {message}'
                    return StateChangeResult(StateChangeOutcome.RECHECK_NEEDED, message)
                except NotImplementedError:
                    pass

            return StateChangeResult(
                StateChangeOutcome.FAILURE,
                error_message_on_timeout(
                    service,
                    error,
                    state.strings.change,
                    actual_timeout_length=curr_time - start_time,
                    check_length=curr_time - check_time,
                ),
            )

        return StateChangeResult(StateChangeOutcome.RECHECK_NEEDED, None)

    def _should_display_state(self, state):
        return state.is_user_facing or self.pgconf['verbose']

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
        subprocess.call(failapp._log_command(), stdout=sys.stderr)
        if state == 'start':
            # we don't want services that failed to start to be 'up'
            failapp.stop()

        pgctl_print()
        pgctl_print('There might be useful information further up in the log; you can view it by running:')
        for service in failapp.services:
            pgctl_print('    less +G {}'.format(bestrelpath(service.path.join('logs', 'current').strpath)))

        raise PgctlUserMessage(f'Some services failed to {state}: {commafy(failed)}')

    def start(self):
        """Idempotent start of a service or group of services"""
        failed = self.__change_state(Start, self.services)
        return self.__show_failure('start', failed)

    def stop(self, with_log_running=False):
        """Idempotent stop of a service or group of services

        :param with_log_running: controls whether the logger associated with
        this service should be stopped or left running. For restart cases, we
        want to leave the logger running (since poll-ready may still be writing
        log messages).
        """
        failed = self.__change_state(Stop, self.services)

        if not with_log_running:
            failed_set = set(failed)
            services_to_stop_logs_on = [
                service for service in self.services
                if service.name not in failed_set
            ]
            failed.extend(
                self.__change_state(StopLogs, services_to_stop_logs_on),
            )

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
        self.stop(with_log_running=True)
        self.start()

    def reload(self):
        """Reloads the configuration for a service"""
        pgctl_print('reload:', commafy(self.service_names))
        raise PgctlUserMessage('reloading is not yet implemented.')

    def _log_command(self, interactive: bool = False) -> typing.Tuple[str]:
        # TODO(p3): -n: send the value to tail -n
        # TODO(p3): -f: force iteractive behavior
        # TODO(p3): -F: force iteractive behavior off
        tail = ('tail', '-n', '30', '--verbose')  # show file headers

        if interactive:
            # we're interactive; give a continuous log
            # TODO-TEST: pgctl log | pb should be non-interactive
            tail += ('--follow=name', '--retry')

        logfiles = []
        for service in self.services:
            service.ensure_logs()
            logfile = service.path.join('logs', 'current')
            logfile = bestrelpath(str(logfile))
            logfiles.append(logfile)

        return tail + tuple(logfiles)

    def log(self, interactive=None):
        """Displays the stdout and stderr for a service or group of services"""
        if interactive is None:
            interactive = sys.stdout.isatty()
        exec_(self._log_command(interactive))  # never returns

    def debug(self):
        """Allow a service to run in the foreground"""
        try:
            # start supervise in the foreground with the service up
            service, = self.services
        except ValueError:
            raise PgctlUserMessage(
                'Must debug exactly one service, not: ' + commafy(self.service_names),
            )

        if service.state['state'] != 'down':
            self.stop()

        self._run_playground_wide_hook('pre-start')
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
            path=path,
            scratch_dir=self.pghome.join(path.relto('/'), abs=1),
            default_timeout=self.pgconf['timeout'],
            environment_tracing_enabled=self.pgconf['environment_process_tracing'],
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
        return _services_to_names(self.services)

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
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=False,
        help='show additional service action information',
    )
    parser.add_argument('--pgdir', help='name the playground directory', default=argparse.SUPPRESS)
    parser.add_argument('--pghome', help='directory to keep user-level playground state', default=argparse.SUPPRESS)
    parser.add_argument(
        '--json', action='store_true', default=False,
        help='output in JSON (only supported by some commands)',
    )
    # This argument is no longer used but is kept as a hidden argument to avoid
    # breaking consumers which call pgctl with it.
    parser.add_argument(
        '--force', action='store_true', dest='_unused_force', help=argparse.SUPPRESS,
    )
    parser.add_argument(
        '--no-force', action='store_true', default=False,
        help='do not force bad services to stop',
    )
    parser.add_argument(
        '--config',
        help='specify a config file path to load',
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


def _services_to_names(services):
    return tuple(service.name for service in services)


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
        return f'{seconds} seconds'


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    config = Config('pgctl')
    config = config.combined(PGCTL_DEFAULTS, args)

    if config['telemetry']:
        telemetry.setup_clog(config['telemetry_clog_config_path'])

    app = PgctlApp(config)

    return app()


if __name__ == '__main__':
    exit(main())
