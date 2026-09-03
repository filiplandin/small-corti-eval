class UnknownDependencyError(ValueError):
    pass


class DependencyCycleError(ValueError):
    pass


def build_plan(graph):
    visited = set()
    result = []

    def visit(task):
        if task in visited:
            return
        visited.add(task)
        for dependency in graph.get(task, ()):
            visit(dependency)
        result.append(task)

    for task in graph:
        visit(task)
    return result
