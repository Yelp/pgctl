# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os


def get_playground_file(parser, playground_dir):
    playground_file = os.path.join(playground_dir, 'playground.yaml')

    if not os.path.exists(playground_file):
        parser.error("%s does not exist" % playground_file)
    else:
        return playground_file


def start(playground_config_path):
    print('Starting:', playground_config_path)


def stop(playground_config_path):
    print('Stopping:', playground_config_path)


def status(playground_config_path):
    print('Status:', playground_config_path)


def restart(playground_config_path):
    stop(playground_config_path)
    start(playground_config_path)


def debug(playground_config_path):
    print('Starting Debug:', playground_config_path)


def _add_common(parser):
    parser.add_argument(
        '--playground-path',
        default='.',
        dest='playground_config_path',
        type=lambda x: get_playground_file(parser, x)
    )


def main(argv=None):
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest='command')

    add_parser = subparsers.add_parser('start')
    stop_parser = subparsers.add_parser('stop')
    status_parser = subparsers.add_parser('status')
    restart_parser = subparsers.add_parser('restart')
    debug_parser = subparsers.add_parser('debug')

    for p in [add_parser, stop_parser, status_parser, restart_parser, debug_parser]:
        _add_common(p)

    args = parser.parse_args(argv)

    if args.command == 'start':
        start(
            args.playground_config_path
        )
    elif args.command == 'stop':
        stop(
            args.playground_config_path
        )
    elif args.command == 'status':
        status(
            args.playground_config_path
        )
    elif args.command == 'restart':
        restart(
            args.playground_config_path
        )
    elif args.command == 'debug':
        debug(
            args.playground_config_path
        )
    else:
        raise NotImplementedError
