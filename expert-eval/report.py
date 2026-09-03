#!/usr/bin/env python3
"""Generate a meeting-friendly report for one expert-eval run."""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics


PRODUCT_LABELS = {
    "claude": "Claude Code + Sonnet",
    "corti": "OpenCode + Corti S1",
    "glm": "OpenCode + GLM 5.2",
}


def load_rows(run_dir: pathlib.Path) -> list[dict]:
    path = run_dir / "results.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def generate(run_dir: pathlib.Path) -> str:
    rows = load_rows(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    providers = sorted({row["provider"] for row in rows})
    lines = [
        "# Corti expert evaluation report",
        "",
        f"Run: `{manifest['run_id']}`  ",
        f"Suite: `{manifest.get('suite_version', 'v1')}`  ",
        f"Random seed: `{manifest['seed']}`  ",
        f"Attempts per task: `{manifest['repeat']}`",
        "",
        "## Summary",
        "",
        "| Agent product | Model | Passes / valid | Pass rate | Errors | Median successful attempt | Mean suite time |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for provider in providers:
        subset = [row for row in rows if row["provider"] == provider]
        valid = [row for row in subset if row["status"] in {"PASS", "FAIL", "TIMEOUT"}]
        passed = sum(row["status"] == "PASS" for row in valid)
        errors = sum(row["status"] not in {"PASS", "FAIL"} for row in subset)
        successful_times = [
            row["total_wall_seconds"] if "total_wall_seconds" in row else row["wall_seconds"]
            for row in subset if row["status"] == "PASS"
        ]
        rate = f"{100 * passed / len(valid):.1f}%" if valid else "n/a"
        median = f"{statistics.median(successful_times):.1f}s" if successful_times else "n/a"
        elapsed_times = [
            row["total_wall_seconds"] if "total_wall_seconds" in row else row["wall_seconds"]
            for row in subset
        ]
        repeat = manifest["repeat"]
        suite_time = f"{sum(elapsed_times) / repeat / 60:.1f} min"
        model = next(row["model"] for row in subset)
        label = PRODUCT_LABELS.get(provider, provider)
        lines.append(
            f"| {label} | `{model}` | {passed}/{len(valid)} | {rate} | "
            f"{errors} | {median} | {suite_time} |"
        )

    lines += [
        "",
        "Errors include infrastructure, CLI, and harness errors; they are excluded from the pass-rate denominator. Timeouts count as unsuccessful valid attempts because the common time budget is part of agent performance. Mean suite time is total end-to-end wall time divided by the configured repeat count.",
    ]
    lines += [
        "",
        "## Per attempt",
        "",
        "| Task | Attempt | Agent | Status | Time | Fixture unchanged |",
        "|---|---:|---|---|---:|---:|",
    ]
    for row in sorted(rows, key=lambda item: (item["task"], item["attempt"], item["provider"])):
        lines.append(
            f"| {row['task']} | {row['attempt']} | {row['provider']} | {row['status']} | "
            f"{(row['total_wall_seconds'] if 'total_wall_seconds' in row else row['wall_seconds']):.1f}s | "
            f"{'yes' if row['fixture_unchanged'] else 'NO'} |"
        )

    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- OpenCode+Corti versus OpenCode+GLM shares an agent scaffold; Claude Code+Sonnet is a product-level comparison.",
        "- Do not interpret infrastructure errors as coding failures.",
        "- Inspect per-task patches and logs before explaining why an agent won or lost.",
        "- This pilot is intended for qualitative diagnosis; it is not a statistically powered leaderboard.",
        "- Cost is omitted unless both CLIs expose comparable, complete accounting.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=pathlib.Path)
    args = parser.parse_args()
    report = generate(args.run_dir.resolve())
    (args.run_dir / "REPORT.md").write_text(report)
    print(report.split("## Per attempt", 1)[0].strip())


if __name__ == "__main__":
    main()
