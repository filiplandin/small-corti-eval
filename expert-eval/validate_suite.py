#!/usr/bin/env python3
"""Validate that each starter fails and each private reference solution passes."""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
TASKS = ROOT / "tasks"


def overlay(source: pathlib.Path, destination: pathlib.Path) -> None:
    for path in source.rglob("*"):
        if path.is_file():
            target = destination / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def grade(task: pathlib.Path, workspace: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(task / "grader.py"), str(workspace)],
        capture_output=True,
        text=True,
        timeout=60,
    )


def public_tests(workspace: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=60,
    )


def main() -> None:
    failures: list[str] = []
    task_dirs = sorted(path for path in TASKS.iterdir() if path.is_dir())
    for task in task_dirs:
        required = [task / "TASK.md", task / "starter", task / "grader.py", task / "solution"]
        missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
        if missing:
            failures.append(f"{task.name}: missing {', '.join(missing)}")
            continue
        leaked = [name for name in ["grader.py", "solution"] if (task / "starter" / name).exists()]
        if leaked:
            failures.append(f"{task.name}: private artifacts leaked into starter: {', '.join(leaked)}")
            continue
        with tempfile.TemporaryDirectory(prefix=f"validate-{task.name}-") as temp:
            workspace = pathlib.Path(temp) / "workspace"
            shutil.copytree(task / "starter", workspace)
            starter = grade(task, workspace)
            overlay(task / "solution", workspace)
            solved = grade(task, workspace)
            public = public_tests(workspace)
            if starter.returncode == 0:
                failures.append(f"{task.name}: starter unexpectedly passes hidden grader")
            if solved.returncode != 0:
                output = (solved.stdout + solved.stderr).strip()
                failures.append(f"{task.name}: reference solution fails: {output[-1000:]}")
            if public.returncode != 0:
                output = (public.stdout + public.stderr).strip()
                failures.append(f"{task.name}: reference fails public tests: {output[-1000:]}")
        print(f"{task.name}: starter fails, reference and public tests pass")

    if failures:
        raise SystemExit("\n".join(failures))
    print(f"\nValidated {len(task_dirs)} tasks")


if __name__ == "__main__":
    main()
