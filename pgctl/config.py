#!/usr/bin/env python
"""
configuration: (decreasing scope, increasing priority)
  1) system level:  /etc/mything.conf
  2) user level:    ~/.config/mything.conf
  3) environment:   $MYTHING_X
  4) app level:     ..., $PWD/../.mything.conf, $PWD/.mything.conf
  5) cli:           --x
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import json
import logging
from os import environ
from os.path import join

try:
    from yaml import load as yaml_load
except ImportError:  # pragma: no cover
    def yaml_load(dummy_file):
        pass

from pgctl.configsearch import search_parent_directories

log = logging.getLogger(__name__)


class UnrecognizedConfig(ValueError):
    pass


class AmbiguousConfig(EnvironmentError):
    pass


class Dummy(object):
    pass


class Config(object):

    def __init__(self, projectname, defaults=None):
        self.projectname = projectname
        self.defaults = defaults

    def from_file(self, filename):
        # TODO P3: refactor this spaghetti
        if filename.endswith(('.conf', '.ini')):
            from ConfigParser import SafeConfigParser
            parser = SafeConfigParser()
            parser.read(filename)
            result = dict(parser.items(self.projectname))
            for key, value in result.items():
                if key.endswith('_list'):
                    value = result.pop(key).split()
                    key = key.rsplit('_list', 1)[0]
                    result[key] = value
            return result
        elif filename.endswith(('.yaml', '.yml')):
            return yaml_load(open(filename))
        elif filename.endswith(('.json')):
            return json.load(open(filename))
        else:
            raise UnrecognizedConfig('Unknown config type: %s' % filename)

    def from_glob(self, pattern):
        from pgctl.configsearch import glob
        results = []
        for fname in glob(pattern):
            try:
                config = self.from_file(fname)
            except UnrecognizedConfig:
                continue
            else:
                results.append(config)

        if len(results) == 1:
            return results[0]
        elif len(results) > 1:
            raise AmbiguousConfig('multiple configurations found at %s' % pattern)

    def from_path_prefix(self, pattern_prefix):
        pattern = ''.join((pattern_prefix, self.projectname, '.*'))
        return self.from_glob(pattern)

    def from_system(self):
        etc = join(environ.get('PREFIX', '/'), 'etc', '')
        return self.from_path_prefix(etc)

    def from_homedir(self):
        home = environ.get('HOME', '$HOME')
        return self.from_path_prefix(home + '/.')

    def from_environ(self, env=None):
        if env is None:
            env = environ

        var_prefix = self.projectname.upper() + '_'
        config = {}
        for varname, value in env.items():
            if varname.startswith(var_prefix):
                varname = varname.replace(var_prefix, '', 1).lower()
                if varname.endswith('_list'):
                    varname = varname.rsplit('_list', 1)[0]
                    value = value.split()
                config[varname] = value
        return config

    def from_app(self, path='.'):
        pattern = self.projectname + '.*'
        return merge(
            self.from_glob(join(parentdir, pattern))
            for parentdir in reversed(tuple(search_parent_directories(path)))
        )

    @staticmethod
    def from_cli(args):
        return vars(args)

    def combined(self, defaults=(), args=Dummy()):
        return merge((
            defaults,
            self.from_system(),
            self.from_homedir(),
            self.from_environ(),
            self.from_app(),
            self.from_cli(args),
        ))


def merge(values):
    from collections import deque
    result = {}
    q = deque()
    for value in values:
        q.append((result, value))
    while q:
        q.extend(_merge(*q.popleft()))
    return result


def _merge(old, new):
    """assume both are mappings, and the old is our mutable result"""
    from collections import Mapping
    if new is None:
        return
    for key in new:
        if isinstance(new[key], Mapping):
            if isinstance(old.get(key), Mapping):
                yield (old[key], new[key])
            else:
                old[key] = dict(new[key])
        else:
            old[key] = new[key]


def main():
    from sys import argv
    for project in argv[1:]:
        print(json.dumps(
            Config(project).combined(),
            sort_keys=True,
            indent=4,
        ))


if __name__ == '__main__':
    exit(main())
