import json
import subprocess

import pytest
from testing.subprocess import assert_command

from pgctl import __version__


class DescribeCli:

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
        with tmpdir.as_cwd():
            output = json.loads(subprocess.check_output(('pgctl', 'config')))

        # Just smoke testing that a few values are present.
        assert 'aliases' in output
        assert 'verbose' in output

    def it_shows_help_with_no_arguments(self):
        proc = subprocess.run(('pgctl',), capture_output=True)
        assert proc.returncode == 2
        assert b'usage: pgctl' in proc.stderr
        assert b'pgctl: error: the following arguments are required: command' in proc.stderr

    def it_shows_version(self):
        version_s = __version__ + '\n'
        assert_command(
            ('pgctl', '--version'),
            version_s,
            '',
            0,  # too few arguments
        )
