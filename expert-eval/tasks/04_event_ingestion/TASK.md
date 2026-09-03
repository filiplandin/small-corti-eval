# Implement deterministic NDJSON event ingestion

Implement `load_latest_events(lines)` in `events.py`. The function consumes an
iterable of strings containing newline-delimited JSON records.

Required behavior:

- Ignore blank or whitespace-only lines.
- Every nonblank line must decode to a JSON object; otherwise raise
  `EventFormatError` with the one-based input line number in the message.
- Required fields are `id`, `timestamp`, and `kind`.
- `id` must be a non-empty string.
- `kind` must be `"created"`, `"updated"`, or `"deleted"`.
- `timestamp` must be an ISO-8601 string with an explicit timezone. Accept `Z`
  as UTC. Naive datetimes are invalid.
- Preserve all fields of each accepted event.
- For repeated IDs, keep the event with the latest absolute timestamp. If two
  timestamps are equal, keep the later input occurrence.
- Return a list ordered by ascending absolute timestamp, then by ID.
- Do not mutate caller-provided objects or collections.
- Keep the implementation dependency-free.

Run:

```bash
python3 -m unittest discover -s tests -v
```
