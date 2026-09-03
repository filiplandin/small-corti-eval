import unittest

from config_merge import DELETE, merge_config


class ConfigMergeTests(unittest.TestCase):
    def test_nested_merge_and_delete(self):
        base = {"db": {"host": "localhost", "port": 5432}, "debug": False}
        overlay = {"db": {"port": 6432}, "debug": DELETE}
        self.assertEqual(
            merge_config(base, overlay),
            {"db": {"host": "localhost", "port": 6432}},
        )

    def test_result_does_not_alias_inputs(self):
        base = {"items": [{"name": "a"}]}
        result = merge_config(base, {})
        result["items"][0]["name"] = "changed"
        self.assertEqual(base["items"][0]["name"], "a")


if __name__ == "__main__":
    unittest.main()
