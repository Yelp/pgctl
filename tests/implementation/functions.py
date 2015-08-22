# -*- coding: utf-8 -*-
# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from frozendict import frozendict
from testfixtures import ShouldRaise

from pgctl.functions import JSONEncoder
from pgctl.functions import uniq


class DescribeUniq(object):

    def it_does_not_have_duplicates(self):
        data = ['b', 'b', 'b']
        assert list(uniq(data)) == ['b']

    def it_removes_duplicates_with_first_one_wins_mentality(self):
        data = ['a', 'b', 'c', 'b', 'd', 'a']
        assert list(uniq(data)) == ['a', 'b', 'c', 'd']


class DescribeJSONEncoder(object):

    def it_encodes_frozendict(self):
        test_dict = frozendict({
            'pgdir': 'playground',
            'services': ('default',),
            'aliases': frozendict({
                'default': ('')
            }),
        })
        result = JSONEncoder(sort_keys=True, indent=4).encode(test_dict)
        assert result == '''\
{
    "aliases": {
        "default": ""
    }, 
    "pgdir": "playground", 
    "services": [
        "default"
    ]
}'''  # noqa

    def it_encodes_other(self):
        with ShouldRaise(TypeError("<type 'object'> is not JSON serializable")):
            JSONEncoder(sort_keys=True, indent=4).encode(object)
