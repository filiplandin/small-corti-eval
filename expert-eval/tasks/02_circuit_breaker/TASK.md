# Implement a circuit breaker

Implement the dependency-free `CircuitBreaker` in `circuit_breaker.py` while
preserving its public API.

Required behavior:

- `failure_threshold` must be an integer >= 1; booleans are not valid integers
  here. Invalid values raise `ValueError`.
- `recovery_timeout` must be >= 0.
- The initial state is `"closed"`.
- In the closed state, `call(fn, *args, **kwargs)` invokes `fn` and returns its
  result. A success resets the consecutive-failure count.
- Exceptions from `fn` count as consecutive failures and are re-raised. When
  the threshold is reached, the breaker becomes `"open"` and records the time.
- While open and before the timeout has elapsed, `call` must raise
  `CircuitOpenError` without invoking `fn`.
- Once the timeout has elapsed, the next call is a half-open probe. A successful
  probe closes and resets the breaker. A failed probe reopens it from the new
  failure time and re-raises the original exception.
- The read-only `state` property must report `"closed"`, `"open"`, or
  `"half-open"` consistently. In particular, once an open breaker's timeout
  has elapsed, `state` must report `"half-open"` before the probe call occurs.
- Use the injected `clock` for all time decisions.

Thread-safety is out of scope.

Run the public tests with:

```bash
python3 -m unittest discover -s tests -v
```
