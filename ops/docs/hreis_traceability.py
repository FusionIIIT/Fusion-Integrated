"""Keep test citations distinct from verification and unresolved external requirements."""

import argparse
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/09-hreis/hreis-traceability-status.md"
ID = re.compile(r"(?:HR-(?:CFR|AFR|UC)|BR-HR|[BC]W-HR)-\d+")


def test_references():
    references = {}
    for path in sorted((ROOT / "modules/hreis/tests").glob("test_*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for node in ast.walk(ast.parse("\n".join(lines))):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            for identifier in set(ID.findall("\n".join(lines[node.lineno - 1 : node.end_lineno]))):
                references.setdefault(identifier, []).append(f"`{path.name}::{node.name}`")
    return references


def build():
    references = test_references()
    blueprint = (OUTPUT.parent / "hreis-blueprint.md").read_text(encoding="utf-8")
    entries = []
    linked = 0
    for line in blueprint.split("## 3.2", 1)[0].splitlines():
        columns = [column.strip().strip("`") for column in line.split("|")[1:-1]]
        if not columns or not ID.fullmatch(columns[0]):
            continue
        identifier, description, _, enforcement, _ = columns
        tests = references.get(identifier, [])
        linked += bool(tests)
        note = (
            ", ".join(tests) if tests else "**OPEN: external contract or source ruling required**"
        )
        entries.append(f"| `{identifier}` | {description} | {enforcement} | {note} |")
    if len(entries) != 193:
        raise ValueError("Expected exactly 193 live source IDs.")
    return "\n".join(
        [
            "# HR-EIS builder traceability checkpoint",
            "",
            "This inventories direct citations inside builder test functions; it does not certify",
            "complete behavioral coverage or replace Student 2's independent specification suites.",
            "",
            "- Live source IDs: **193**.",
            f"- IDs directly cited by a builder test: **{linked}**.",
            f"- IDs without a direct citation: **{193 - linked}**.",
            "",
            "Six source/integration obligations remain unresolved:",
            "HR-CFR-013 and HR-AFR-059/090/091/092/093.",
            "HR-AFR-092 and BR-HR-028 now have an actual public-directory-contract refresh test:",
            "IAM-owned fields refresh while HR snapshots remain unchanged; current grants",
            "control the next HTTP read. This does not establish every external exchange.",
            "No finance connection, undefined LTC return, approved gap or signature is fabricated.",
            "See hreis-reference.md for source links and the quality report for execution results.",
            "",
            "| ID | Source requirement | Current enforcement area | Builder test citations |",
            "|---|---|---|---|",
            *entries,
            "",
        ]
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    result = build()
    if options.check:
        if OUTPUT.read_text(encoding="utf-8") != result:
            raise SystemExit(
                "HR-EIS traceability is stale; run python ops/docs/hreis_traceability.py"
            )
    else:
        OUTPUT.write_text(result, encoding="utf-8")
        print("HR-EIS test citations refreshed from the live blueprint and builder test functions.")
