from __future__ import absolute_import
from __future__ import unicode_literals


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
    pass


class NotReady(PgctlUserError):
    pass


class Unsupervised(Exception):
    pass
