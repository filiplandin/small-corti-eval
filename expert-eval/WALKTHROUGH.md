# Technical walkthrough

## 1. The exact experimental unit

One attempt consists of:

1. Choose one task, one provider, and one attempt number.
2. Create a new unpredictable system temporary directory.
3. Copy only `starter/`, its public tests, and `TASK.md` into that directory.
4. Invoke the provider with the exact task text and common suffix.
5. For Corti, pass the temporary workspace explicitly using OpenCode `--dir`.
6. Wait for the agent to exit or reach the common timeout.
7. Hash the original task fixture again to detect accidental writes.
8. Run the hidden grader against the temporary workspace.
9. Save the CLI log, final workspace, unified patch, and result metadata.

The job order is shuffled with a recorded seed. Every attempt gets a clean
workspace, including infrastructure retries.

## 2. How provider calls are made

The Python harness makes no direct HTTP requests. It launches installed CLIs
with `subprocess.run`, captures stdout/stderr, and enforces the same timeout.

OpenCode + Corti or GLM:

```text
opencode run --pure --auto --dir <workspace> \
  --model <model-id> --format json <prompt>
```

Claude Code + Sonnet:

```text
claude -p <prompt> --model <model-id> --output-format json \
  --no-session-persistence --safe-mode --disable-slash-commands \
  --dangerously-skip-permissions
```

## 3. Scoring states

| Status | Meaning | Included in coding pass-rate denominator? |
|---|---|---:|
| `PASS` | CLI exited successfully and hidden grader passed | Yes |
| `FAIL` | CLI exited successfully but hidden grader failed | Yes |
| `INFRA_ERROR` | Provider, authentication, network, or rate-limit failure | No |
| `CLI_ERROR` | Agent CLI exited abnormally without a recognized infrastructure cause | No; inspect separately |
| `TIMEOUT` | Common wall-time limit was reached | Yes, as an unsuccessful attempt |
| `HARNESS_ERROR` | Evaluation fixture changed or another invariant failed | No; invalidate the attempt |

A verifier pass can never override an unsuccessful CLI status. This specifically
prevents the false GLM passes seen in the first benchmark.

## 4. The ten tasks

### 01 — TTL/LRU cache repair

**Scenario:** A bounded in-memory cache combines time-based expiry with
least-recently-used eviction.

**Bugs in the starter:** expiry uses `>` instead of `>=`, reads do not update
recency, expired entries remain counted, constructor inputs are not validated,
and updates do not have fully specified recency semantics.

**What it tests:** stateful reasoning, boundary conditions, injected clocks,
and interactions between two policies. It is harder than a single arithmetic
bug because individually reasonable fixes can conflict.

**What to inspect in a run:** Did the agent introduce one coherent expiry
helper? Does it purge stale entries before capacity eviction? Did it preserve
`KeyError(key)`? Does it reject a boolean capacity explicitly?

### 02 — Circuit-breaker state machine

**Scenario:** Calls to an unhealthy dependency should be blocked until a
recovery probe is allowed.

**Starter state:** the public class exists but `call` is unimplemented.

**What it tests:** translating prose into a state machine, consecutive failure
semantics, timing boundaries, exception propagation, and recovery behavior.

**What to inspect:** How did the agent represent `closed`, `open`, and
`half-open`? Does a failed probe restart the timeout? Does a normal success
reset prior failures? Does the `state` property become `"half-open"` as soon as
the recovery timeout elapses, before a probe is invoked?

### 03 — Atomic account transfers

**Scenario:** An ordered batch of transfers must either commit completely or
leave all balances unchanged.

**Bug:** the starter mutates balances incrementally, so a later error leaves a
partial transaction.

**What it tests:** multi-step invariants, staged changes, validation ordering,
numeric edge cases, object identity, and rollback-by-design.

**What to inspect:** A strong solution validates against a staged copy and only
commits at the end. Check that the original mapping object is returned and that
booleans, infinity, and NaN are rejected.

### 04 — NDJSON event ingestion

**Scenario:** An event stream must be validated, deduplicated, and sorted.

**Bug:** the starter merely calls `json.loads` and returns input order.

**What it tests:** structured parsing, useful error attribution, timezone-aware
comparison, deduplication rules, stable tie-breaking, and preservation of
unknown fields.

**What to inspect:** Does the agent compare absolute instants rather than raw
timestamp strings? Does an equal timestamp keep the later occurrence? Do error
messages retain the one-based line number?

### 05 — Deterministic dependency planning

**Scenario:** Build a stable execution plan from task dependencies.

**Bugs:** the starter silently invents unknown dependency nodes, misses cycles,
and depends on mapping/set iteration order.

**What it tests:** graph algorithms, error semantics, deterministic output, and
cycle diagnostics.

