# Repair deterministic dependency planning

`build_plan(graph)` receives a mapping from task name to an iterable of direct
dependency names. Repair it without changing the public API or exception
classes.

Required behavior:

- Return every task exactly once in a valid topological order: dependencies
  must appear before their dependants.
- When multiple tasks are available, always choose the lexicographically
  smallest. The complete output must therefore be deterministic regardless of
  mapping or set insertion order.
- Every dependency must also be a key in `graph`. Otherwise raise
  `UnknownDependencyError` and include both the depending task and unknown
  dependency in the exception message.
- A cycle, including a self-cycle, raises `DependencyCycleError`. Its message
  must mention every task participating in at least one cycle; exact formatting
  is not prescribed.
- Do not mutate the mapping or dependency iterables.
- Task names are strings. An empty graph returns an empty list.
- Keep the implementation dependency-free.

Run:

```bash
python3 -m unittest discover -s tests -v
```
