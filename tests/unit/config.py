#pylint:disable=no-self-use
import pytest
parametrize = pytest.mark.parametrize

import pgctl.config as C


class example1(object):
    conf = '''\
[pgctl]
pgdir = mypgdir
pgconf = my.conf
services =
    first
    second
    third
'''

    yaml = '''\
pgdir: mypgdir
pgconf: my.conf
services:
    - first
    - second
    - third
'''

    environ = {
        'PATH': 'A:B:C',
        'PGCTL_PGDIR': 'mypgdir',
        'PGCTL_PGCONF': 'my.conf',
        'PGCTL_SERVICES': 'first second third',
    }

    import argparse
    cli_args = argparse.Namespace(
        pgdir='mypgdir',
        pgconf='my.conf',
        services=['first', 'second', 'third'],
    )

    parsed = {
        'pgdir': 'mypgdir',
        'pgconf': 'my.conf',
        'services': ['first', 'second', 'third'],
    }


class DescribeConfig(object):
    def it_can_be_derived_from_a_file(self, tmpdir):
        conffile = tmpdir.join('my.conf')
        conffile.write(example1.conf)
        conf = C.Config.from_file(conffile.strpath)
        assert vars(conf) == example1.parsed

    def it_can_be_derived_from_args(self):
        conf = C.Config.from_cli(example1.cli_args)
        assert vars(conf) == example1.parsed


class DescribeParseConfig(object):
    @parametrize('suffix', ('conf', 'ini'))
    def it_can_parse_conf(self, tmpdir, suffix):
        conffile = tmpdir.join('my.' + suffix)
        conffile.write(example1.conf)
        conf = C.parse_config(conffile.strpath)
        assert conf == example1.parsed

    @parametrize('suffix', ('yaml', 'yml'))
    def it_can_parse_yaml(self, tmpdir, suffix):
        conffile = tmpdir.join('my.' + suffix)
        conffile.write(example1.yaml)
        conf = C.parse_config(conffile.strpath)
        assert conf == example1.parsed


class DescribeParseEnvirons(object):
    def it_can_parse(self):
        assert C.parse_environ('MY_', {'MY_X': 2, 'MYY': 3, 'Z': 4}) == {'x': 2}

    def it_has_parity_with_file_configs(self):
        assert C.parse_environ('PGCTL_', example1.environ) == example1.parsed
