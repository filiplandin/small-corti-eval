import heapq


class UnknownDependencyError(ValueError):
    pass


class DependencyCycleError(ValueError):
    pass


def build_plan(graph):
    dependencies = {task: set(values) for task, values in graph.items()}
    for task, values in dependencies.items():
        for dependency in values:
            if dependency not in dependencies:
                raise UnknownDependencyError(f"{task} depends on unknown task {dependency}")

    dependants = {task: set() for task in dependencies}
    indegree = {task: len(values) for task, values in dependencies.items()}
    for task, values in dependencies.items():
        for dependency in values:
            dependants[dependency].add(task)

    ready = [task for task, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    result = []
    while ready:
        task = heapq.heappop(ready)
        result.append(task)
        for dependant in sorted(dependants[task]):
            indegree[dependant] -= 1
            if indegree[dependant] == 0:
                heapq.heappush(ready, dependant)

    if len(result) != len(dependencies):
        cyclic = _cyclic_nodes(dependencies)
        raise DependencyCycleError("cycle involving: " + ", ".join(sorted(cyclic)))
    return result


def _cyclic_nodes(graph):
    cyclic = set()
    for start in graph:
        stack = [(start, iter(graph[start]))]
        path = [start]
        positions = {start: 0}
        while stack:
            node, children = stack[-1]
            try:
                child = next(children)
            except StopIteration:
                stack.pop(); positions.pop(node, None); path.pop()
                continue
            if child in positions:
                cyclic.update(path[positions[child]:])
            elif child not in positions:
                positions[child] = len(path); path.append(child)
                stack.append((child, iter(graph[child])))
    return cyclic
