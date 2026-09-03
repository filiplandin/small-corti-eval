import copy
import math
import sys

sys.path.insert(0, sys.argv[1])
from transfers import (
    InsufficientFundsError,
    InvalidTransferError,
    UnknownAccountError,
    apply_transfers,
)


accounts = {"a": 10.0, "b": 0.0, "c": 1.0}
transfers = [("a", "b", 7.0), ("b", "c", 5.0)]
transfers_before = copy.deepcopy(transfers)
identity = id(accounts)
assert apply_transfers(accounts, transfers) is accounts and id(accounts) == identity
assert accounts == {"a": 3.0, "b": 2.0, "c": 6.0}
assert transfers == transfers_before

cases = [
    (("a", "missing", 1), UnknownAccountError),
    (("a", "a", 1), InvalidTransferError),
    (("a", "b", 0), InvalidTransferError),
    (("a", "b", -1), InvalidTransferError),
    (("a", "b", True), InvalidTransferError),
    (("a", "b", "1"), InvalidTransferError),
    (("a", "b", math.inf), InvalidTransferError),
    (("a", "b", math.nan), InvalidTransferError),
]
for transfer, expected in cases:
    state = {"a": 5.0, "b": 0.0}; before = copy.deepcopy(state)
    try: apply_transfers(state, [("a", "b", 1), transfer])
    except expected: pass
    else: raise AssertionError(f"did not raise {expected.__name__} for {transfer!r}")
    assert state == before, f"batch was not atomic for {transfer!r}"

state = {"a": 5, "b": 0}; before = dict(state)
try: apply_transfers(state, [("a", "b", 3), ("a", "b", 3)])
except InsufficientFundsError: pass
else: raise AssertionError("insufficient funds not detected sequentially")
assert state == before
print("PASS")
