# Implement immutable layered configuration merging

Repair `merge_config(base, overlay)` in `config_merge.py` while preserving the
public function and exported `DELETE` sentinel.

Required behavior:

- Both arguments must be mappings; otherwise raise `TypeError`.
- Return a new plain `dict`. Never mutate either input or reuse mutable nested
  containers from them.
- When both values for a key are mappings, merge them recursively.
- Any other overlay value replaces the base value. Lists and tuples are
  replaced, not concatenated.
- `None` is an ordinary replacement value.
- If an overlay value is the exact exported `DELETE` sentinel, remove that key.
  Deleting a missing key is a no-op.
- The sentinel works recursively.
- Keys present only in the base or only in the overlay must be deep-copied into
  the result.
- Support arbitrary mapping implementations, not only `dict`.
- Keep the implementation dependency-free.

Run:

```bash
python3 -m unittest discover -s tests -v
```
