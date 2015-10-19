# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import unicode_literals

import uuid
from sys import executable

from testing.subprocess import assert_command


class DescribeCombined(object):

    def it_can_be_run_via_python_m(self, tmpdir):
        a = tmpdir.ensure_dir('a')
        b = a.ensure_dir('b')
        c = b.ensure_dir('c')

        prefix = str(uuid.uuid4())
        tmpdir.ensure(prefix + '.ini')
        a.ensure(prefix + '.yaml')
        b.ensure(prefix + '.conf')
        c.ensure(prefix + '.a')
        c.ensure(prefix + '.b').chmod(0o666)

        with c.as_cwd():
            assert_command(
                (executable, '-m', 'pgctl.configsearch', prefix + '*'),
                '''\
{tmpdir}/a/b/c/{prefix}.a
{tmpdir}/a/b/{prefix}.conf
{tmpdir}/a/{prefix}.yaml
{tmpdir}/{prefix}.ini
'''.format(tmpdir=tmpdir.strpath, prefix=prefix),
                '',
                0,
            )
