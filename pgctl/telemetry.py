import datetime
import getpass
import json
import os
import socket
import sys
import typing

import yaml

from pgctl import __version__


try:
    import clog
except ImportError:
    clog = None

_clog_configured = False


def setup_clog(config_path: str) -> None:  # pragma: no cover
    global _clog_configured
    if clog is None or _clog_configured:
        return

    with open(config_path) as f:
        clog_config = yaml.safe_load(f)
    clog.config.configure_from_dict(clog_config)

    _clog_configured = True


def _event_context() -> typing.Dict[str, typing.Any]:
    return {
        'argv': sys.argv,
        'cwd': os.getcwd(),
        'hostname': socket.gethostname(),
        'time': datetime.datetime.now().isoformat(),
        'user': getpass.getuser(),
        'version': __version__,
    }


def emit_event(event_name: str, attributes: typing.Dict[str, typing.Any]):
    if not _clog_configured:
        return

    payload = dict(
        _event_context(),
        event=event_name,
        attributes=attributes,
    )
    clog.log_line('tmp_pgctl_events', json.dumps(payload, sort_keys=True))
