import asyncio
import unittest

from async_pool import map_limited


class AsyncPoolTests(unittest.IsolatedAsyncioTestCase):
    async def test_limits_concurrency_and_preserves_order(self):
        active = 0
        maximum = 0

        async def work(value):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            await asyncio.sleep((4 - value) * 0.005)
            active -= 1
            return value * 2

        self.assertEqual(await map_limited(work, [1, 2, 3], 2), [2, 4, 6])
        self.assertEqual(maximum, 2)

    async def test_invalid_limit(self):
        with self.assertRaises(ValueError):
            await map_limited(lambda value: value, [], 0)


if __name__ == "__main__":
    unittest.main()
