import time
from collections import OrderedDict


class TTLCache:
    def __init__(self, capacity, ttl_seconds, clock=time.monotonic):
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise ValueError("capacity must be an integer >= 1")
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must be >= 0")
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries = OrderedDict()

    def _purge_expired(self):
        now = self._clock()
        expired = [
            key for key, (_, created_at) in self._entries.items()
            if now - created_at >= self.ttl_seconds
        ]
        for key in expired:
            del self._entries[key]

    def get(self, key):
        value, created_at = self._entries[key]
        if self._clock() - created_at >= self.ttl_seconds:
            del self._entries[key]
            raise KeyError(key)
        self._entries.move_to_end(key)
        return value

    def put(self, key, value):
        self._purge_expired()
        if key in self._entries:
            del self._entries[key]
        self._entries[key] = (value, self._clock())
        if len(self._entries) > self.capacity:
            self._entries.popitem(last=False)

    def __len__(self):
        self._purge_expired()
        return len(self._entries)
