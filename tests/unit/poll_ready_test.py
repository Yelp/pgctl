import os
from unittest import mock

import pytest

from pgctl import poll_ready


@pytest.yield_fixture(autouse=True)
def in_tmpdir(tmpdir):
    with tmpdir.as_cwd():
        yield


class DescribeFloatFile:

    def it_loads_files(self):
        filename = 'notification-fd'
        with open(filename, 'w') as f:
            f.write('5')
        result = poll_ready.floatfile(filename)
        assert isinstance(result, float)
        assert result == 5.0


class DescribeGetVal:

    def it_loads_environment_var(self):
        with mock.patch.dict(os.environ, [('SVWAIT', '5')]):
            result = poll_ready.getval('does not exist', 'SVWAIT', '2')
            assert isinstance(result, float)
            assert result == 5.0

    def it_loads_file_var(self):
        with mock.patch.dict(os.environ, [('SVWAIT', '6')]):
            filename = 'wait-ready'
            with open(filename, 'w') as f:
                f.write('5')
            result = poll_ready.getval(filename, 'SVWAIT', '2')
            assert isinstance(result, float)
            assert result == 5.0

    def it_loads_default_var(self):
        result = poll_ready.getval('does not exist', 'SVWAIT', '2')
        assert isinstance(result, float)
        assert result == 2.0


def test_main_coverage_hack():
    """For some reason, coverage flakes on the first branch of poll-ready's
    main function. This test executes the lines in that branch to avoid
    test failures that are already ignored by the maintainers.

    We suspect the underlying coverage problem is related to the exec call and
    coverage not getting collecting data before the new image executable image
    is loaded, but have not been able to fix it.
    """
    class CoverageHackException(Exception):
        pass

    with mock.patch.object(
        poll_ready,
        'exec_',
        autospec=True,
    ) as mock_exec, mock.patch.dict(
            os.environ,
            {'PGCTL_DEBUG': 'true'},
    ), pytest.raises(CoverageHackException):
        mock_exec.side_effect = CoverageHackException
        poll_ready.main()
