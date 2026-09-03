import pathlib
import tempfile
import unittest
import zipfile

from safe_zip import UnsafeArchiveError, safe_extract_zip


class SafeZipTests(unittest.TestCase):
    def test_rejects_invalid_size_before_opening_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            missing_archive = root / "missing.zip"
            for invalid in (-1, 1.5, True):
                destination = root / f"output-{invalid!r}"
                with self.assertRaises((TypeError, ValueError)):
                    safe_extract_zip(missing_archive, destination, invalid)
                self.assertFalse(destination.exists())

    def test_extracts_files_and_returns_sorted_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "input.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("b.txt", "b")
                bundle.writestr("nested/a.txt", "a")
            destination = root / "output"
            self.assertEqual(
                safe_extract_zip(archive, destination, 2),
                ["b.txt", "nested/a.txt"],
            )
            self.assertEqual((destination / "nested" / "a.txt").read_text(), "a")

    def test_rejects_traversal_without_creating_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "input.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("ok.txt", "ok")
                bundle.writestr("../escape.txt", "bad")
            destination = root / "output"
            with self.assertRaises(UnsafeArchiveError):
                safe_extract_zip(archive, destination, 100)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
