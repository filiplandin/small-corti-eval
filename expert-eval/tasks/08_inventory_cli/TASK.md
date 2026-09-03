# Complete a persistent inventory CLI

Complete the dependency-free `inventory` package. It is invoked as:

```bash
python3 -m inventory --db PATH COMMAND ...
```

The database is a JSON object mapping SKU strings to non-negative integer
quantities.

Commands:

- `add SKU QUANTITY`: quantity must be a positive integer. Add it to any
  existing quantity and output `{"sku": SKU, "quantity": NEW_TOTAL}`.
- `remove SKU QUANTITY`: quantity must be a positive integer and cannot exceed
  current stock. Delete the SKU when the resulting quantity is zero. Output the
  resulting SKU and quantity.
- `get SKU`: output the current SKU and quantity.
- `list`: output a JSON list of `{"sku": ..., "quantity": ...}` objects sorted
  lexicographically by SKU.

Additional requirements:

- Successful commands emit exactly one JSON value followed by a newline on
  stdout and return exit code 0.
- User/data errors return exit code 2, write a concise message to stderr, and
  must not change the database.
- Reject empty SKUs, unknown SKUs for `get`/`remove`, invalid quantities,
  insufficient stock, malformed JSON, non-object databases, and database
  entries with invalid SKU or quantity types. Booleans are not quantities.
- A missing database behaves like an empty inventory. Read-only commands must
  not create it.
- When a mutating command targets a database whose parent directories do not
  exist, create those directories before saving the database.
- Mutating commands must persist atomically by writing a sibling temporary file
  and replacing the database with `os.replace` only after all validation.
- Preserve the public helpers in `inventory.store`; organize other code freely.
- Do not use network access or third-party dependencies.

Run:

```bash
python3 -m unittest discover -s tests -v
```
