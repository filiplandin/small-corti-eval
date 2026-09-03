import time
from collections import OrderedDict


class TTLCache:
    def __init__(self, capacity, ttl_seconds, clock=time.monotonic):
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries = OrderedDict()

    def get(self, key):
        value, created_at = self._entries[key]
        if self._clock() - created_at > self.ttl_seconds:
            del self._entries[key]
            raise KeyError(key)
        return value

    def put(self, key, value):
        self._entries[key] = (value, self._clock())
        if len(self._entries) > self.capacity:
            self._entries.popitem(last=False)

    def __len__(self):
        return len(self._entries)
