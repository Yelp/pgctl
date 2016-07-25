# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import unicode_literals

import os

import pytest
import six
from testing.norm import norm_trailing_whitespace_json
from testing.subprocess import assert_command

from pgctl import __version__


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
    "poll": ".01",
    "services": [
        "default"
    ],
    "timeout": "2.0"
}}
'''.format(pghome=expected_pghome)

        assert_command(
            ('pgctl', 'config'),
            expected_output,
            '',
            0,
            norm=norm_trailing_whitespace_json,
            cwd=tmpdir.strpath,
            env=env,
        )

        from sys import executable
        assert_command(
            (executable, '-m', 'pgctl.cli', 'config'),
            expected_output,
            '',
            0,
            norm=norm_trailing_whitespace_json,
            cwd=tmpdir.strpath,
            env=env,
        )

    def it_shows_help_with_no_arguments(self):
        assert_command(
            ('pgctl',),
            '',
            '''\
usage: pgctl [-h] [--version] [--pgdir PGDIR] [--pghome PGHOME]
             {{start,stop,status,restart,reload,log,debug,config}}
             [services [services ...]]
pgctl: error: {}
'''.format(
                'too few arguments'
                if six.PY2 else
                'the following arguments are required: command'
            ),
            2,  # too few arguments
        )

    def it_shows_version(self):
        version_s = __version__ + '\n'
        assert_command(
            ('pgctl', '--version'),
            # argparse changes where `version` goes in py3
            '' if six.PY2 else version_s,
            version_s if six.PY2 else '',
            0,  # too few arguments
        )
