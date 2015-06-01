# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from setuptools import find_packages
from setuptools import setup


setup(
    name=str('pgctl'),
    description='Tool to setup a yelp playground',
    version='0.0.1',
    platforms='linux',
    classifiers=[
        'Programming Language :: Python :: 2.7',
    ],

    packages=find_packages(exclude=('tests*',)),
    install_requires=[
        'argparse',
    ],
    # FIXME: all tests still pass if you break this.
    entry_points={
        'console_scripts': [
            'pg = pgctl.main:main.py',
        ],
    },
)
