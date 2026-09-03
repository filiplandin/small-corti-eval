import argparse


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("command", choices=["add", "remove", "get", "list"])
    parser.add_argument("sku", nargs="?")
    parser.add_argument("quantity", nargs="?")
    parser.parse_args(argv)
    raise NotImplementedError
