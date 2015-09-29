# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from setuptools import find_packages
from setuptools import setup

from pgctl import __version__


def main():
    setup(
        name=str('pgctl'),
        description='A tool to configure and manage developer playgrounds.',
        url='http://pgctl.readthedocs.org/en/latest/',
        version=__version__,
        platforms='linux',
        classifiers=[
            'Programming Language :: Python :: 2.7',
        ],
        packages=find_packages(exclude=('tests*',)),
        install_requires=[
            'argparse',
            'frozendict',
            'cached-property',
            'py',
            'six',
        ],
        # FIXME: all tests still pass if you break this.
        entry_points={
            'console_scripts': [
                'pgctl-2015 = pgctl.cli:main',
                'pgctl-poll-ready = pgctl.poll_ready:main',
            ],
        },

        author='Buck Evan',
        author_email='buck.2019@gmail.com',
    )


if __name__ == '__main__':
    exit(main())
