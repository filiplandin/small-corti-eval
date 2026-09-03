import json
import os
import pathlib
import tempfile


class InventoryError(ValueError):
    pass


def _validate(inventory):
    if not isinstance(inventory, dict):
        raise InventoryError("database must be a JSON object")
    for sku, quantity in inventory.items():
        if not isinstance(sku, str) or not sku:
            raise InventoryError("database contains an invalid SKU")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            raise InventoryError(f"invalid quantity for {sku}")
    return inventory


def load_inventory(path):
    path = pathlib.Path(path)
    if not path.exists():
        return {}
    try:
        inventory = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryError("database is not valid JSON") from exc
    return _validate(inventory)


def save_inventory(path, inventory):
    path = pathlib.Path(path)
    _validate(inventory)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(inventory, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise
