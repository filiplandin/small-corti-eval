import sys

sys.path.insert(0, sys.argv[1])
from circuit_breaker import CircuitBreaker, CircuitOpenError


for threshold in [0, -1, 1.5, True]:
    try: CircuitBreaker(threshold, 1)
    except ValueError: pass
    else: raise AssertionError(f"invalid threshold accepted: {threshold!r}")
try: CircuitBreaker(1, -1)
except ValueError: pass
else: raise AssertionError("negative timeout accepted")

now = [0.0]; breaker = CircuitBreaker(2, 5, lambda: now[0])
attempts = [0]
def fail(): attempts[0] += 1; raise LookupError("failure")
for _ in range(2):
    try: breaker.call(fail)
    except LookupError: pass
assert breaker.state == "open"
try: breaker.call(fail)
except CircuitOpenError: pass
else: raise AssertionError("open breaker did not reject call")
assert attempts[0] == 2
now[0] = 5
assert breaker.state == "half-open"
try: breaker.call(fail)
except LookupError: pass
assert breaker.state == "open"
now[0] = 9.9
try: breaker.call(lambda: 1)
except CircuitOpenError: pass
else: raise AssertionError("failed probe did not restart timeout")
now[0] = 10
assert breaker.call(lambda x, scale=1: x * scale, 4, scale=3) == 12
assert breaker.state == "closed"

# A success in closed state resets consecutive failures.
try: breaker.call(fail)
except LookupError: pass
assert breaker.call(lambda: "ok") == "ok"
try: breaker.call(fail)
except LookupError: pass
assert breaker.state == "closed"
print("PASS")
