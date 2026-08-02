#!/usr/bin/env python
"""Every cross-module getter must take a sequence, not a single id.

A singular get_x(id) is the thing that gets called inside a loop. Making the
batched form the only form available means the N+1 is not merely discouraged,
it is unwritable.
"""
import ast
import pathlib
import sys

SEQ_HINTS = ("Sequence", "Iterable", "list", "List", "set", "tuple", "Collection")
EXEMPT = {"build_navigation", "active_module_codes", "search"}


def main() -> int:
    bad = []
    for path in sorted(pathlib.Path("modules").glob("*/contracts.py")):
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
                continue
            if node.name in EXEMPT:
                continue
            if not node.name.startswith("get_"):
                continue
            args = [a for a in node.args.args if a.arg != "self"]
            if not args:
                continue
            first = args[0]
            ann = ast.unparse(first.annotation) if first.annotation else ""
            if not any(h in ann for h in SEQ_HINTS):
                bad.append(f"{path}:{node.lineno} {node.name}({first.arg}: {ann or '?'})")

    for b in bad:
        print(f"singular contract getter: {b}", file=sys.stderr)
    if bad:
        print("\nContract getters must be plural — take a sequence of ids.",
              file=sys.stderr)
        return 1
    print("all contract getters are plural")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
