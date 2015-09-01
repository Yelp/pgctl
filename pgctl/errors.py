from __future__ import absolute_import
from __future__ import unicode_literals

from .functions import bestrelpath


class PgctlUserError(Exception):
    """
    This is the class of user errors, as distinct from programmer errors.
    When a user has an error, we don't need or want a stack trace.
    """


class CircularAliases(PgctlUserError):
    pass


class NoPlayground(PgctlUserError):
    pass


class NoSuchService(PgctlUserError):
    pass


class LockHeld(PgctlUserError):

    def __str__(self):
        from subprocess import check_output, STDOUT
        path, = self.args  # pylint:disable=unpacking-non-sequence
        path = bestrelpath(path)
        fuser = check_output(('fuser', '-v', path), stderr=STDOUT)
        return '''\
We sent SIGTERM, but these processes did not stop:
%s
temporary fix: fuser -kv %s
permanent fix: http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services''' % (fuser, path)
