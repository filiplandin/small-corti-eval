import argparse
import json
import pathlib
import sys

from .store import InventoryError, load_inventory, save_inventory


def _quantity(raw):
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise InventoryError("quantity must be a positive integer") from exc
    if str(value) != raw or value <= 0:
        raise InventoryError("quantity must be a positive integer")
    return value


def _sku(raw):
    if not isinstance(raw, str) or not raw:
        raise InventoryError("SKU must not be empty")
    return raw


def _parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ["add", "remove"]:
        command = subparsers.add_parser(name); command.add_argument("sku"); command.add_argument("quantity")
    command = subparsers.add_parser("get"); command.add_argument("sku")
    subparsers.add_parser("list")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    path = pathlib.Path(args.db)
    try:
        inventory = load_inventory(path)
        if args.command == "list":
            output = [{"sku": sku, "quantity": inventory[sku]} for sku in sorted(inventory)]
        else:
            sku = _sku(args.sku)
            if args.command == "get":
                if sku not in inventory: raise InventoryError(f"unknown SKU: {sku}")
                output = {"sku": sku, "quantity": inventory[sku]}
            else:
                quantity = _quantity(args.quantity)
                if args.command == "add":
                    inventory[sku] = inventory.get(sku, 0) + quantity
                else:
                    if sku not in inventory: raise InventoryError(f"unknown SKU: {sku}")
                    if quantity > inventory[sku]: raise InventoryError(f"insufficient stock: {sku}")
                    inventory[sku] -= quantity
                    if inventory[sku] == 0: del inventory[sku]
                save_inventory(path, inventory)
                output = {"sku": sku, "quantity": inventory.get(sku, 0)}
    except InventoryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(output, separators=(",", ":")))
    return 0
