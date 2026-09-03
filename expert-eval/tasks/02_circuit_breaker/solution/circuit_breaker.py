import time


class CircuitOpenError(RuntimeError):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=30, clock=time.monotonic):
        if not isinstance(failure_threshold, int) or isinstance(failure_threshold, bool) or failure_threshold < 1:
            raise ValueError("failure_threshold must be an integer >= 1")
        if recovery_timeout < 0:
            raise ValueError("recovery_timeout must be >= 0")
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._clock = clock
        self._state = "closed"
        self._failures = 0
        self._opened_at = None

    @property
    def state(self):
        if self._state == "open" and self._clock() - self._opened_at >= self.recovery_timeout:
            return "half-open"
        return self._state

    def call(self, fn, *args, **kwargs):
        current = self.state
        if current == "open":
            raise CircuitOpenError("circuit breaker is open")
        if current == "half-open":
            self._state = "half-open"
        try:
            result = fn(*args, **kwargs)
        except Exception:
            self._failures += 1
            if self._state == "half-open" or self._failures >= self.failure_threshold:
                self._state = "open"
                self._opened_at = self._clock()
            raise
        self._state = "closed"
        self._failures = 0
        self._opened_at = None
        return result
