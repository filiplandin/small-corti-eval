import math
from numbers import Real


class UnknownAccountError(ValueError):
    pass


class InvalidTransferError(ValueError):
    pass


class InsufficientFundsError(ValueError):
    pass


def apply_transfers(accounts, transfers):
    """Apply transfers in order and return the original account mapping."""
    staged = dict(accounts)
    for source, destination, amount in transfers:
        if source not in staged or destination not in staged:
            raise UnknownAccountError("unknown account")
        if source == destination:
            raise InvalidTransferError("source and destination must differ")
        if isinstance(amount, bool) or not isinstance(amount, Real) or not math.isfinite(amount) or amount <= 0:
            raise InvalidTransferError("amount must be finite and positive")
        if staged[source] < amount:
            raise InsufficientFundsError(source)
        staged[source] -= amount
        staged[destination] += amount
    accounts.clear()
    accounts.update(staged)
    return accounts
