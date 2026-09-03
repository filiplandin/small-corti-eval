import unittest

from ttl_cache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class TTLCacheTests(unittest.TestCase):
    def test_boolean_capacity_is_invalid(self):
        with self.assertRaises(ValueError):
            TTLCache(True, 5)

    def test_value_expires_at_boundary(self):
        clock = FakeClock()
        cache = TTLCache(2, 5, clock)
        cache.put("a", 1)
        clock.now = 5
        with self.assertRaises(KeyError):
            cache.get("a")

    def test_get_updates_lru_order(self):
        clock = FakeClock()
        cache = TTLCache(2, 10, clock)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(cache.get("a"), 1)
        cache.put("c", 3)
        with self.assertRaises(KeyError):
            cache.get("b")


if __name__ == "__main__":
    unittest.main()
