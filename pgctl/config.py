#!/usr/bin/env python
"""
configuration: (decreasing scope, increasing priority)
  1) system level:  /etc/mything.conf
  2) user level:    ~/.config/mything.conf
  3) environment:   $MYTHING_X
  4? super-app:     $PWD/../.mything.conf (?)
  4) app level:     $PWD/.mything.conf
  5) cli:           --x
"""


def _listify_services(config):
    if 'services' in config:
        config = config.copy()
        config['services'] = config['services'].split()
    return config


def parse_config(filename):
    if filename.endswith(('.conf', '.ini')):
        from ConfigParser import SafeConfigParser
        parser = SafeConfigParser()
        parser.read(filename)
        config = dict(parser.items('pgctl'))
        return _listify_services(config)
    elif filename.endswith(('.yaml', '.yml')):
        import yaml
        return yaml.load(open(filename))
    else:
        ValueError('Unknown config type: %s' % filename)


def parse_environ(prefix, environ=None):
    if environ is None:
        from os import environ

    config = {}
    for varname, value in environ.items():
        if varname.startswith(prefix):
            varname = varname.replace(prefix, '', 1).lower()
            config[varname] = value
    return _listify_services(config)


class Config(object):
    def __init__(
            self,
            pgdir='playground',
            pgconf='conf.yaml',
            services=('default',),
    ):
        self.pgdir = pgdir
        self.pgconf = pgconf
        self.services = services

    def start(self, wait=True):
        """start a list of services"""
        print 'starting:', self.services, wait

    def stop(self):
        """stop a list of services"""
        print 'stopping:', self.services

    @classmethod
    def from_file(cls, filename):
        return cls(**parse_config(filename))

    @classmethod
    def from_environ(cls, environ=None):
        return cls(**parse_environ('PGCTL_', environ))

    @classmethod
    def from_cli(cls, args):
        return cls(**vars(args))

    @classmethod
    def merge(cls, *configs):
        result = {}
        for config in configs:
            result.update(config)
        return cls(**result)
