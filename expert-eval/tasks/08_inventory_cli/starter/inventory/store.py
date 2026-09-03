import json


class InventoryError(ValueError):
    pass


def load_inventory(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_inventory(path, inventory):
    path.write_text(json.dumps(inventory))
