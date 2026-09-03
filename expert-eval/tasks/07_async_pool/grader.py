import asyncio
import sys

sys.path.insert(0, sys.argv[1])
from async_pool import map_limited


async def main():
    consumed = [False]
    def items():
        consumed[0] = True
        yield 1
    for bad in [0, -1, 1.5, True]:
        consumed[0] = False
        try: await map_limited(lambda value: value, items(), bad)
        except ValueError: pass
        else: raise AssertionError(f"invalid limit accepted: {bad!r}")
        assert not consumed[0], "items consumed before limit validation"

    assert await map_limited(lambda value: asyncio.sleep(0, result=value), [], 2) == []

    active = 0; maximum = 0; calls = []
    async def work(value):
        nonlocal active, maximum
        calls.append(value); active += 1; maximum = max(maximum, active)
        try:
            await asyncio.sleep((6 - value) * 0.002)
            return value * 10
        finally:
            active -= 1
    assert await map_limited(work, (value for value in range(1, 6)), 3) == [10, 20, 30, 40, 50]
    assert maximum == 3 and sorted(calls) == [1, 2, 3, 4, 5] and active == 0

    started = asyncio.Event(); cleaned = []
    async def fragile(value):
        if value == "fail":
            await started.wait()
            raise RuntimeError("original")
        started.set()
        try:
            await asyncio.sleep(10)
        finally:
            cleaned.append(value)
    try: await map_limited(fragile, ["slow", "fail", "queued"], 2)
    except RuntimeError as exc: assert str(exc) == "original"
    else: raise AssertionError("worker exception not propagated")
    assert "slow" in cleaned and active == 0

asyncio.run(main())
print("PASS")
