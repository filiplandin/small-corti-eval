import pathlib
import stat
import sys
import tempfile
import zipfile

sys.path.insert(0, sys.argv[1])
from safe_zip import UnsafeArchiveError, safe_extract_zip


with tempfile.TemporaryDirectory() as temp:
    root = pathlib.Path(temp)
    unopened = root / "missing.zip"
    for invalid in [-1, 1.5, True]:
        destination = root / f"invalid-{invalid!r}"
        try: safe_extract_zip(unopened, destination, invalid)
        except (TypeError, ValueError): pass
        else: raise AssertionError(f"invalid size accepted: {invalid!r}")
        assert not destination.exists()

    archive = root / "valid.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("empty/", b"")
        bundle.writestr("z.txt", b"z")
        bundle.writestr("nested/a.bin", b"abc")
    destination = root / "valid"
    assert safe_extract_zip(archive, destination, 4) == ["nested/a.bin", "z.txt"]
    assert (destination / "empty").is_dir()
    assert (destination / "nested" / "a.bin").read_bytes() == b"abc"
    try: safe_extract_zip(archive, destination, 4)
    except FileExistsError: pass
    else: raise AssertionError("existing destination accepted")

    unsafe_names = ["/absolute", "../escape", "a/../b", "a//b", "a/./b", "C:/drive", "a\\b"]
    for index, name in enumerate(unsafe_names):
        bad = root / f"unsafe-{index}.zip"
        with zipfile.ZipFile(bad, "w") as bundle: bundle.writestr(name, b"x")
        output = root / f"unsafe-{index}"
        try: safe_extract_zip(bad, output, 10)
        except UnsafeArchiveError: pass
        else: raise AssertionError(f"unsafe name accepted: {name!r}")
        assert not output.exists()

    symlink = root / "symlink.zip"
    link = zipfile.ZipInfo("link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(symlink, "w") as bundle: bundle.writestr(link, "target")
    try: safe_extract_zip(symlink, root / "symlink-out", 100)
    except UnsafeArchiveError: pass
    else: raise AssertionError("symbolic link accepted")

    for name, members in {
        "duplicate": [("a", b"1"), ("a", b"2")],
        "parent-conflict": [("a", b"file"), ("a/b", b"child")],
    }.items():
        bad = root / f"{name}.zip"
        with zipfile.ZipFile(bad, "w") as bundle:
            for member, content in members: bundle.writestr(member, content)
        output = root / f"{name}-out"
        try: safe_extract_zip(bad, output, 100)
        except UnsafeArchiveError: pass
        else: raise AssertionError(f"{name} accepted")
        assert not output.exists()

    oversized = root / "oversized.zip"
    with zipfile.ZipFile(oversized, "w") as bundle:
        bundle.writestr("first", b"12"); bundle.writestr("second", b"34")
    try: safe_extract_zip(oversized, root / "oversized-out", 3)
    except UnsafeArchiveError: pass
    else: raise AssertionError("oversized archive accepted")
    assert not (root / "oversized-out").exists()
print("PASS")
