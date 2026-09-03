import copy
import sys

sys.path.insert(0, sys.argv[1])
from dependency_plan import DependencyCycleError, UnknownDependencyError, build_plan


graph = {
    "release": {"package", "test"},
    "test": {"compile"},
    "package": {"compile"},
    "compile": set(),
    "announce": set(),
}
before = copy.deepcopy(graph)
assert build_plan(graph) == ["announce", "compile", "package", "test", "release"]
assert graph == before
assert build_plan({}) == []

try: build_plan({"ship": {"missing"}})
except UnknownDependencyError as exc:
    assert "ship" in str(exc) and "missing" in str(exc)
else: raise AssertionError("unknown dependency accepted")

cycles = [
    ({"a": {"a"}}, {"a"}),
    ({"a": {"b"}, "b": {"c"}, "c": {"a"}, "free": set()}, {"a", "b", "c"}),
    ({"a": {"b"}, "b": {"a"}, "c": {"d"}, "d": {"c"}}, {"a", "b", "c", "d"}),
]
for cyclic_graph, names in cycles:
    try: build_plan(cyclic_graph)
    except DependencyCycleError as exc:
        assert all(name in str(exc) for name in names), (cyclic_graph, exc)
    else: raise AssertionError(f"cycle accepted: {cyclic_graph}")
print("PASS")
