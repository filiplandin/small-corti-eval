import copy
import sys

sys.path.insert(0, sys.argv[1])
from events import EventFormatError, load_latest_events


lines = [
    "  ",
    '{"id":"x","timestamp":"2026-02-01T12:00:00+02:00","kind":"created","meta":{"n":1}}',
    '{"id":"y","timestamp":"2026-02-01T09:30:00Z","kind":"created"}',
    '{"id":"x","timestamp":"2026-02-01T10:00:00Z","kind":"updated","meta":{"n":2}}',
    '{"id":"x","timestamp":"2026-02-01T10:00:00+00:00","kind":"deleted","reason":"duplicate time"}',
]
before = copy.deepcopy(lines)
result = load_latest_events(lines)
assert lines == before
assert [event["id"] for event in result] == ["y", "x"]
assert result[1]["kind"] == "deleted" and result[1]["reason"] == "duplicate time"

bad_lines = [
    "[]",
    '{"id":"","timestamp":"2026-01-01T00:00:00Z","kind":"created"}',
    '{"id":"a","timestamp":"2026-01-01T00:00:00","kind":"created"}',
    '{"id":"a","timestamp":"bad","kind":"created"}',
    '{"id":"a","timestamp":"2026-01-01T00:00:00Z","kind":"other"}',
    '{"id":"a","timestamp":"2026-01-01T00:00:00Z"}',
]
for bad in bad_lines:
    try: load_latest_events(["", bad])
    except EventFormatError as exc: assert "2" in str(exc)
    else: raise AssertionError(f"invalid event accepted: {bad}")
print("PASS")
