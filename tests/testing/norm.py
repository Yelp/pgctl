"""
Normalize the output of programs, for comparison across invocations.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

from re import compile as Regex
from re import escape
from sys import prefix


class Normalized(str):
    rules = ()

    def __new__(cls, value):
        for pattern, replacement in cls.rules:
            value = pattern.sub(replacement, value)
        return super(Normalized, cls).__new__(cls, value)


class timestamp(Normalized):
    """normalize pgctl's output"""
    rules = (
        # 2015-10-16 17:05:56.635827500
        (Regex(r'(?m)^\d{4}(-\d\d){2} (\d\d:){2}\d\d\.\d{6,9} '), '{TIMESTAMP} '),
    )


class pgctl(Normalized):
    """normalize pgctl's output"""
    rules = timestamp.rules + (
        (Regex(r'\(pid \d+\)'), '(pid {PID})'),
        (Regex(r' [\d.]+ seconds'), ' {TIME} seconds'),
        (
            Regex(r'(?m)^UID +PID +PPID +PGID +SID +C +STIME +TTY +STAT +TIME +CMD'),
            '{PS-HEADER}',
        ),
        (
            Regex(r'(?m)^\S+ +\d+ +\d+ +\d+ +\d+ +\d+ +\S+ +\S+ +\S+ +\S+ +'),
            '{PS-STATS} ',
        ),
        # TODO-TEST: the slow-fuser case:
        (Regex(r' \(it took [\d.]+s to poll\)'), ''),
        (Regex(r'\B%s\b' % escape(prefix)), '${PREFIX}'),
        (Regex(r'/(pypy3?|python[23])(\.[0-9]+)? '), '/python '),
    )


def norm_trailing_whitespace_json(string):
    return string.replace(' \n', '\n')
