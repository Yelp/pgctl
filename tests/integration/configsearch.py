# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import unicode_literals

from subprocess import PIPE
from subprocess import Popen
from sys import executable


class DescribeCombined(object):

    def it_can_be_run_via_python_m(self, tmpdir):
        a = tmpdir.ensure_dir('a')
        b = a.ensure_dir('b')
        c = b.ensure_dir('c')

        tmpdir.ensure('my.ini')
        a.ensure('my.yaml')
        b.ensure('my.conf')
        c.ensure('my.a')
        c.ensure('my.b').chmod(0o666)

        with c.as_cwd():
            config = Popen((executable, '-m', 'pgctl.configsearch', 'my*'), stdout=PIPE)
            config, _ = config.communicate()

        assert config == '''\
{tmpdir}/a/b/c/my.a
{tmpdir}/a/b/my.conf
{tmpdir}/a/my.yaml
{tmpdir}/my.ini
'''.format(tmpdir=tmpdir.strpath)