**What to inspect:** Kahn's algorithm with a min-heap is a natural solution for
lexicographically smallest availability. Cycle reporting needs more than simply
listing all nodes left after Kahn's algorithm, because nodes downstream of a
cycle are blocked but do not themselves participate in one.

### 06 — Immutable layered configuration merge

**Scenario:** Merge base configuration with an overlay, including recursive
deletion, without sharing mutable state.

**Bug:** the starter performs only a shallow `dict.update`.

**What it tests:** recursive data transformation, mapping abstractions, sentinel
identity, deep copying, and non-mutation guarantees.

**What to inspect:** Does the solution test `value is DELETE`, rather than
equality? Are lists replaced rather than concatenated? Can mutating the result
change either input?

### 07 — Bounded async worker pool

**Scenario:** Map an async function over inputs with a concurrency limit.

**Bug:** the starter starts all coroutines at once and does no cleanup.

**What it tests:** asynchronous concurrency, ordered results, semaphores,
cancellation, exception preservation, and cleanup of background tasks.

**What to inspect:** A semaphore alone is insufficient if an exception leaves
other tasks running. Strong solutions cancel unfinished tasks and await them
with `return_exceptions=True` before re-raising.

### 08 — Persistent inventory CLI

**Scenario:** A small command-line application maintains JSON inventory across
processes.

**Starter state:** storage is unsafe and the CLI is unimplemented.

**What it tests:** repository navigation across modules, CLI design, subprocess
behavior, persistent state, validation, failure atomicity, JSON contracts, and
atomic file replacement.

**What to inspect:** Does `list` avoid creating a database? Are malformed files
preserved after errors? Are writes done through a sibling temporary file and
`os.replace`? Does a mutation create missing parent directories? Are stdout,
stderr, and exit codes disciplined?

### 09 — Safe ZIP extraction

**Scenario:** An application must unpack an untrusted ZIP without allowing
filesystem escape, symbolic links, conflicting paths, oversized payloads, or
partial output after validation failures.

**Starter state:** the public exception and function exist but extraction is
unimplemented.

**What it tests:** security-boundary reasoning, archive metadata, cross-platform
path semantics, complete preflight validation, streaming I/O, and cleanup.

**What to inspect:** Does the agent validate every member before creating the
destination? Does it reject both traversal and file/directory conflicts? Does
it avoid `extractall` and remove partial output if extraction itself fails?

### 10 — HTTP retry policy

**Scenario:** A synchronous client needs bounded retries without accidentally
replaying unsafe operations.

**Starter state:** response and exception types exist but policy execution is
unimplemented.

**What it tests:** idempotency, precise failure classification, retry budgets,
case-insensitive headers, exponential backoff, exception causality, and
side-effect discipline.

**What to inspect:** Does the agent avoid retrying an unsafe POST without an
idempotency key? Does it sleep only between attempts? Does transport exhaustion
preserve the final exception as the cause?

## 5. Difficulty and coverage map

| Capability | Tasks |
|---|---|
| Local bug repair | 01, 03, 05 |
| Implementation from specification | 02, 07, 08 |
| Stateful behavior | 01, 02, 08 |
| Multi-file/repository navigation | 03, 08 |
| Algorithms | 05, 07 |
| Parsing and validation | 04, 06, 08 |
| Security boundaries | 09 |
| Retry and idempotency policy | 10 |
| Failure atomicity and cleanup | 03, 07, 08, 09 |
| Deterministic edge cases | All tasks |

The suite is Python-only and dependency-free on purpose: installation and
ecosystem variance should not dominate this pilot. A later expansion should add
TypeScript, a real existing repository, build failures, and dependency/API
migrations.

## 6. Fairness controls

All products receive the same task text, public files, timeout, and fresh
workspace. Jobs run sequentially in a reproducibly shuffled order. Corti and
GLM also share the same OpenCode command structure.

The products do not receive identical internal scaffolds: OpenCode and Claude
Code have different system prompts and tools. Results therefore compare
agent products, not isolated foundation models. Filesystem isolation prevents
accidental grader leakage but is not a security boundary against a malicious
process.

## 7. Inspecting results

After a run, open:

```text
expert-eval/results/<run-id>/
├── REPORT.md
├── manifest.json
├── results.jsonl
└── runs/<provider>/<task>/attempt-XX/
    ├── agent.log
    ├── patch.diff
    ├── result.json
    └── workspace/
```

Review in this order:

1. `result.json`: status, model, duration, CLI exit, hidden-grade outcome.
2. `patch.diff`: what the agent actually changed.
3. `agent.log`: how it navigated, tested, recovered, or failed.
4. `workspace/`: final complete repository if the patch needs context.
5. `grader.py`: only after judging the agent's approach, to understand the
   exact missed invariant.
