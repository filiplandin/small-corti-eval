#!/usr/bin/env python3
"""Run the Corti expert evaluation in isolated temporary workspaces."""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import pathlib
import platform
import random
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent
TASKS = ROOT / "tasks"
RESULTS = ROOT / "results"
SUITE_VERSION = "v2.1"
DEFAULT_MODELS = {
    "corti": "corti/corti-s1",
    "glm": "opencode/glm-5.2",
    "claude": "claude-sonnet-5",
}
INFRA_PATTERNS = (
    "429",
    "rate limit",
    "rate-limit",
    "rate_limited",
    "overloaded",
    "temporarily unavailable",
    "apierror",
    "authentication",
    "unauthorized",
    "provider returned error",
    "connection error",
)
PROMPT_SUFFIX = """

Work only in the current repository. Do not inspect parent directories or any
other benchmark runs. Implement the requested behavior, preserve public APIs,
and run the included public tests before finishing. Do not use network access.
""".strip()


@dataclass(frozen=True)
class Job:
    provider: str
    task: str
    attempt: int


def job_key(value: Job | dict[str, Any]) -> tuple[str, str, int]:
    if isinstance(value, Job):
        return value.provider, value.task, value.attempt
    return value["provider"], value["task"], int(value["attempt"])


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def task_dirs() -> list[pathlib.Path]:
    return sorted(p for p in TASKS.iterdir() if p.is_dir())


