# -*- coding: utf-8 -*-
"""
Format stolen from daemontools' tai64nlocal:

    2015-10-19 17:43:37.772152500

We'd usually use the s6 tool, but there's a problem:
    http://www.mail-archive.com/skaware@list.skarnet.org/msg00575.html
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals


def timestamp():
    from datetime import datetime
    return datetime.now().strftime('%F %T.%f ')


def prepend_timestamps(infile, outfile):
    needstamp = True
    while True:
        c = infile.read(1)
        if c == b'':  # EOF
            break
        elif needstamp:
            outfile.write(timestamp().encode('UTF-8'))
            needstamp = False
        outfile.write(c)
        if c == b'\n':
            needstamp = True


def main():
    import sys
    import io
    infile = io.open(sys.stdin.fileno(), buffering=0, mode='rb')
    outfile = io.open(sys.stdout.fileno(), buffering=0, mode='wb')
    prepend_timestamps(infile, outfile)


if __name__ == '__main__':
    exit(main())
