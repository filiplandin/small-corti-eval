# Small Corti evaluation

A reproducible ten-task Python benchmark for comparing coding-agent products.
The harness currently supports:

- OpenCode with `corti/corti-s1`
- OpenCode with `opencode/glm-5.2`
- Claude Code with `claude-sonnet-5`

The suite is intentionally small, dependency-free, and designed for inspecting
task-level behavior rather than producing a general-purpose leaderboard.

## How it works

Each attempt runs in a fresh system temporary directory. The agent receives
only the task prompt, starter code, and public tests. The hidden grader and
reference solution remain outside the workspace.

The runner records the exact command and model, validates fixture integrity,
grades the final workspace, and checkpoints results atomically.

See [the technical walkthrough](expert-eval/WALKTHROUGH.md) for the task list,
workspace lifecycle, scoring states, and fairness controls.

## Repository layout

```text
expert-eval/
  tasks/           Task prompts, starter code, public tests, graders, solutions
  tests/           Harness regression tests
  run.py           Isolated and resumable benchmark runner
  report.py        Per-run Markdown report generator
  validate_suite.py
```

## Validate the suite

No provider credentials or model calls are required:

```bash
python3 expert-eval/validate_suite.py
python3 -m unittest discover -s expert-eval/tests -v
```

Validation requires every starter to fail its grader and every reference
solution to pass.

## Run the benchmark

Prerequisites:

- Python 3.11 or newer
- OpenCode configured for the selected Corti or GLM model
- Claude Code authenticated when running Claude

Run all three products twice:

```bash
python3 expert-eval/run.py all \
  --repeat 2 \
  --seed 20260903 \
  --timeout 900 \
  --infra-retries 2
```

Run one provider or task:

```bash
python3 expert-eval/run.py corti --repeat 1
python3 expert-eval/run.py corti --task 09_safe_zip --repeat 1
```

Pin a model explicitly:

```bash
python3 expert-eval/run.py corti \
  --corti-model corti/corti-s1-instant \
  --repeat 2
```

Results are written to `expert-eval/results/<run-id>/` and are intentionally
excluded from version control.

## Scope

This is an end-to-end product comparison. Corti and GLM share the OpenCode
scaffold; Claude Code has a different built-in scaffold and tools. The harness
makes no direct HTTP calls and relies on the installed CLIs for provider
configuration and authentication.

Suite `v2.1` accepts either `TypeError` or `ValueError` when tasks 9 and 10
reject invalid arguments. This is explicit in the prompts, public tests, and
hidden graders.

Publishing graders and reference solutions makes the tasks unsuitable as
secret future benchmark items. Use this repository for reproducibility and
technical review, and use new private tasks for contamination-sensitive runs.
