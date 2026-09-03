from dataclasses import dataclass, field
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


def request_with_retries(
    send,
    method,
    *,
    max_attempts=3,
    base_delay=1.0,
    sleep,
    idempotency_key=None,
):
    raise NotImplementedError
