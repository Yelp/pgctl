from py._path.local import LocalPath as Path

from pgctl.service import Service


def test_str_and_repr():
    service = Service(Path('/tmp/magic-service'), Path('/tmp/magic-service-scratch'), None)
    assert str(service) == 'magic-service'
