# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import unicode_literals

import os
from subprocess import PIPE
from subprocess import Popen

import pytest


class DescribeCli(object):

    @pytest.mark.parametrize(
        ('xdg_runtime_dir', 'expected_pghome'),
        [
            ('/herp/derp', '/herp/derp/pgctl'),
            ('~/.herp', '~/.herp/pgctl'),
            ('', '~/.run/pgctl'),
        ],
    )
    def it_can_show_its_configuration(
            self,
            xdg_runtime_dir,
            expected_pghome,
            tmpdir,
            in_example_dir,
            homedir,
    ):
        env = dict(os.environ, XDG_RUNTIME_DIR=xdg_runtime_dir)
        config1 = Popen(('pgctl-2015', 'config'), stdout=PIPE, cwd=tmpdir.strpath, env=env)
        config1, _ = config1.communicate()
        assert config1 == '''\
{{
    "command": "config", 
    "pgconf": "conf.yaml", 
    "pgdir": "playground", 
    "pghome": "{pghome}", 
    "services": [
        "default"
    ]
}}
'''.format(pghome=expected_pghome)  # noqa

        from sys import executable
        config2 = Popen((executable, '-m', 'pgctl.cli', 'config'), stdout=PIPE, cwd=tmpdir.strpath, env=env)
        config2, _ = config2.communicate()
        assert config1 == config2

    def it_shows_help_with_no_arguments(self):
        p = Popen(('pgctl-2015',))
        assert p.wait() == 2  # too few arguments
        # TODO assert the output
