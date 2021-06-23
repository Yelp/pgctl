#!/usr/bin/env python
"""
This is a quick script that enables the coveragepy process_startup feature in this python
interpreter in subsequent runs.

See: http://nedbatchelder.com/code/coverage/subprocess.html
"""
from distutils.sysconfig import get_python_lib
from os.path import join

python_lib = get_python_lib()
with open(join(python_lib, 'coveragepy.pth'), 'w') as coveragepy_pth:
    coveragepy_pth.write('import sys; exec(%r)\n' % '''\
try:
    import coverage
except ImportError:
    pass
else:
    coverage.process_startup()
''')
