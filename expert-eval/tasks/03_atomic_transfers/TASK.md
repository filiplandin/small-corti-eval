# Make a batch of account transfers atomic

`apply_transfers(accounts, transfers)` applies an ordered batch of money
transfers to a mutable account-balance mapping. The current implementation can
leave partially applied changes when a later transfer is invalid.

Preserve the public function signature and exception classes.

Required behavior:

- `accounts` maps account IDs to numeric balances.
- Each transfer is `(source_id, destination_id, amount)`.
- Validate and apply transfers in their given order; an earlier valid transfer
  may fund a later one within the same batch.
- Unknown accounts raise `UnknownAccountError`.
- A transfer to the same account raises `InvalidTransferError`.
- Amounts must be numeric, finite, and strictly positive. Booleans are not
  valid amounts. Invalid amounts raise `InvalidTransferError`.
- Insufficient funds at that point in the ordered batch raise
  `InsufficientFundsError`.
- If any transfer fails, the original `accounts` mapping must remain exactly
  unchanged.
- On success, mutate and return the original mapping object.
- Do not modify the transfer collection.

Keep the package dependency-free. Run:

```bash
python3 -m unittest discover -s tests -v
```
