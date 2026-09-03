#!/usr/bin/env python3
"""Summarize usage reported in saved coding-agent CLI logs."""
from __future__ import annotations

import argparse
import json
import pathlib
from collections import defaultdict
from typing import Any


PRODUCT_LABELS = {
    "claude": "Claude Code + Sonnet",
    "corti": "OpenCode + Corti S1",
    "glm": "OpenCode + GLM 5.2",
}


def json_lines(path: pathlib.Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {path}:{line_number}: {exc}") from exc
        if isinstance(value, dict):
            records.append(value)
    return records


def log_usage(provider: str, path: pathlib.Path) -> dict[str, float | int]:
    records = json_lines(path)
    if provider == "claude":
        result_records = [record for record in records if isinstance(record.get("usage"), dict)]
        if not result_records:
            raise ValueError(f"Claude usage object not found in {path}")
        output = sum(int(record["usage"].get("output_tokens", 0)) for record in result_records)
        thinking = sum(
            int(record["usage"].get("output_tokens_details", {}).get("thinking_tokens", 0))
            for record in result_records
        )
        return {
            "output_tokens": output,
            "reasoning_tokens": thinking,
            # Claude reports thinking as a subset of output_tokens.
            "generated_tokens": output,
            "cost_usd": sum(float(record.get("total_cost_usd", 0)) for record in result_records),
        }

    steps = [record for record in records if record.get("type") == "step_finish"]
    if not steps:
        raise ValueError(f"OpenCode step usage not found in {path}")
    output = sum(int(step.get("part", {}).get("tokens", {}).get("output", 0)) for step in steps)
    reasoning = sum(int(step.get("part", {}).get("tokens", {}).get("reasoning", 0)) for step in steps)
    return {
        "output_tokens": output,
        "reasoning_tokens": reasoning,
        # OpenCode exposes reasoning as a separate counter.
        "generated_tokens": output + reasoning,
        "cost_usd": sum(float(step.get("part", {}).get("cost", 0)) for step in steps),
    }


def summarize(run_dirs: list[pathlib.Path]) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "attempts": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "generated_tokens": 0,
            "cost_usd": 0.0,
        }
    )
    seen: set[pathlib.Path] = set()
    for run_dir in run_dirs:
        result_path = run_dir / "results.jsonl"
        if not result_path.is_file():
            raise ValueError(f"results file not found: {result_path}")
        for row in json_lines(result_path):
            provider = row["provider"]
            attempt_dir = (
                run_dir / "runs" / provider / row["task"]
                / f"attempt-{int(row['attempt']):02d}"
            )
            log_path = (attempt_dir / "agent.log").resolve()
            if log_path in seen:
                raise ValueError(f"duplicate attempt log: {log_path}")
            seen.add(log_path)
            if not log_path.is_file():
                raise ValueError(f"agent log not found: {log_path}")
            usage = log_usage(provider, log_path)
            totals[provider]["attempts"] += 1
            for field in ("output_tokens", "reasoning_tokens", "generated_tokens", "cost_usd"):
                totals[provider][field] += usage[field]

    return [
        {
            "provider": provider,
            "product": PRODUCT_LABELS.get(provider, provider),
            **totals[provider],
        }
        for provider in sorted(totals)
    ]


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Product | Attempts | Reported output | Reasoning / thinking | Generated incl. reasoning | Logged cost |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['product']} | {row['attempts']:,} | {row['output_tokens']:,} | "
            f"{row['reasoning_tokens']:,} | {row['generated_tokens']:,} | "
            f"${row['cost_usd']:.2f} |"
        )
    indexed = {row["provider"]: row for row in rows}
    if indexed.get("corti", {}).get("output_tokens") and indexed.get("claude", {}).get("output_tokens"):
        ratio = indexed["corti"]["output_tokens"] / indexed["claude"]["output_tokens"]
        lines += [
            "",
            f"Corti / Claude reported-output ratio: **{ratio:.2f}×**",
        ]
    lines += [
        "",
        "Usage comes from provider CLI logs. Claude thinking tokens are included in its output-token total; OpenCode reports reasoning separately. Token and cost schemas are not guaranteed to be billing-equivalent across providers.",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dirs", nargs="+", type=pathlib.Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()
    rows = summarize([path.resolve() for path in args.run_dirs])
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(render_markdown(rows))


if __name__ == "__main__":
    main()
