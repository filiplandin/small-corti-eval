# Repair a bounded TTL/LRU cache

`TTLCache` is intended to be a small in-memory cache with both expiration and
least-recently-used eviction. The current implementation has production bugs.

Preserve the public class and method signatures in `ttl_cache.py`.

Required behavior:

- `capacity` must be an integer >= 1; booleans are not valid integers here.
  Otherwise raise `ValueError`.
- `ttl_seconds` must be >= 0; otherwise raise `ValueError`.
- An entry expires when its age is **greater than or equal to** `ttl_seconds`.
- `get(key)` raises `KeyError(key)` for missing or expired entries.
- A successful `get` makes that key the most recently used entry.
- Updating an existing key replaces its value and expiration time and makes it
  most recently used.
- Inserting beyond capacity evicts the least recently used live entry.
- `len(cache)` counts only live entries and removes expired entries as a side
  effect.
- Keep the implementation synchronous and dependency-free. The injected
  `clock` must remain supported so behavior can be tested deterministically.

Run the public tests with:

```bash
python3 -m unittest discover -s tests -v
```
