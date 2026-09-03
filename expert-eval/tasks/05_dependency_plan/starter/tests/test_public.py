import unittest

from dependency_plan import DependencyCycleError, UnknownDependencyError, build_plan


class DependencyTests(unittest.TestCase):
    def test_deterministic_topological_order(self):
        graph = {
            "deploy": {"test", "build"},
            "test": {"build"},
            "build": set(),
            "docs": set(),
        }
        self.assertEqual(build_plan(graph), ["build", "docs", "test", "deploy"])

    def test_unknown_dependency(self):
        with self.assertRaises(UnknownDependencyError):
            build_plan({"build": {"compile"}})

    def test_cycle(self):
        with self.assertRaises(DependencyCycleError):
            build_plan({"a": {"b"}, "b": {"a"}})


if __name__ == "__main__":
    unittest.main()
