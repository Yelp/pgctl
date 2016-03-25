from __future__ import absolute_import
from __future__ import unicode_literals


def reraise(error):
    import six
    six.reraise(type(error), error)


class Impossible(AssertionError):
    """raised only in cases that we believe to be impossible"""


class Unsupervised(Exception):
    """The pgctl supervision process has gone missing."""


class PgctlUserMessage(Exception):
    """
    This is the class of user messages, as distinct from programmer errors.
    For some cases, there's nothing better to do than send a message to the user.
    When that happens, we don't need or want a stack trace.
    """


class CircularAliases(PgctlUserMessage):
    """The user has configured their pgctl aliases with a circular definition."""


class NoPlayground(PgctlUserMessage):
    """The pgctl system could find no playground to operate on."""


class NoSuchService(PgctlUserMessage):
    """The pgctl system could find the indicated playground service to operate on."""


class LockHeld(PgctlUserMessage):
    """The pgctl supervision lock is held. This generally indicates subprocesses escaping supervision."""


class NotReady(PgctlUserMessage):
    """The service is still performing its previous state change."""
