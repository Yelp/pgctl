import os
from argparse import Namespace
from contextlib import contextmanager
from unittest import mock

from testing.norm import norm_trailing_whitespace_json
from testing.subprocess import assert_command

from pgctl.config import Config


@contextmanager
def setup(tmpdir):
    etc = tmpdir.ensure_dir('etc')
    home = tmpdir.ensure_dir('home')
    app = tmpdir.ensure_dir('app')
    a = app.ensure_dir('a')
    b = a.ensure_dir('b')
    c = b.ensure_dir('c')

    etc.join('my.conf').write('[my]\netc = etc')
    home.join('.my.json').write('{"home":"home"}')
    app.join('my.ini').write('''\
[my]
app = app
apps_list =
    1
    2
    3\
''')
    a.join('my.yaml').write('app/a: app/a')
    b.join('my.yaml').write('app/b: app/b')
    c.join('my.junk').write('junk!')
    c.join('foo.json').write('{"foo": "bar"}')

    with mock.patch.dict(os.environ, {
        'PREFIX': tmpdir.strpath,
        'HOME': home.strpath,
        'MY_ENVIRON': 'environ',
        'MY_ENVIRONS_LIST': '1 2 3',
    }):
        with c.as_cwd():
            yield


class DescribeCombined:

    def it_combines_all_the_configs(self, tmpdir):
        config = Config('my', {'default': 'default'})
        with setup(tmpdir):
            conf = config.combined(args=Namespace(config='foo.json'))

        assert conf == {
            'config': 'foo.json',
            'etc': 'etc',
            'home': 'home',
            'app': 'app',
            'apps': ['1', '2', '3'],
            'app/a': 'app/a',
            'app/b': 'app/b',
            'environ': 'environ',
            'environs': ['1', '2', '3'],
            'foo': 'bar',
        }

    def it_can_be_run_via_python_m(self, tmpdir):
        from sys import executable
        expected_output = '''\
{
    "app": "app",
    "app/a": "app/a",
    "app/b": "app/b",
    "apps": [
        "1",
        "2",
        "3"
    ],
    "config": null,
    "environ": "environ",
    "environs": [
        "1",
        "2",
        "3"
    ],
    "etc": "etc",
    "home": "home"
}
'''
        with setup(tmpdir):
            assert_command(
                (executable, '-m', 'pgctl.config', 'my'),
                expected_output,
                '',
                0,
                norm=norm_trailing_whitespace_json,
            )
