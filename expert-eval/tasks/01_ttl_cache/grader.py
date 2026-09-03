import pathlib
import sys

sys.path.insert(0, sys.argv[1])
from ttl_cache import TTLCache


class Clock:
    def __init__(self): self.value = 0.0
    def __call__(self): return self.value


for capacity in [0, -1, 1.5, True]:
    try: TTLCache(capacity, 1)
    except ValueError: pass
    else: raise AssertionError(f"invalid capacity accepted: {capacity!r}")
try: TTLCache(1, -0.1)
except ValueError: pass
else: raise AssertionError("negative ttl accepted")

clock = Clock(); cache = TTLCache(2, 5, clock)
cache.put("a", 1); clock.value = 1; cache.put("b", 2)
assert cache.get("a") == 1
clock.value = 2; cache.put("c", 3)
try: cache.get("b")
except KeyError as exc: assert exc.args == ("b",)
else: raise AssertionError("least-recently-used entry not evicted")

clock.value = 6
assert len(cache) == 1, "len must purge the entry at the expiration boundary"
cache.put("c", 30)
clock.value = 10
assert cache.get("c") == 30, "updating a key must reset expiration"

zero = TTLCache(1, 0, clock); zero.put("x", 1)
assert len(zero) == 0
print("PASS")
