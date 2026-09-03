import copy
import datetime as dt
import json


class EventFormatError(ValueError):
    pass


def _timestamp(value, line_number):
    if not isinstance(value, str):
        raise EventFormatError(f"line {line_number}: invalid timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventFormatError(f"line {line_number}: invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EventFormatError(f"line {line_number}: timestamp requires timezone")
    return parsed


def load_latest_events(lines):
    latest = {}
    for line_number, line in enumerate(lines, 1):
        if not isinstance(line, str) or not line.strip():
            if isinstance(line, str):
                continue
            raise EventFormatError(f"line {line_number}: expected string")
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError) as exc:
            raise EventFormatError(f"line {line_number}: invalid JSON") from exc
        if not isinstance(event, dict):
            raise EventFormatError(f"line {line_number}: event must be an object")
        if not isinstance(event.get("id"), str) or not event["id"]:
            raise EventFormatError(f"line {line_number}: invalid id")
        if event.get("kind") not in {"created", "updated", "deleted"}:
            raise EventFormatError(f"line {line_number}: invalid kind")
        parsed = _timestamp(event.get("timestamp"), line_number)
        previous = latest.get(event["id"])
        if previous is None or parsed >= previous[0]:
            latest[event["id"]] = (parsed, copy.deepcopy(event))
    return [event for _, event in sorted(latest.values(), key=lambda item: (item[0], item[1]["id"]))]
