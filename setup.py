from setuptools import find_packages
from setuptools import setup

from pgctl import __version__


def main():
    setup(
        name='pgctl',
        description='A tool to configure and manage developer playgrounds.',
        url='http://pgctl.readthedocs.org/en/latest/',
        version=__version__,
        platforms=['linux'],
        classifiers=[
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: Implementation :: CPython',
        ],
        python_requires='>=3.6',
        packages=find_packages(exclude=('tests*',)),
        install_requires=[
            'frozendict',
            'cached-property',
            'contextlib2',
            # 1.4.32 adds PathLike compatibility to py.path
            'py>=1.4.32',
            'pyyaml',
            's6',
        ],
        extras_require={
            'telemetry': ['yelp-clog'],
        },
        # FIXME: all tests still pass if you break this.
        entry_points={
            'console_scripts': [
                'pgctl = pgctl.cli:main',
                'pgctl-poll-ready = pgctl.poll_ready:main',
                'pgctl-fuser = pgctl.fuser:main',
            ],
        },

        author='Buck Evan',
        author_email='buck.2019@gmail.com',
    )


if __name__ == '__main__':
    exit(main())
