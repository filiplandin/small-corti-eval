import json


class EventFormatError(ValueError):
    pass


def load_latest_events(lines):
    events = []
    for line in lines:
        if line.strip():
            events.append(json.loads(line))
    return events
