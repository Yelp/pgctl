# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import unicode_literals

import os
from contextlib import contextmanager

import mock

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

    with mock.patch.dict(os.environ, {
        'PREFIX': tmpdir.strpath,
        'HOME': home.strpath,
        'MY_ENVIRON': 'environ',
        'MY_ENVIRONS_LIST': '1 2 3',
    }):
        with c.as_cwd():
            yield


class DescribeCombined(object):

    def it_combines_all_the_configs(self, tmpdir):
        config = Config('my', {'default': 'default'})
        with setup(tmpdir):
            conf = config.combined()

        assert conf == {
            'etc': 'etc',
            'home': 'home',
            'app': 'app',
            'apps': ['1', '2', '3'],
            'app/a': 'app/a',
            'app/b': 'app/b',
            'environ': 'environ',
            'environs': ['1', '2', '3'],
        }

    def it_can_be_run_via_python_m(self, tmpdir):
        from sys import executable
        from subprocess import Popen, PIPE
        with setup(tmpdir):
            config = Popen((executable, '-m', 'pgctl.config', 'my'), stdout=PIPE)
            config, _ = config.communicate()

        assert config == '''\
{
    "app": "app", 
    "app/a": "app/a", 
    "app/b": "app/b", 
    "apps": [
        "1", 
        "2", 
        "3"
    ], 
    "environ": "environ", 
    "environs": [
        "1", 
        "2", 
        "3"
    ], 
    "etc": "etc", 
    "home": "home"
}
'''  # noqa
