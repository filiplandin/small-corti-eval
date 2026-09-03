# Implement a bounded HTTP retry policy

Implement `request_with_retries` in `retrying.py` while preserving the public
classes and function signature. `send` is a zero-argument callable that either
returns a `Response` or raises an exception.

Required behavior:

- Validate all arguments before calling `send` or `sleep`.
- `method` must be a non-empty string and is compared case-insensitively.
- `max_attempts` must be an integer >= 1; booleans are invalid.
- `base_delay` must be a finite, non-boolean integer or float >= 0.
- `idempotency_key` must be `None` or a non-empty string.
- Invalid arguments must raise either `TypeError` or `ValueError`, before
  calling `send` or `sleep`.
- Retry only `TransientTransportError` and response statuses `429`, `500`,
  `502`, `503`, and `504`. Propagate every other exception immediately and
  return every other response immediately.
- Automatic retries are allowed for `GET`, `HEAD`, `PUT`, `DELETE`, `OPTIONS`,
  and `TRACE`. Any method may retry when a non-empty `idempotency_key` is
  supplied. When retries are not allowed, return the first response or
  propagate the first exception without sleeping.
- Make at most `max_attempts` calls to `send`.
- Between retryable attempts, use a case-insensitive `Retry-After` response
  header when its stripped value contains only decimal digits. Otherwise sleep
  for `base_delay * 2 ** (attempt_number - 1)`, where the first call has
  attempt number 1. Transport exceptions always use this fallback.
- Never sleep after the final attempt. If the final result is a retryable
  response, return it. If the final result is `TransientTransportError`, raise
  `RetryExhaustedError` with that exception as `__cause__`.
- Do not mutate a `Response` or its headers. Keep the module synchronous and
  dependency-free.

Run:

```bash
python3 -m unittest discover -s tests -v
```
