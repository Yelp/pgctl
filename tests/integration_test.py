# pylint:disable=old-style-class,no-self-use,no-init
from subprocess import Popen


class DescribePgctlCLI:
    def it_shows_help_with_no_arguments(self):
        p = Popen(('pgctl-2015',))
        assert p.wait() == 2  # too few arguments
        # TODO assert the output
