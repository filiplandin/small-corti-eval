import pathlib
import shutil
import stat
import zipfile


class UnsafeArchiveError(ValueError):
    pass


def _validated_entries(bundle, max_total_size):
    entries = []
    kinds = {}
    total = 0
    for info in bundle.infolist():
        name = info.filename
        if not name or "\\" in name or name.startswith("/"):
            raise UnsafeArchiveError(f"unsafe entry name: {name!r}")
        trimmed = name[:-1] if name.endswith("/") else name
        parts = trimmed.split("/")
        if not trimmed or any(part in {"", ".", ".."} for part in parts):
            raise UnsafeArchiveError(f"unsafe entry name: {name!r}")
        if len(parts[0]) >= 2 and parts[0][1] == ":":
            raise UnsafeArchiveError(f"unsafe entry name: {name!r}")
        mode = info.external_attr >> 16
        if stat.S_IFMT(mode) == stat.S_IFLNK:
            raise UnsafeArchiveError(f"symbolic link rejected: {name!r}")
        is_directory = info.is_dir()
        normalized = "/".join(parts)
        if normalized in kinds:
            raise UnsafeArchiveError(f"duplicate path: {normalized!r}")
        for index in range(1, len(parts)):
            parent = "/".join(parts[:index])
            if kinds.get(parent) == "file":
                raise UnsafeArchiveError(f"file is also a parent: {parent!r}")
        if not is_directory:
            prefix = normalized + "/"
            if any(existing.startswith(prefix) for existing in kinds):
                raise UnsafeArchiveError(f"file is also a parent: {normalized!r}")
            total += info.file_size
            if total > max_total_size:
                raise UnsafeArchiveError("archive exceeds max_total_size")
        kinds[normalized] = "directory" if is_directory else "file"
        entries.append((info, pathlib.PurePosixPath(normalized), is_directory))
    return entries


def safe_extract_zip(archive_path, destination, max_total_size):
    if (
        not isinstance(max_total_size, int)
        or isinstance(max_total_size, bool)
        or max_total_size < 0
    ):
        raise ValueError("max_total_size must be an integer >= 0")
    destination = pathlib.Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    with zipfile.ZipFile(archive_path) as bundle:
        entries = _validated_entries(bundle, max_total_size)
        destination.mkdir(parents=True)
        extracted = []
        try:
            for info, relative, is_directory in entries:
                target = destination.joinpath(*relative.parts)
                if is_directory:
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                extracted.append(relative.as_posix())
        except BaseException:
            shutil.rmtree(destination)
            raise
    return sorted(extracted)
