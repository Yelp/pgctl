#!/usr/bin/env python
"""
configuration: (decreasing scope, increasing priority)
  1) system level:  /etc/mything.conf
  2) user level:    ~/.config/mything.conf
  3) environment:   $MYTHING_X
  4) app level:     ..., $PWD/../.mything.conf, $PWD/.mything.conf
  5) cli:           --x
"""
import configparser
import json
import logging
from os import environ
from os.path import join

import yaml

from pgctl.configsearch import search_parent_directories

log = logging.getLogger(__name__)


class UnrecognizedConfig(ValueError):
    pass


class AmbiguousConfig(EnvironmentError):
    pass


class Dummy:
    def __init__(self):
        self.config = None


class Config:

    def __init__(self, projectname, defaults=None):
        self.projectname = projectname
        self.defaults = defaults

    def from_file(self, filename):
        # TODO P3: refactor this spaghetti
        # TODO(ckuehl|2019-08-08): why do we support .ini files??
        if filename.endswith(('.conf', '.ini')):
            parser = configparser.ConfigParser()
            parser.read(filename)
            result = dict(parser.items(self.projectname))
            for key, value in result.items():
                if key.endswith('_list'):
                    value = result.pop(key).split()
                    key = key.rsplit('_list', 1)[0]
                    result[key] = value
            return result
        elif filename.endswith(('.yaml', '.yml')):
            return yaml.load(
                open(filename),
                Loader=getattr(yaml, 'CSafeLoader', yaml.SafeLoader),
            )
        elif filename.endswith('.json'):
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
        if environ.get('PGCTL_NO_GLOBAL_CONFIG') == 'true':
            return {}
        etc = join(environ.get('PREFIX', '/'), 'etc', '')
        return self.from_path_prefix(etc)

    def from_homedir(self):
        if environ.get('PGCTL_NO_GLOBAL_CONFIG') == 'true':
            return {}
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

    def from_cli(self, args):
        configs = []
        if args.config is not None:
            configs.append(self.from_file(args.config))
        configs.append(vars(args))
        return merge(configs)

    def combined(self, defaults=(), args=Dummy()):
        return merge((
            defaults,
            self.from_system(),
            self.from_homedir(),
            self.from_app(),
            self.from_environ(),
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
    from collections.abc import Mapping
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
