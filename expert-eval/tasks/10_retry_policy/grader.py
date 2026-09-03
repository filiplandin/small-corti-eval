import math
import sys

sys.path.insert(0, sys.argv[1])
from retrying import (
    Response,
    RetryExhaustedError,
    TransientTransportError,
    request_with_retries,
)


def invoke(send, method="GET", **kwargs):
    sleeps = []
    result = request_with_retries(send, method, sleep=sleeps.append, **kwargs)
    return result, sleeps


calls = []
for kwargs in [
    {"method": ""},
    {"max_attempts": 0}, {"max_attempts": True}, {"max_attempts": 1.5},
    {"base_delay": -1}, {"base_delay": True}, {"base_delay": math.inf},
    {"idempotency_key": ""}, {"idempotency_key": 1},
]:
    method = kwargs.pop("method", "GET")
    try: invoke(lambda: calls.append(1), method, **kwargs)
    except (TypeError, ValueError): pass
    else: raise AssertionError(f"invalid arguments accepted: {kwargs!r}")
assert not calls

responses = iter([Response(503, {"retry-after": " 2 "}), Response(200, body="ok")])
result, sleeps = invoke(lambda: next(responses), method="get", base_delay=0.5)
assert result.body == "ok" and sleeps == [2]

responses = iter([Response(500, {"Retry-After": "later"}), Response(502), Response(504)])
result, sleeps = invoke(lambda: next(responses), max_attempts=3, base_delay=0.5)
assert result.status == 504 and sleeps == [0.5, 1.0]

calls = []
result, sleeps = invoke(lambda: calls.append(1) or Response(503), method="POST")
assert result.status == 503 and len(calls) == 1 and sleeps == []

responses = iter([Response(429), Response(201)])
result, sleeps = invoke(lambda: next(responses), method="POST", idempotency_key="order-1", base_delay=0)
assert result.status == 201 and sleeps == [0]

attempts = [0]
def flaky():
    attempts[0] += 1
    if attempts[0] == 1: raise TransientTransportError("offline")
    return Response(204)
result, sleeps = invoke(flaky, method="PUT", base_delay=3)
assert result.status == 204 and sleeps == [3]

try: invoke(lambda: (_ for _ in ()).throw(RuntimeError("fatal")))
except RuntimeError as exc: assert str(exc) == "fatal"
else: raise AssertionError("non-transient exception retried or swallowed")

attempts = [0]; sleeps = []
def unavailable():
    attempts[0] += 1
    raise TransientTransportError("still offline")
try:
    request_with_retries(unavailable, "DELETE", max_attempts=3, base_delay=1, sleep=sleeps.append)
except RetryExhaustedError as exc:
    assert isinstance(exc.__cause__, TransientTransportError)
else: raise AssertionError("transport exhaustion not wrapped")
assert attempts[0] == 3 and sleeps == [1, 2]

try: invoke(lambda: (_ for _ in ()).throw(TransientTransportError("post")), method="POST")
except TransientTransportError: pass
else: raise AssertionError("unsafe POST transport failure was retried or wrapped")
print("PASS")
