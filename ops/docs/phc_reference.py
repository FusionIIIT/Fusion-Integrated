from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT = ROOT / "docs/21-phc/phc-blueprint.md"
OUTPUT = ROOT / "docs/21-phc/phc-reference.md"
IDENTIFIER = re.compile(
    r"\b(?:PHC-BR-\d+|PHC-UC-\d+|BW-PHC-\d+|CW-PHC-\d+|CFR-PHC-\d+|AFR-PHC-\d+)\b"
)
SOURCE = re.compile(r"((?:modules|client/src/modules)/[A-Za-z0-9_./-]+)(?:::(\w+))?")


def table_rows() -> dict[str, str]:
    text = BLUEPRINT.read_text()
    section = text.split("## (a) Traceability table", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        cells = line.split("|")
        if len(cells) != 7:
            continue
        identifier = cells[1].strip().strip("`")
        if IDENTIFIER.fullmatch(identifier):
            rows[identifier] = cells[4].strip()
    return rows


def resolve_source(enforcement: str) -> tuple[Path, int] | None:
    for raw_path, symbol in SOURCE.findall(enforcement):
        candidate = ROOT / raw_path.rstrip(".")
        if not candidate.is_file():
            continue
        lines = candidate.read_text().splitlines()
        if symbol:
            line = next((n for n, value in enumerate(lines, 1)
                         if re.search(rf"\b{re.escape(symbol)}\b", value)), None)
        else:
            line = next((n for n, value in enumerate(lines, 1)
                         if re.match(r"\s*(?:class|def)\s+", value)), 1)
        if line:
            return candidate, line
    return None


def resolve_test(identifier: str) -> tuple[Path, int] | None:
    for candidate in sorted((ROOT / "modules/phc/tests").glob("*.py")):
        for line_number, line in enumerate(candidate.read_text().splitlines(), 1):
            if identifier in line:
                return candidate, line_number
    return None


def link(path: Path, line: int) -> str:
    relative = Path("..") / ".." / path.relative_to(ROOT)
    target = f"{relative.as_posix()}#L{line}"
    return f"[{path.relative_to(ROOT).as_posix()}:{line}]({target})"


def main() -> int:
    rows = table_rows()
    failures = []
    output = [
        "# PHC specification reference",
        "",
        "Each live specification ID links to an implementation location and its test citation.",
        "",
        "| ID | Implementation | Test |",
        "|---|---|---|",
    ]
    for identifier, enforcement in sorted(rows.items()):
        source = resolve_source(enforcement)
        test = resolve_test(identifier)
        if source is None:
            failures.append(f"{identifier}: no existing implementation path in {enforcement!r}")
        if test is None:
            failures.append(f"{identifier}: no test citation under modules/phc/tests")
        if source and test:
            output.append(f"| `{identifier}` | {link(*source)} | {link(*test)} |")
    if failures:
        for failure in failures:
            print(failure)
        return 1
    OUTPUT.write_text("\n".join(output) + "\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(rows)} live requirement links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
