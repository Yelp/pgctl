from .errors import CircularDependencies
from .errors import PgctlUserMessage


def topological_sort(services, dependency_map):
    """Sort services so that dependencies come before dependents.

    :param services: iterable of service objects (must have .name attribute)
    :param dependency_map: dict mapping service name -> list of service names it depends on
    :return: list of services in dependency order
    """
    service_by_name = {s.name: s for s in services}
    service_names = set(service_by_name.keys())

    adj = {name: [] for name in service_names}
    for name in service_names:
        for dep in dependency_map.get(name, ()):
            if dep in service_names:
                adj[dep].append(name)

    UNVISITED, IN_PROGRESS, DONE = 0, 1, 2
    state = {name: UNVISITED for name in service_names}
    order = []

    def visit(name):
        if state[name] == DONE:
            return
        if state[name] == IN_PROGRESS:
            raise CircularDependencies(
                f"Circular dependency detected involving service '{name}'"
            )
        state[name] = IN_PROGRESS
        for neighbor in adj[name]:
            visit(neighbor)
        state[name] = DONE
        order.append(name)

    for name in sorted(service_names):
        visit(name)

    order.reverse()
    return [service_by_name[name] for name in order]


def resolve_start_order(services, dependency_map, service_by_name_fn=None):
    """Return services ordered so dependencies start first.

    Also includes any transitive dependencies from dependency_map that are
    not already in the requested services list. If service_by_name_fn is
    provided, it will be called to resolve dependency names into Service
    objects. Unknown dependency names raise an error.

    :param services: list of Service objects explicitly requested
    :param dependency_map: dict mapping service name -> tuple of dependency names
    :param service_by_name_fn: callable(name) -> Service, for resolving deps not in services
    """
    service_by_name = {s.name: s for s in services}
    needed = set(service_by_name.keys())

    queue = list(needed)
    while queue:
        name = queue.pop()
        for dep in dependency_map.get(name, ()):
            if dep not in needed:
                if dep in service_by_name:
                    pass
                elif service_by_name_fn is not None:
                    try:
                        service_by_name[dep] = service_by_name_fn(dep)
                    except Exception:
                        raise PgctlUserMessage(
                            f"Service '{name}' depends on '{dep}', but '{dep}' does not exist"
                        )
                else:
                    raise PgctlUserMessage(
                        f"Service '{name}' depends on '{dep}', but '{dep}' does not exist"
                    )
                needed.add(dep)
                queue.append(dep)

    return topological_sort(
        [service_by_name[n] for n in needed],
        dependency_map,
    )
