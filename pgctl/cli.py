# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os

from .config import Config

PGCTL_CONFIG = Config(
    projectname='pgctl',
    defaults={
        'pgdir': 'playground',
        'pgconf': 'conf.yaml',
        'services': ('default',),
    },
)


def get_playground_file(parser, playground_dir):
    playground_file = os.path.join(playground_dir, 'playground.yaml')

    if not os.path.exists(playground_file):
        parser.error('%s does not exist' % playground_file)
    else:
        return playground_file


class PgctlApp(object):
    def __init__(self, playground_config_path):
        self.playground_config_path = playground_config_path

    def start(self):
        print('Starting:', self)

    def stop(self):
        print('Stopping:', self)

    def status(self):
        print('Status:', self)

    def restart(self):
        self.stop()
        self.start()

    def debug(self):
        print('Debugging:', self)


def _add_common(parser):
    parser.add_argument(
        '--playground-path',
        default='.',
        dest='playground_config_path',
        type=lambda x: get_playground_file(parser, x)
    )


def parser():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest='command')

    add_parser = subparsers.add_parser('start')
    stop_parser = subparsers.add_parser('stop')
    status_parser = subparsers.add_parser('status')
    restart_parser = subparsers.add_parser('restart')
    debug_parser = subparsers.add_parser('debug')

    for p in [add_parser, stop_parser, status_parser, restart_parser, debug_parser]:
        _add_common(p)

    return parser


def main(argv=None):
    args = parser().parse_args(argv)
    config = PGCTL_CONFIG.combined()
    app = PgctlApp(config)

    if args.command == 'start':
        app.start()
    elif args.command == 'stop':
        app.stop()
    elif args.command == 'status':
        app.status()
    elif args.command == 'restart':
        app.restart()
    elif args.command == 'debug':
        app.debug()
    else:
        raise NotImplementedError


if __name__ == '__main__':
    exit(main())
