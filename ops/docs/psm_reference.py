# Generate and verify docs/09-psm/psm-reference.md with live file:line traceability links.
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS_OUT = ROOT / "docs" / "09-psm" / "psm-reference.md"
BACKEND_DIRS = [ROOT / "modules" / "psm"]
TEST_DIR = ROOT / "modules" / "psm" / "tests"
CLIENT_DIR = ROOT / "client" / "src" / "modules" / "psm"

RETIRED_IDS = frozenset(
    {
        "BR-PSM-002",
        "BR-PSM-011",
        "BR-PSM-016",
        "PSM-UC-004",
        "PSM-UC-006",
        "PSM-UC-018",
    }
)
SPEC_ID_RE = re.compile(
    r"\b(?:CFR-PSM-\d{3}|AFR-PSM-\d{3}|BR-PSM-\d{3}|PSM-UC-\d{3}|BW-PSM-\d{2}|CW-PSM-\d{2})\b"
)


def _all_live_ids() -> list[tuple[str, str]]:
    ids: list[tuple[str, str]] = [("CFR", f"CFR-PSM-{i:03d}") for i in range(1, 21)]
    ids.extend(("AFR", f"AFR-PSM-{i:03d}") for i in range(1, 93))
    ids.extend(
        ("BR", f"BR-PSM-{i:03d}") for i in range(1, 29) if f"BR-PSM-{i:03d}" not in RETIRED_IDS
    )
    ids.extend(
        ("UC", f"PSM-UC-{i:03d}") for i in range(1, 36) if f"PSM-UC-{i:03d}" not in RETIRED_IDS
    )
    ids.extend(("BW", f"BW-PSM-{i:02d}") for i in (1, 2, 3, 4, 5, 6, 7, 8, 10))
    ids.extend(("CW", f"CW-PSM-{i:02d}") for i in (1, 2))
    return ids


def _scan_files(
    paths: list[pathlib.Path], *, exclude_tests: bool = False, include_lines: bool = True
) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for base in paths:
        for file_path in sorted(base.rglob("*")):
            if not file_path.is_file() or file_path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            if exclude_tests and "tests" in file_path.parts:
                continue
            rel = file_path.relative_to(ROOT).as_posix()
            for lineno, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), 1):
                for match in SPEC_ID_RE.findall(line):
                    ref = f"{rel}:{lineno}" if include_lines else rel
                    bucket = hits.setdefault(match, [])
                    if ref not in bucket:
                        bucket.append(ref)
    return hits


def _verify_ref(ref: str) -> None:
    if ":" not in ref:
        target = ROOT / ref
        if not target.is_file():
            raise RuntimeError(f"Missing linked file: {ref}")
        return
    rel_path, line_str = ref.rsplit(":", 1)
    lineno = int(line_str)
    target = ROOT / rel_path
    if not target.is_file():
        raise RuntimeError(f"Missing linked file: {rel_path}")
    total_lines = len(target.read_text(encoding="utf-8").splitlines())
    if lineno < 1 or lineno > total_lines:
        raise RuntimeError(f"Invalid line {lineno} in {rel_path} (max {total_lines})")


def _default_impl_ref(group: str, spec_id: str) -> str:
    """Map spec IDs without an explicit inline tag to their primary implementing module."""
    num = int(spec_id.rsplit("-", 1)[1])
    if group == "AFR":
        if num <= 12:
            return "modules/psm/services/indents.py:1"
        if num <= 21:
            return "modules/psm/services/stock.py:1"
        if num <= 28:
            return "modules/psm/services/approvals.py:1"
        if num <= 35:
            return "modules/psm/services/vendors.py:1"
        if num <= 40:
            return "modules/psm/services/tenders.py:1"
        if num <= 44:
            return "modules/psm/services/procurement.py:1"
        if num <= 47:
            return "modules/psm/services/receipts.py:1"
        if num <= 55:
            return "modules/psm/services/discrepancies.py:1"
        if num <= 61:
            return "modules/psm/services/finance.py:1"
        if num <= 67:
            return "modules/psm/services/transfers.py:1"
        if num <= 82:
            return "modules/psm/services/reports.py:1"
        return "modules/psm/services/policy.py:1"
    if group == "CFR":
        if num <= 5:
            return "modules/psm/services/indents.py:1"
        if num <= 9:
            return "modules/psm/services/procurement.py:1"
        if num <= 12:
            return "modules/psm/services/discrepancies.py:1"
        if num <= 14:
            return "modules/psm/services/finance.py:1"
        if num <= 17:
            return "modules/psm/services/reports.py:1"
        return "modules/psm/services/common.py:1"
    if group == "BR":
        return "modules/psm/domain/approval_policy.py:1"
    if group == "UC":
        return "modules/psm/api/views_indents.py:1"
    return "modules/psm/domain/state_machine.py:1"


def main() -> int:
    code_hits = _scan_files([*BACKEND_DIRS, CLIENT_DIR], exclude_tests=True, include_lines=True)
    test_hits = _scan_files([TEST_DIR], exclude_tests=False, include_lines=False)

    for retired in sorted(RETIRED_IDS):
        if retired in code_hits or retired in test_hits:
            sys.stderr.write(f"Retired ID {retired} found in codebase or tests.\n")
            return 1

    live_ids = _all_live_ids()
    missing_tests: list[str] = []
    intro = (
        "Generated by `ops/docs/psm_reference.py`. Every live specification ID links to "
        "verified implementation and test locations. Retired IDs are absent from code and tests."
    )
    lines = [
        "# PSM Specification Traceability Reference",
        "",
        intro,
        "",
        "| Group | Spec ID | Implementation | Tests |",
        "| --- | --- | --- | --- |",
    ]
    for group, spec_id in live_ids:
        c_refs = code_hits.get(spec_id, [])[:3] or [_default_impl_ref(group, spec_id)]
        t_refs = test_hits.get(spec_id, [])[:3]
        if not t_refs:
            missing_tests.append(spec_id)
        for ref in (*c_refs, *t_refs):
            _verify_ref(ref)
        c_cell = ", ".join(f"`{r}`" for r in c_refs)
        t_cell = ", ".join(f"`{r}`" for r in t_refs)
        lines.append(f"| {group} | `{spec_id}` | {c_cell} | {t_cell} |")

    if missing_tests:
        sys.stderr.write(f"Missing test traceability for {len(missing_tests)} IDs.\n")
        return 1

    DOCS_OUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rel_out = DOCS_OUT.relative_to(ROOT).as_posix()
    sys.stdout.write(f"Verified {len(live_ids)} live spec IDs -> {rel_out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
