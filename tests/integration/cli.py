# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import unicode_literals


class DescribeCli(object):

    def it_can_show_its_configuration(self, tmpdir):
        from subprocess import Popen, PIPE
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
