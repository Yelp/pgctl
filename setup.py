# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from setuptools import find_packages
from setuptools import setup


def main():
    setup(
        name=str('pgctl'),
        description='A tool to configure and manage developer playgrounds.',
        version='0.1.0',
        platforms='linux',
        classifiers=[
            'Programming Language :: Python :: 2.7',
        ],

        packages=find_packages(exclude=('tests*',)),
        install_requires=[
            'argparse',
            'frozendict',
            'cached-property',
            'six',
        ],
        # FIXME: all tests still pass if you break this.
        entry_points={
            'console_scripts': [
                'pgctl-2015 = pgctl.cli:main',
            ],
        },
    )


if __name__ == '__main__':
    exit(main())
