import copy
from collections.abc import Mapping

DELETE = object()


def merge_config(base, overlay):
    if not isinstance(base, Mapping) or not isinstance(overlay, Mapping):
        raise TypeError("base and overlay must be mappings")
    result = copy.deepcopy(dict(base))
    for key, value in overlay.items():
        if value is DELETE:
            result.pop(key, None)
        elif key in result and isinstance(result[key], Mapping) and isinstance(value, Mapping):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result
