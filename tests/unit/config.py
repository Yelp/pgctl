from __future__ import absolute_import
from __future__ import unicode_literals

import os

import mock
import pytest
from testfixtures import ShouldRaise
from testfixtures import StringComparison as S

import pgctl.config as C


class example1(object):
    config = C.Config('example1')

    ini = '''\
[example1]
pgdir = mypgdir
pgconf = my.conf
services_list =
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

    json = '''\
{
    "pgdir": "mypgdir",
    "pgconf": "my.conf",
    "services": [
        "first",
        "second",
        "third"
    ]
}
'''

    environ = {
        'PATH': 'A:B:C',
        'EXAMPLE1_PGDIR': 'mypgdir',
        'EXAMPLE1_PGCONF': 'my.conf',
        'EXAMPLE1_SERVICES_LIST': 'first second third',
    }

    import argparse
    cli_args = argparse.Namespace(
        pgdir='mypgdir',
        pgconf='my.conf',
        services=['first', 'second', 'third'],
        config=None,
    )

    parsed = {
        'pgdir': 'mypgdir',
        'pgconf': 'my.conf',
        'services': ['first', 'second', 'third'],
    }

    parameters = pytest.mark.parametrize(
        'format,suffix',
        (
            ('ini', 'ini'),
            ('ini', 'conf'),
            ('yaml', 'yaml'),
            ('yaml', 'yml'),
            ('json', 'json'),
        )
    )


class DescribeConfig(object):

    @example1.parameters
    def it_can_parse_files(self, tmpdir, format, suffix):
        conffile = tmpdir.join('my.' + suffix)
        conffile.write(getattr(example1, format))
        conf = example1.config.from_file(conffile.strpath)
        assert conf == example1.parsed

    def it_cant_parse_nonsense(self, tmpdir):
        conffile = tmpdir.join('my.nonsense')
        conffile.write(example1.yaml)

        with ShouldRaise(
            C.UnrecognizedConfig(S(r'Unknown config type: .*/my\.nonsense'))
        ):
            example1.config.from_file(conffile.strpath)

    def it_can_be_derived_from_args(self):
        conf = example1.config.from_cli(example1.cli_args)

        # this one is slightly different because of how cli arguments are parsed
        expected = example1.parsed.copy()
        expected['config'] = None

        assert conf == expected

    def it_can_be_derived_from_homedir(self, tmpdir):
        conffile = tmpdir.join('.example1.ini')
        conffile.write(example1.ini)
        with mock.patch.dict(os.environ, {'HOME': tmpdir.strpath}):
            conf = example1.config.from_homedir()
        assert conf == example1.parsed

    def it_can_find_system_level_config(self, tmpdir):
        conffile = tmpdir.join('etc/example1.yaml').ensure()
        conffile.write(example1.yaml)
        with mock.patch.dict(os.environ, {'PREFIX': tmpdir.strpath}):
            assert example1.config.from_system() == example1.parsed


class DescribeFromEnviron(object):

    def it_can_parse(self):
        config = C.Config(projectname='my')
        assert config.from_environ({'MY_X': 2, 'MYY': 3, 'Z': 4}) == {'x': 2}

    def it_has_parity_with_file_configs(self):
        config = C.Config(projectname='example1')
        assert config.from_environ(example1.environ) == example1.parsed

    def it_can_parse_the_environ(self):
        config = C.Config(projectname='example1')
        with mock.patch.dict(os.environ, example1.environ):
            assert config.from_environ() == example1.parsed


class DescribeMerge(object):

    def it_overrides_correctly(self):
        assert C.merge((
            {1: 1},
            {1: 2},
        )) == {1: 2}

    def it_handles_None_gracefully(self):
        assert C.merge((
            {1: 1, 2: 2},
            None,
            {1: 'one', 3: 'three', 4: None},
            {'four': 'four'},
        )) == {1: 'one', 2: 2, 3: 'three', 4: None, 'four': 'four'}

    def it_handles_nested_maps(self):
        assert C.merge((
            {
                'map': {
                    'a': 'b',
                    'c': 'd',
                },
                2: {},
                3: 3,
            },
            {
                'map': {
                    'a': 'e',
                    'f': 'g',
                },
                2: 2,
                3: {},
            },
        )) == {
            'map': {
                'a': 'e',
                'c': 'd',
                'f': 'g',
            },
            2: 2,
            3: {},
        }

    def it_handles_frozen_maps(self):
        from frozendict import frozendict
        assert C.merge((
            frozendict({
                'map': frozendict({
                    'a': 'b',
                    'c': 'd',
                }),
            }),
            frozendict({
                'map': frozendict({
                    'a': 'e',
                    'f': 'g',
                }),
            }),
        )) == {
            'map': {
                'a': 'e',
                'c': 'd',
                'f': 'g',
            },
        }


class DescribeFromPathPrefix(object):

    @example1.parameters
    def it_can_find_configs(self, tmpdir, format, suffix):
        conffile = tmpdir.join('prefix-example1.' + suffix)
        conffile.write(getattr(example1, format))
        conf = example1.config.from_path_prefix(
            tmpdir.join('prefix-').strpath
        )
        assert conf == example1.parsed

    def it_represents_no_config_as_None(self, tmpdir):
        conf = example1.config.from_path_prefix(tmpdir.strpath + '/')
        assert conf is None

    def it_skips_nonsense(self, tmpdir):
        conffile = tmpdir.join('example1.ini')
        conffile.write(example1.ini)
        conffile = tmpdir.join('example1.nonsense')
        conffile.write(example1.ini)
        conf = example1.config.from_path_prefix(tmpdir.strpath + '/')
        assert conf == example1.parsed

    def it_explodes_on_ambiguity(self, tmpdir):
        conffile = tmpdir.join('example1.ini')
        conffile.write(example1.ini)
        conffile = tmpdir.join('example1.conf')
        conffile.write(example1.ini)
        with ShouldRaise(
            C.AmbiguousConfig(
                S(r'multiple configurations found at .*/example1\.\*'))
        ):
            example1.config.from_path_prefix(tmpdir.strpath + '/')


class DescribeFromApp(object):

    def it_searches_pwd(self, tmpdir):
        conffile = tmpdir.join('example1.json')
        conffile.write(example1.json)
        with tmpdir.as_cwd():
            conf = example1.config.from_app()
        assert conf == example1.parsed

    def it_searches_parent_dirs(self, tmpdir):
        conffile = tmpdir.join('example1.json')
        conffile.write(example1.json)
        with tmpdir.join('a', 'b', 'c').ensure_dir().as_cwd():
            conf = example1.config.from_app()
        assert conf == example1.parsed

    def it_merges_parent_Configs(self, tmpdir):
        tmpdir.join('example1.json').write('''{"a":1, "b":2}''')
        tmpdir.join('a/b/c/example1.yaml').ensure().write('''{"b":3, "c":4}''')
        with tmpdir.join('a', 'b', 'c').ensure_dir().as_cwd():
            conf = example1.config.from_app()
        assert conf == {'a': 1, 'b': 3, 'c': 4}
