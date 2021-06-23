#!/usr/bin/env python
import imp
import sys


def main():
    # we don't want $PWD to obscure our python packages,
    # unless the module can't be found in the python packages
    path = sys.path[1:] + sys.path[:1]
    modulename = sys.argv[1]

    print(imp.find_module(modulename, path)[1])


if __name__ == '__main__':
    exit(main())
