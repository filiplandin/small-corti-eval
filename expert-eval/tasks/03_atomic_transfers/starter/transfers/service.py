class UnknownAccountError(ValueError):
    pass


class InvalidTransferError(ValueError):
    pass


class InsufficientFundsError(ValueError):
    pass


def apply_transfers(accounts, transfers):
    """Apply transfers in order and return the original account mapping."""
    for source, destination, amount in transfers:
        if source not in accounts or destination not in accounts:
            raise UnknownAccountError("unknown account")
        if amount <= 0:
            raise InvalidTransferError("amount must be positive")
        if accounts[source] < amount:
            raise InsufficientFundsError(source)
        accounts[source] -= amount
        accounts[destination] += amount
    return accounts
