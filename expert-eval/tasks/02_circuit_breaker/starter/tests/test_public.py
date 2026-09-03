import unittest

from circuit_breaker import CircuitBreaker, CircuitOpenError


class CircuitBreakerTests(unittest.TestCase):
    def test_boolean_threshold_is_invalid(self):
        with self.assertRaises(ValueError):
            CircuitBreaker(True, 5)

    def test_opens_at_threshold_and_blocks_calls(self):
        now = [0.0]
        breaker = CircuitBreaker(2, 10, lambda: now[0])
        calls = [0]

        def fail():
            calls[0] += 1
            raise ValueError("boom")

        for _ in range(2):
            with self.assertRaises(ValueError):
                breaker.call(fail)
        self.assertEqual(breaker.state, "open")
        with self.assertRaises(CircuitOpenError):
            breaker.call(fail)
        self.assertEqual(calls[0], 2)

    def test_successful_probe_closes(self):
        now = [0.0]
        breaker = CircuitBreaker(1, 5, lambda: now[0])
        with self.assertRaises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("x")))
        now[0] = 5
        self.assertEqual(breaker.state, "half-open")
        self.assertEqual(breaker.call(lambda: 42), 42)
        self.assertEqual(breaker.state, "closed")


if __name__ == "__main__":
    unittest.main()
