# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import unicode_literals

import os

import pytest
from testing import assert_command


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
            homedir,
    ):
        env = dict(os.environ, XDG_RUNTIME_DIR=xdg_runtime_dir)
        expected_output = '''\
{{
    "aliases": {{
        "default": [
            "(all services)"
        ]
    }}, 
    "command": "config", 
    "pgdir": "playground", 
    "pghome": "{pghome}", 
    "services": [
        "default"
    ], 
    "wait_period": "2.0"
}}
'''.format(pghome=expected_pghome)  # noqa

        assert_command(
            ('pgctl-2015', 'config'),
            expected_output,
            '',
            0,
            cwd=tmpdir.strpath,
            env=env,
        )

        from sys import executable
        assert_command(
            (executable, '-m', 'pgctl.cli', 'config'),
            expected_output,
            '',
            0,
            cwd=tmpdir.strpath,
            env=env,
        )

    def it_shows_help_with_no_arguments(self):
        assert_command(
            ('pgctl-2015',),
            '',
            '''\
usage: pgctl-2015 [-h] [--version] [--pgdir PGDIR] [--pghome PGHOME]
                  {start,stop,status,restart,reload,log,debug,config}
                  [services [services ...]]
pgctl-2015: error: too few arguments
''',
            2,  # too few arguments
        )
