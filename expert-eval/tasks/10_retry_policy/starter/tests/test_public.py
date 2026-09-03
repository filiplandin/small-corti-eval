import unittest

from retrying import Response, request_with_retries


class RetryPolicyTests(unittest.TestCase):
    def test_rejects_invalid_arguments_before_sending(self):
        calls = []
        invalid_cases = [
            {"method": ""},
            {"max_attempts": 0},
            {"max_attempts": 1.5},
            {"max_attempts": True},
            {"base_delay": -1},
            {"base_delay": True},
            {"idempotency_key": ""},
            {"idempotency_key": 1},
        ]
        for kwargs in invalid_cases:
            method = kwargs.pop("method", "GET")
            with self.subTest(method=method, kwargs=kwargs):
                with self.assertRaises((TypeError, ValueError)):
                    request_with_retries(
                        lambda: calls.append(1), method, sleep=lambda _: None, **kwargs
                    )
        self.assertEqual(calls, [])

    def test_retries_get_and_uses_retry_after(self):
        responses = iter([
            Response(503, {"Retry-After": "2"}),
            Response(200, body="ok"),
        ])
        sleeps = []
        result = request_with_retries(
            lambda: next(responses), "get", sleep=sleeps.append
        )
        self.assertEqual(result.body, "ok")
        self.assertEqual(sleeps, [2])

    def test_post_without_idempotency_key_is_not_retried(self):
        calls = []
        result = request_with_retries(
            lambda: calls.append(1) or Response(503),
            "POST",
            sleep=lambda delay: self.fail("must not sleep"),
        )
        self.assertEqual(result.status, 503)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
