# Repair a bounded asynchronous worker pool

Repair `map_limited(fn, items, limit)` in `async_pool.py` without changing its
signature.

Required behavior:

- `fn` is an async callable and `items` is any finite iterable.
- Invoke `fn(item)` once per item while running no more than `limit` calls at
  the same time.
- Preserve input order in the returned result list even when calls finish out
  of order.
- `limit` must be an integer >= 1; booleans are invalid. Raise `ValueError`
  before consuming `items` when invalid.
- An empty iterable returns `[]`.
- If a worker raises or is cancelled, cancel all unfinished workers, wait for
  their cleanup, and re-raise the original exception. Do not return partial
  results or leave background tasks running.
- If the caller cancels `map_limited`, apply the same cleanup behavior and
  propagate cancellation.
- Keep the implementation dependency-free and compatible with `asyncio.run`.

Run:

```bash
python3 -m unittest discover -s tests -v
```
