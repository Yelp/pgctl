import pytest

from pgctl.dependencies import resolve_start_order
from pgctl.dependencies import topological_sort
from pgctl.errors import CircularDependencies
from pgctl.errors import PgctlUserMessage


class FakeService:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'FakeService({self.name!r})'

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


def it_handles_no_dependencies():
    services = [FakeService('a'), FakeService('b'), FakeService('c')]
    result = topological_sort(services, {})
    assert set(s.name for s in result) == {'a', 'b', 'c'}


def it_sorts_a_linear_chain():
    services = [FakeService('db'), FakeService('api'), FakeService('web')]
    deps = {'api': ['db'], 'web': ['api']}
    result = topological_sort(services, deps)
    names = [s.name for s in result]
    assert names.index('db') < names.index('api')
    assert names.index('api') < names.index('web')


def it_sorts_a_diamond_dependency():
    services = [FakeService('db'), FakeService('cache'), FakeService('api'), FakeService('web')]
    deps = {'api': ['db', 'cache'], 'web': ['api']}
    result = topological_sort(services, deps)
    names = [s.name for s in result]
    assert names.index('db') < names.index('api')
    assert names.index('cache') < names.index('api')
    assert names.index('api') < names.index('web')


def it_raises_on_circular_dependency():
    services = [FakeService('a'), FakeService('b')]
    deps = {'a': ['b'], 'b': ['a']}
    with pytest.raises(CircularDependencies):
        topological_sort(services, deps)


def it_ignores_dependencies_not_in_service_list():
    services = [FakeService('api')]
    deps = {'api': ['db']}
    result = topological_sort(services, deps)
    assert [s.name for s in result] == ['api']


def it_orders_dependencies_before_dependents_on_start():
    services = [FakeService('web'), FakeService('api'), FakeService('db')]
    deps = {'api': ['db'], 'web': ['api']}
    result = resolve_start_order(services, deps)
    names = [s.name for s in result]
    assert names.index('db') < names.index('api')
    assert names.index('api') < names.index('web')


def it_pulls_in_transitive_dependencies():
    services = [FakeService('web')]
    all_services = {'web': FakeService('web'), 'api': FakeService('api'), 'db': FakeService('db')}
    deps = {'web': ['api'], 'api': ['db']}
    result = resolve_start_order(services, deps, service_by_name_fn=lambda n: all_services[n])
    names = [s.name for s in result]
    assert 'db' in names
    assert 'api' in names
    assert names.index('db') < names.index('api')
    assert names.index('api') < names.index('web')


def it_raises_on_unknown_dependency():
    services = [FakeService('api')]
    deps = {'api': ['nonexistent']}

    def bad_lookup(name):
        raise KeyError(name)

    with pytest.raises(PgctlUserMessage, match="does not exist"):
        resolve_start_order(services, deps, service_by_name_fn=bad_lookup)


def it_raises_on_unknown_dependency_without_resolver():
    services = [FakeService('api')]
    deps = {'api': ['nonexistent']}
    with pytest.raises(PgctlUserMessage, match="does not exist"):
        resolve_start_order(services, deps)


def it_raises_on_nonexistent_service_dependency():
    """When a dependency references a service that doesn't exist as a directory
    in the playground, the resolver should raise a clear error message."""
    services = [FakeService('api')]
    deps = {'api': ['cache']}

    def resolver_that_checks_path(name):
        # Simulate what service_by_name does: raise when the path doesn't exist
        raise KeyError(f"No such service: '{name}'")

    with pytest.raises(PgctlUserMessage, match=r"Service 'api' depends on 'cache', but 'cache' does not exist"):
        resolve_start_order(services, deps, service_by_name_fn=resolver_that_checks_path)
