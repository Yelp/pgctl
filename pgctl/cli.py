# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse

from .config import Config

PGCTL_DEFAULTS = {
    'pgdir': 'playground',
    'pgconf': 'conf.yaml',
    'services': ('default',),
}


class PgctlApp(object):

    def __init__(self, config):
        self._config = config

    def __call__(self):
        command = getattr(self, self._config['command'], None)
        if command is None:
            return "No such command: '%s'" % self.config['command']
        return command()

    def start(self):
        print('Starting:', self._config['services'])

    def stop(self):
        print('Stopping:', self._config['services'])

    def status(self):
        print('Status:', self._config['services'])

    def restart(self):
        self.stop()
        self.start()

    def reload(self):
        print('reload:', self._config['services'])

    def log(self):
        print('Log:', self._config['services'])

    def debug(self):
        print('Debugging:', self._config['services'])

    def config(self):
        print(self._config)

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

    print(config.from_app())

    config = config.combined(PGCTL_DEFAULTS, args)

    app = PgctlApp(config)

    return app()


if __name__ == '__main__':
    exit(main())
