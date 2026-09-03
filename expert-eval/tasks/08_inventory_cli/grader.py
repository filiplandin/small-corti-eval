import json
import os
import pathlib
import subprocess
import sys
import tempfile

workspace = pathlib.Path(sys.argv[1])
env = dict(os.environ, PYTHONPATH=str(workspace))


def run(db, *args):
    return subprocess.run(
        [sys.executable, "-m", "inventory", "--db", str(db), *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


with tempfile.TemporaryDirectory() as temp:
    db = pathlib.Path(temp) / "nested" / "inventory.json"
    result = run(db, "list")
    assert result.returncode == 0 and json.loads(result.stdout) == [] and not db.exists()

    for sku, quantity in [("B-2", "3"), ("A-1", "2"), ("B-2", "4")]:
        result = run(db, "add", sku, quantity)
        assert result.returncode == 0 and result.stdout.endswith("\n") and result.stderr == ""
    assert json.loads(run(db, "get", "B-2").stdout) == {"sku": "B-2", "quantity": 7}
    assert json.loads(run(db, "list").stdout) == [
        {"sku": "A-1", "quantity": 2}, {"sku": "B-2", "quantity": 7}
    ]

    before = db.read_bytes()
    invalid = [
        ("remove", "B-2", "8"),
        ("remove", "missing", "1"),
        ("add", "X", "0"),
        ("add", "X", "-1"),
        ("add", "X", "1.0"),
    ]
    for args in invalid:
        result = run(db, *args)
        assert result.returncode == 2 and result.stderr.strip() and db.read_bytes() == before

    result = run(db, "remove", "B-2", "7")
    assert result.returncode == 0 and json.loads(result.stdout)["quantity"] == 0
    assert "B-2" not in json.loads(db.read_text())

    corrupt = pathlib.Path(temp) / "corrupt.json"; corrupt.write_text("not json")
    before = corrupt.read_bytes(); result = run(corrupt, "add", "X", "1")
    assert result.returncode == 2 and corrupt.read_bytes() == before

    invalid_db = pathlib.Path(temp) / "invalid.json"
    for content in ["[]", '{"X":true}', '{"":1}', '{"X":-1}']:
        invalid_db.write_text(content); before = invalid_db.read_bytes()
        result = run(invalid_db, "list")
        assert result.returncode == 2 and invalid_db.read_bytes() == before
print("PASS")
