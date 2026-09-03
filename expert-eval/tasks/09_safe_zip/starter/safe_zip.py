class UnsafeArchiveError(ValueError):
    pass


def safe_extract_zip(archive_path, destination, max_total_size):
    raise NotImplementedError
