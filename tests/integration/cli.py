# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import unicode_literals

from subprocess import PIPE
from subprocess import Popen

from pgctl.cli import idempotent_svscan


class DescribeCli(object):

    def it_can_show_its_configuration(self, tmpdir):
        config1 = Popen(('pgctl-2015', 'config'), stdout=PIPE, cwd=tmpdir.strpath)
        config1, _ = config1.communicate()
        assert config1 == '''\
{
    "command": "config", 
    "pgconf": "conf.yaml", 
    "pgdir": "playground", 
    "services": [
        "default"
    ]
}
'''  # noqa

        from sys import executable
        config2 = Popen((executable, '-m', 'pgctl.cli', 'config'), stdout=PIPE, cwd=tmpdir.strpath)
        config2, _ = config2.communicate()
        assert config1 == config2

    def it_shows_help_with_no_arguments(self):
        p = Popen(('pgctl-2015',))
        assert p.wait() == 2  # too few arguments
        # TODO assert the output


class DescribeSvscan(object):

    def it_does_not_deadlock(self, in_example_dir):
        idempotent_svscan('bad_service')
        p = Popen(('date'), stdout=PIPE, stderr=PIPE)
        _, _ = p.communicate()
        assert True
