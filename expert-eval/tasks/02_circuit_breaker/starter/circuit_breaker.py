import time


class CircuitOpenError(RuntimeError):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=30, clock=time.monotonic):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._clock = clock
        self._state = "closed"

    @property
    def state(self):
        return self._state

    def call(self, fn, *args, **kwargs):
        raise NotImplementedError
