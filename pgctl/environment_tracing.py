import os
import re
import typing


NUMBERS_ONLY = re.compile('^[0-9]+$')


def find_processes_with_environ(environ: typing.Dict[bytes, bytes], proc_root: str = '/proc') -> typing.Set[int]:
    ret = set()

    for proc_entry in os.listdir(proc_root):
        if not NUMBERS_ONLY.match(proc_entry):
            continue
        try:
            with open(os.path.join(proc_root, proc_entry, 'environ'), 'rb') as f:
                proc_environ = {}
                for key_value in f.read().split(b'\x00'):
                    if key_value and b'=' in key_value:
                        key, value = key_value.split(b'=', 1)
                        proc_environ[key] = value

                if all(proc_environ.get(key) == value for key, value in environ.items()):
                    ret.add(int(proc_entry))
        except (PermissionError, FileNotFoundError):
            continue

    return ret
