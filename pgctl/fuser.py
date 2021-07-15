"""\
usage: pgctl-fuser [-d] file [file ...]

Shows the pids (of the current user) that have this file opened.
This is useful for finding which processes hold a file lock (flock).
This has the same behavior as `lsof -t file`, but is *much* faster.
"""
from .debug import trace


def stat(path):
    from os import stat
    try:
        return stat(path)
    except OSError as error:
        trace('fuser suppressed: %s', error)
    return None


def listdir(path):
    from os import listdir
    try:
        return listdir(path)
    except OSError as error:
        trace('fuser suppressed: %s', error)
        return ()


def fuser(path, allow_deleted=False):
    """Return the list of pids that have 'path' open, for the current user"""
    search = stat(path)
    if search is None and not allow_deleted:
        return

    from glob import glob
    for fddir in glob('/proc/*/fd/'):
        try:
            pid = int(fddir.split('/', 3)[2])
        except ValueError:
            continue

        fds = listdir(fddir)
        for fd in fds:
            from os.path import join
            fd = join(fddir, fd)
            found = stat(fd)
            if found is None:
                # fd disappeared since we listed
                continue

            if found == search:
                yield pid
                break

            if allow_deleted and found.st_nlink == 0:
                from os import readlink
                if readlink(fd) == path + ' (deleted)':
                    yield pid
                    break


def main(args=None):
    from argparse import ArgumentParser
    from sys import argv
    args = args or argv

    parser = ArgumentParser(description=__doc__)
    parser.add_argument('-d', '--allow-deleted', action='store_true', help='allow deleted files')
    parser.add_argument('file', nargs='+')
    args = parser.parse_args(args[1:])

    for f in args.file:
        for pid in fuser(f, allow_deleted=args.allow_deleted):
            print(pid)


if __name__ == '__main__':
    exit(main())
