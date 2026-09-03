# Safely extract an untrusted ZIP archive

Implement `safe_extract_zip(archive_path, destination, max_total_size)` in
`safe_zip.py` while preserving the public function and `UnsafeArchiveError`.

The destination must not exist before the call. On success, create it and
return the lexicographically sorted POSIX-style relative paths of extracted
regular files; directory entries are not returned.

Required behavior:

- `max_total_size` must be an integer >= 0; booleans are invalid. Validate it
  before opening the archive or creating the destination. For an invalid value,
  raise either `TypeError` or `ValueError`.
- Raise `FileExistsError` if `destination` already exists.
- Validate the complete ZIP directory before creating `destination` or writing
  any files. Any unsafe entry raises `UnsafeArchiveError` and leaves the
  destination absent.
- Entry names use `/` as their separator. Reject absolute paths, Windows drive
  or UNC paths, backslashes, and any empty, `.` or `..` path component. A final
  empty component is allowed only for a directory entry ending in `/`.
- Reject symbolic-link entries, duplicate normalized paths, and archives where
  one entry must be both a file and a parent directory of another entry.
- The sum of declared uncompressed sizes of regular files must be <=
  `max_total_size`.
- Create explicit and implicit directories as necessary. Extract regular files
  by streaming their contents; do not call `ZipFile.extract` or `extractall`.
- If extraction fails after validation, remove the newly created destination
  before re-raising the original exception.
- Keep the implementation synchronous and dependency-free.

Run:

```bash
python3 -m unittest discover -s tests -v
```
