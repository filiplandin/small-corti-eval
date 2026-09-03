import copy
import sys
from collections import UserDict
from collections.abc import Mapping

sys.path.insert(0, sys.argv[1])
from config_merge import DELETE, merge_config


def snapshot(value):
    if value is DELETE:
        return ("DELETE_SENTINEL",)
    if isinstance(value, Mapping):
        return tuple((key, snapshot(item)) for key, item in value.items())
    if isinstance(value, list):
        return tuple(snapshot(item) for item in value)
    return copy.deepcopy(value)


base = UserDict({
    "service": {"host": "a", "limits": {"cpu": 1, "memory": 2}},
    "features": ["old"],
    "nullable": "value",
    "keep": {"nested": [1]},
})
overlay = UserDict({
    "service": {"limits": {"cpu": 4, "memory": DELETE}, "port": 80},
    "features": ["new"],
    "nullable": None,
    "missing": DELETE,
})
base_before = snapshot(base); overlay_before = snapshot(overlay)
result = merge_config(base, overlay)
assert type(result) is dict
assert result == {
    "service": {"host": "a", "limits": {"cpu": 4}, "port": 80},
    "features": ["new"],
    "nullable": None,
    "keep": {"nested": [1]},
}
assert snapshot(base) == base_before and snapshot(overlay) == overlay_before
result["features"].append("mutated"); result["keep"]["nested"].append(2)
assert snapshot(base) == base_before and snapshot(overlay) == overlay_before

for bad_base, bad_overlay in [([], {}), ({}, []), (None, {})]:
    try: merge_config(bad_base, bad_overlay)
    except TypeError: pass
    else: raise AssertionError("non-mapping input accepted")
print("PASS")
