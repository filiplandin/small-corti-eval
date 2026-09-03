import unittest

from transfers import InsufficientFundsError, apply_transfers


class TransferTests(unittest.TestCase):
    def test_success_mutates_original(self):
        accounts = {"a": 10, "b": 0, "c": 0}
        result = apply_transfers(accounts, [("a", "b", 6), ("b", "c", 4)])
        self.assertIs(result, accounts)
        self.assertEqual(accounts, {"a": 4, "b": 2, "c": 4})

    def test_failed_batch_is_atomic(self):
        accounts = {"a": 10, "b": 0}
        before = dict(accounts)
        with self.assertRaises(InsufficientFundsError):
            apply_transfers(accounts, [("a", "b", 5), ("a", "b", 6)])
        self.assertEqual(accounts, before)


if __name__ == "__main__":
    unittest.main()
