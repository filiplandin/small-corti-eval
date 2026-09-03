from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from typing import Any


@dataclass
class Response:
    status: int
    headers: object = field(default_factory=dict)
    body: Any = None


class TransientTransportError(Exception):
    pass


class RetryExhaustedError(RuntimeError):
    pass


RETRYABLE_METHODS = {"GET", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"}
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _retry_after(response, fallback):
    if isinstance(response.headers, Mapping):
        for name, value in response.headers.items():
            if isinstance(name, str) and name.lower() == "retry-after":
                stripped = value.strip() if isinstance(value, str) else ""
                if stripped.isdecimal():
                    return int(stripped)
                break
    return fallback


def request_with_retries(
    send,
    method,
    *,
    max_attempts=3,
    base_delay=1.0,
    sleep,
    idempotency_key=None,
):
    if not isinstance(method, str) or not method:
        raise ValueError("method must be a non-empty string")
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or max_attempts < 1:
        raise ValueError("max_attempts must be an integer >= 1")
    if (
        isinstance(base_delay, bool)
        or not isinstance(base_delay, (int, float))
        or not math.isfinite(base_delay)
        or base_delay < 0
    ):
        raise ValueError("base_delay must be finite and >= 0")
    if idempotency_key is not None and (
        not isinstance(idempotency_key, str) or not idempotency_key
    ):
        raise ValueError("idempotency_key must be None or a non-empty string")

    retry_allowed = method.upper() in RETRYABLE_METHODS or idempotency_key is not None
    for attempt in range(1, max_attempts + 1):
        try:
            response = send()
        except TransientTransportError as exc:
            if not retry_allowed:
                raise
            if attempt == max_attempts:
                raise RetryExhaustedError("retry attempts exhausted") from exc
            sleep(base_delay * 2 ** (attempt - 1))
            continue
        if not retry_allowed or response.status not in RETRYABLE_STATUSES:
            return response
        if attempt == max_attempts:
            return response
        fallback = base_delay * 2 ** (attempt - 1)
        sleep(_retry_after(response, fallback))
    raise AssertionError("unreachable")