def file_digest(root: pathlib.Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if (
            "__pycache__" in path.parts
            or path.suffix == ".pyc"
            or path.name == ".DS_Store"
        ):
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def write_json_atomic(path: pathlib.Path, payload: Any, *, json_lines: bool = False) -> None:
    """Durably replace a small JSON checkpoint without leaving a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if json_lines:
        text = "".join(json.dumps(item) + "\n" for item in payload)
    else:
        text = json.dumps(payload, indent=2) + "\n"
    with temporary.open("w") as output:
        output.write(text)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)
    try:
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError:
        # Some filesystems do not support syncing directory handles.
        pass


def result_checkpoint_path(run_dir: pathlib.Path, job: Job) -> pathlib.Path:
    return (
        run_dir / "runs" / job.provider / job.task
        / f"attempt-{job.attempt:02d}" / "result.json"
    )


def load_completed_results(run_dir: pathlib.Path, jobs: list[Job]) -> list[dict]:
    """Load aggregate results and recover any completed per-attempt checkpoint."""
    expected = {job_key(job) for job in jobs}
    by_key: dict[tuple[str, str, int], dict] = {}
    result_file = run_dir / "results.jsonl"
    if result_file.exists():
        for line_number, line in enumerate(result_file.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                key = job_key(row)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"invalid checkpoint at {result_file}:{line_number}: {exc}"
                ) from exc
            if key not in expected:
                raise ValueError(f"checkpoint contains unexpected job: {key}")
            if key in by_key:
                raise ValueError(f"checkpoint contains duplicate job: {key}")
            by_key[key] = row

    for job in jobs:
        checkpoint = result_checkpoint_path(run_dir, job)
        if not checkpoint.exists():
            continue
        try:
            row = json.loads(checkpoint.read_text())
            key = job_key(row)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid attempt checkpoint at {checkpoint}: {exc}") from exc
        expected_key = job_key(job)
        if key != expected_key:
            raise ValueError(
                f"attempt checkpoint {checkpoint} identifies {key}, expected {expected_key}"
            )
        if key in by_key and by_key[key] != row:
            raise ValueError(f"conflicting checkpoints for job: {key}")
        by_key[key] = row

    return [by_key[job_key(job)] for job in jobs if job_key(job) in by_key]


def validate_resume_manifest(manifest: dict, fixture_digest: str) -> None:
    required = {
        "run_id", "seed", "repeat", "timeout_seconds", "infra_retries",
        "providers", "models", "tasks", "fixture_digest",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        raise ValueError(f"resume manifest is missing: {', '.join(missing)}")
    if manifest["fixture_digest"] != fixture_digest:
        raise ValueError(
            "task fixtures changed since this run started; restore them or start a new run"
        )


def command(provider: str, workspace: pathlib.Path, prompt: str, model: str) -> list[str]:
    if provider in {"corti", "glm"}:
        return [
            "opencode", "run", "--pure", "--auto", "--dir", str(workspace),
            "--model", model, "--format", "json", prompt,
        ]
    if provider == "claude":
        return [
            "claude", "-p", prompt, "--model", model,
            "--output-format", "json", "--no-session-persistence",
            "--safe-mode", "--disable-slash-commands",
            "--dangerously-skip-permissions",
        ]
    raise ValueError(f"unknown provider: {provider}")


def version_output(command_: list[str]) -> str | None:
    try:
        completed = subprocess.run(command_, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = (completed.stdout + completed.stderr).strip()
    return output.splitlines()[0] if output else None


def classify_nonzero(raw: str) -> str:
    lowered = raw.lower()
    return "INFRA_ERROR" if any(pattern in lowered for pattern in INFRA_PATTERNS) else "CLI_ERROR"


def grader(task_dir: pathlib.Path, workspace: pathlib.Path) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            ["python3", str(task_dir / "grader.py"), str(workspace)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "GRADER_TIMEOUT after 60 seconds"
    except OSError as exc:
        return False, f"GRADER_ERROR: {exc}"
    return completed.returncode == 0, (completed.stdout + completed.stderr).strip()


def workspace_diff(before: pathlib.Path, after: pathlib.Path) -> str:
    relative_paths = {
        p.relative_to(before) for p in before.rglob("*") if p.is_file()
    } | {
        p.relative_to(after) for p in after.rglob("*") if p.is_file()
    }
    chunks: list[str] = []
    for relative in sorted(relative_paths):
        if "__pycache__" in relative.parts or relative.suffix == ".pyc":
            continue
        old_path, new_path = before / relative, after / relative
        try:
            old = old_path.read_text().splitlines(keepends=True) if old_path.exists() else []
            new = new_path.read_text().splitlines(keepends=True) if new_path.exists() else []
        except UnicodeDecodeError:
            if old_path.exists() and new_path.exists() and old_path.read_bytes() == new_path.read_bytes():
                continue
            chunks.append(f"Binary file changed: {relative}\n")
            continue
        if old != new:
            chunks.extend(difflib.unified_diff(
                old, new,
                fromfile=f"a/{relative.as_posix()}",
                tofile=f"b/{relative.as_posix()}",
            ))
    return "".join(chunks)


def prepare_workspace(task_dir: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    workspace = destination / "workspace"
    shutil.copytree(task_dir / "starter", workspace)
    shutil.copy2(task_dir / "TASK.md", workspace / "TASK.md")
    return workspace


def run_process(cmd: list[str], workspace: pathlib.Path, timeout: int) -> tuple[int | None, str, float, str]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            cmd,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        raw = (completed.stdout + "\n" + completed.stderr).strip()
        status = "OK" if completed.returncode == 0 else classify_nonzero(raw)
        return completed.returncode, raw, time.perf_counter() - started, status
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return None, (stdout + "\n" + stderr + "\nTIMEOUT").strip(), time.perf_counter() - started, "TIMEOUT"
    except OSError as exc:
        return None, str(exc), time.perf_counter() - started, "INFRA_ERROR"


def run_job(
    job: Job,
    run_dir: pathlib.Path,
    models: dict[str, str],
    timeout: int,
    infra_retries: int,
    dry_run: bool,
) -> dict:
    task_dir = TASKS / job.task
    fixture_before = file_digest(task_dir)
    prompt = (task_dir / "TASK.md").read_text().strip() + "\n\n" + PROMPT_SUFFIX
    attempt_dir = run_dir / "runs" / job.provider / job.task / f"attempt-{job.attempt:02d}"
    if attempt_dir.exists():
        if (attempt_dir / "result.json").exists():
            raise ValueError(f"refusing to overwrite completed attempt: {attempt_dir}")
        interrupted_at = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archived = attempt_dir.with_name(f"{attempt_dir.name}.interrupted-{interrupted_at}")
        counter = 1
        while archived.exists():
            archived = attempt_dir.with_name(
                f"{attempt_dir.name}.interrupted-{interrupted_at}-{counter}"
            )
            counter += 1
        attempt_dir.rename(archived)
    attempt_dir.mkdir(parents=True)
    final_result: dict | None = None
    total_elapsed = 0.0

    for transport_try in range(1, infra_retries + 2):
        with tempfile.TemporaryDirectory(prefix=f"corti-expert-{job.provider}-{job.task}-") as temp:
            temp_path = pathlib.Path(temp)
            workspace = prepare_workspace(task_dir, temp_path)
            baseline = temp_path / "baseline"
            shutil.copytree(workspace, baseline)
            cmd = command(job.provider, workspace, prompt, models[job.provider])

            if dry_run:
                return {
                    **asdict(job),
                    "timestamp": utc_now(),
                    "model": models[job.provider],
                    "status": "DRY_RUN",
                    "command": cmd,
                }

            returncode, raw, elapsed, process_status = run_process(cmd, workspace, timeout)
            total_elapsed += elapsed
            fixture_after = file_digest(task_dir)
            fixture_unchanged = fixture_before == fixture_after
            grader_ok, grader_output = grader(task_dir, workspace)

            if not fixture_unchanged:
                status = "HARNESS_ERROR"
            elif process_status != "OK":
                status = process_status
            else:
                status = "PASS" if grader_ok else "FAIL"

            final_result = {
                **asdict(job),
                "timestamp": utc_now(),
                "model": models[job.provider],
                "status": status,
                "success": status == "PASS",
                "cli_ok": process_status == "OK",
                "grader_ok": grader_ok,
                "fixture_unchanged": fixture_unchanged,
                "returncode": returncode,
                "wall_seconds": round(elapsed, 2),
                "total_wall_seconds": round(total_elapsed, 2),
                "transport_try": transport_try,
                "command": cmd,
                "grader_output": grader_output[-4000:],
            }

            if status == "INFRA_ERROR" and transport_try <= infra_retries:
                (attempt_dir / f"transport-{transport_try:02d}.log").write_text(raw)
                time.sleep(min(2 ** transport_try, 10))
                continue

            (attempt_dir / "agent.log").write_text(raw)
            (attempt_dir / "patch.diff").write_text(workspace_diff(baseline, workspace))
            snapshot = attempt_dir / "workspace"
            if snapshot.exists():
                shutil.rmtree(snapshot)
            shutil.copytree(workspace, snapshot, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            write_json_atomic(attempt_dir / "result.json", final_result)
            break

    assert final_result is not None
    return final_result


def build_jobs(providers: list[str], tasks: list[str], repeat: int, seed: int) -> list[Job]:
    jobs = [
        Job(provider, task, attempt)
        for task in tasks
        for attempt in range(1, repeat + 1)
        for provider in providers
    ]
    random.Random(seed).shuffle(jobs)
    return jobs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "provider", nargs="?",
        choices=["corti", "glm", "claude", "both", "all"],
    )
    parser.add_argument("--task", action="append", help="Task name; repeat to select several")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--infra-retries", type=int, default=2)
    parser.add_argument("--corti-model", default=DEFAULT_MODELS["corti"])
    parser.add_argument("--glm-model", default=DEFAULT_MODELS["glm"])
    parser.add_argument("--claude-model", default=DEFAULT_MODELS["claude"])
    parser.add_argument("--dry-run", action="store_true", help="Print planned commands without model calls")
    parser.add_argument(
        "--resume", type=pathlib.Path,
        help="Resume an existing results directory using its frozen manifest",
    )
    args = parser.parse_args()

    if args.repeat < 1 or args.timeout < 1 or args.infra_retries < 0:
        parser.error("repeat and timeout must be positive; infra-retries must be non-negative")

    available = [p.name for p in task_dirs()]

    if args.resume:
        if args.provider is not None:
            parser.error("do not pass a provider with --resume; the manifest freezes it")
        if args.dry_run:
            parser.error("--dry-run cannot be combined with --resume")
        run_dir = args.resume.expanduser().resolve()
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.is_file():
            parser.error(f"resume manifest not found: {manifest_path}")
        try:
            manifest = json.loads(manifest_path.read_text())
            validate_resume_manifest(manifest, file_digest(TASKS))
        except (json.JSONDecodeError, ValueError) as exc:
            parser.error(str(exc))
        providers = list(manifest["providers"])
        models = dict(manifest["models"])
        selected = list(manifest["tasks"])
        jobs = build_jobs(providers, selected, manifest["repeat"], manifest["seed"])
        timeout = int(manifest["timeout_seconds"])
        infra_retries = int(manifest["infra_retries"])
        try:
            results = load_completed_results(run_dir, jobs)
        except ValueError as exc:
            parser.error(str(exc))
        write_json_atomic(run_dir / "results.jsonl", results, json_lines=True)
    else:
        if args.provider is None:
            parser.error("provider is required unless --resume is used")
        selected = args.task or available
        unknown = sorted(set(selected) - set(available))
        if unknown:
            parser.error(f"unknown tasks: {', '.join(unknown)}")
        if args.provider == "both":
            providers = ["corti", "claude"]
        elif args.provider == "all":
            providers = ["corti", "glm", "claude"]
        else:
            providers = [args.provider]
        models = {
            "corti": args.corti_model,
            "glm": args.glm_model,
            "claude": args.claude_model,
        }
        jobs = build_jobs(providers, selected, args.repeat, args.seed)
        timeout = args.timeout
        infra_retries = args.infra_retries
        results = []

    if args.dry_run:
        with tempfile.TemporaryDirectory(prefix="corti-expert-dry-run-") as temp:
            for job in jobs:
                task_dir = TASKS / job.task
                workspace = prepare_workspace(task_dir, pathlib.Path(temp) / f"{job.provider}-{job.task}-{job.attempt}")
                prompt = (task_dir / "TASK.md").read_text().strip() + "\n\n" + PROMPT_SUFFIX
                print(json.dumps({**asdict(job), "command": command(job.provider, workspace, prompt, models[job.provider])}))
        return

    if not args.resume:
        run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = RESULTS / run_id
        run_dir.mkdir(parents=True)
        manifest = {
            "run_id": run_id,
            "suite_version": SUITE_VERSION,
            "created_at": utc_now(),
            "seed": args.seed,
            "repeat": args.repeat,
            "timeout_seconds": timeout,
            "infra_retries": infra_retries,
            "providers": providers,
            "models": {provider: models[provider] for provider in providers},
            "tasks": selected,
            "prompt_suffix": PROMPT_SUFFIX,
            "fixture_digest": file_digest(TASKS),
            "environment": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "opencode": version_output(["opencode", "--version"]),
                "claude": version_output(["claude", "--version"]),
            },
        }
        write_json_atomic(run_dir / "manifest.json", manifest)

    result_file = run_dir / "results.jsonl"
    completed = {job_key(row) for row in results}
    print(f"Run directory: {run_dir}", flush=True)
    if args.resume:
        print(f"Recovered {len(completed)}/{len(jobs)} completed jobs", flush=True)
    try:
        for index, job in enumerate(jobs, 1):
            if job_key(job) in completed:
                print(
                    f"[{index}/{len(jobs)}] {job.provider} {job.task} "
                    f"attempt {job.attempt} SKIP (checkpoint)",
                    flush=True,
                )
                continue
            print(f"[{index}/{len(jobs)}] {job.provider} {job.task} attempt {job.attempt}", flush=True)
            result = run_job(job, run_dir, models, timeout, infra_retries, False)
            results.append(result)
            completed.add(job_key(result))
            ordered_results = [
                next(row for row in results if job_key(row) == job_key(planned))
                for planned in jobs if job_key(planned) in completed
            ]
            write_json_atomic(result_file, ordered_results, json_lines=True)
            print(f"  {result['status']} ({result['total_wall_seconds']:.1f}s)", flush=True)
    except KeyboardInterrupt:
        if results:
            subprocess.run(["python3", str(ROOT / "report.py"), str(run_dir)], check=False)
        print(f"\nInterrupted. Resume with:\npython3 {ROOT / 'run.py'} --resume {run_dir}")
        raise SystemExit(130)

    subprocess.run(["python3", str(ROOT / "report.py"), str(run_dir)], check=True)
    print(f"\nReport: {run_dir / 'REPORT.md'}")


if __name__ == "__main__":
    main()
