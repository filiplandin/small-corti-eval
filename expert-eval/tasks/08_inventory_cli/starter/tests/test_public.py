import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def run_cli(db, *args):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run(
        [sys.executable, "-m", "inventory", "--db", str(db), *args],
        capture_output=True,
        text=True,
        env=env,
    )


class InventoryCLITests(unittest.TestCase):
    def test_add_get_list_and_remove(self):
        with tempfile.TemporaryDirectory() as temp:
            db = pathlib.Path(temp) / "nested" / "inventory.json"
            self.assertFalse(db.parent.exists())
            self.assertEqual(run_cli(db, "add", "B", "3").returncode, 0)
            self.assertTrue(db.exists())
            self.assertEqual(json.loads(run_cli(db, "add", "A", "2").stdout)["quantity"], 2)
            self.assertEqual(json.loads(run_cli(db, "get", "B").stdout), {"sku": "B", "quantity": 3})
            self.assertEqual([row["sku"] for row in json.loads(run_cli(db, "list").stdout)], ["A", "B"])
            self.assertEqual(json.loads(run_cli(db, "remove", "B", "3").stdout)["quantity"], 0)

    def test_failed_remove_does_not_change_database(self):
        with tempfile.TemporaryDirectory() as temp:
            db = pathlib.Path(temp) / "inventory.json"
            run_cli(db, "add", "A", "2")
            before = db.read_bytes()
            result = run_cli(db, "remove", "A", "3")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(db.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
