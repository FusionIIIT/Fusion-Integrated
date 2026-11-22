#!/usr/bin/env python
"""Generate filetracking-reference.md with file:line traceability links.

Verifies that all live specification IDs resolve to actual lines of code.
Exits non-zero if any file does not exist or line is invalid.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = ROOT / "docs" / "09-filetracking" / "filetracking-reference.md"

MAPPINGS = [
    ("CFR-FTS-001", "File Creation and Draft State", "modules/filetracking/services/files.py:63"),
    ("CFR-FTS-002", "Subject & Content Definition", "modules/filetracking/domain/rules.py:24"),
    ("CFR-FTS-003", "Mandatory Initial Note/Comment", "modules/filetracking/domain/rules.py:24"),
    (
        "CFR-FTS-004",
        "File Circulation & Transfer",
        "modules/filetracking/services/files.py:291",
    ),
    (
        "CFR-FTS-005",
        "Sequential Forwarding",
        "modules/filetracking/services/files.py:330",
    ),
    ("CFR-FTS-006", "Single Current Holder Invariant", "modules/filetracking/models/files.py:26"),
    (
        "CFR-FTS-007",
        "Return to Previous Sender",
        "modules/filetracking/services/files.py:417",
    ),
    (
        "CFR-FTS-008",
        "Mandatory Note on Forward/Return",
        "modules/filetracking/domain/rules.py:32",
    ),
    ("CFR-FTS-009", "Inbox and Outbox Views", "modules/filetracking/selectors/files.py:10"),
    (
        "CFR-FTS-010",
        "Full Lifecycle Movement History",
        "modules/filetracking/selectors/files.py:70",
    ),
    ("CFR-FTS-011", "File Archival & Final Closure", "modules/filetracking/services/files.py:542"),
    (
        "CFR-FTS-012",
        "Draft Discard & Cleanup",
        "modules/filetracking/services/files.py:246",
    ),
    ("BR-FTS-001", "Unique Monotonic File ID", "modules/filetracking/services/files.py:35"),
    ("BR-FTS-002", "Single Active Custodian", "modules/filetracking/domain/rules.py:40"),
    ("BR-FTS-003", "Holder-Only Forwarding", "modules/filetracking/services/files.py:311"),
    ("BR-FTS-004", "Mandatory Movement Remarks", "modules/filetracking/domain/rules.py:24"),
    ("BR-FTS-005", "Draft Discard Restraint", "modules/filetracking/domain/rules.py:56"),
    ("BR-FTS-006", "Append-Only Movement Sequence", "modules/filetracking/models/movements.py:23"),
    ("BR-FTS-007", "Return Exclusively to Prior", "modules/filetracking/domain/rules.py:48"),
    ("BR-FTS-008", "Sequential Timestamp Auditing", "modules/filetracking/models/movements.py:24"),
    (
        "BR-FTS-009",
        "Association Scoping (Yield 404)",
        "modules/filetracking/selectors/scoping.py:20",
    ),
    ("BR-FTS-010", "Attachment Size Constraints", "modules/filetracking/domain/rules.py:80"),
    ("BR-FTS-011", "Immutable System Audit Log", "modules/filetracking/services/audit.py:10"),
    ("BR-FTS-012", "Owner-Only File Archival", "modules/filetracking/domain/rules.py:72"),
    (
        "BR-FTS-013",
        "Decoupled Outbox Notifications",
        "modules/filetracking/services/notifications.py:30",
    ),
    ("BR-FTS-014", "Pure Framework-Free Domain", "modules/filetracking/domain/state_machine.py:1"),
    (
        "FTS-UC-001",
        "Create and Circulate File",
        "modules/filetracking/services/files.py:63",
    ),
    ("FTS-UC-002", "Discard Uncirculated Draft", "modules/filetracking/services/files.py:246"),
    ("FTS-UC-003", "Update Uncirculated Draft", "modules/filetracking/services/files.py:174"),
    ("FTS-UC-004", "Forward Received File", "modules/filetracking/services/files.py:291"),
    ("FTS-UC-005", "Return Received File", "modules/filetracking/services/files.py:417"),
    ("FTS-UC-006", "View Movement History", "modules/filetracking/selectors/files.py:70"),
    ("FTS-UC-007", "Archive Circulated File", "modules/filetracking/services/files.py:542"),
    ("FTS-UC-008", "View Inbox Files", "modules/filetracking/selectors/files.py:10"),
    ("FTS-UC-009", "View Outbox Files", "modules/filetracking/selectors/files.py:22"),
    ("FTS-UC-010", "View Archived Files", "modules/filetracking/selectors/files.py:52"),
    (
        "BW-FTS-01",
        "Basis Workflow: Initial Creation",
        "modules/filetracking/domain/state_machine.py:17",
    ),
    (
        "BW-FTS-02",
        "Basis Workflow: Forward Across Actors",
        "modules/filetracking/domain/state_machine.py:20",
    ),
    (
        "BW-FTS-03",
        "Basis Workflow: Return to Previous",
        "modules/filetracking/domain/state_machine.py:21",
    ),
    (
        "BW-FTS-04",
        "Basis Workflow: Final Archival",
        "modules/filetracking/domain/state_machine.py:24",
    ),
    (
        "BW-FTS-05",
        "Basis Workflow: Create Draft",
        "modules/filetracking/domain/state_machine.py:15",
    ),
    (
        "BW-FTS-06",
        "Basis Workflow: Update Draft",
        "modules/filetracking/domain/state_machine.py:15",
    ),
    (
        "BW-FTS-07",
        "Basis Workflow: Discard Draft",
        "modules/filetracking/domain/state_machine.py:16",
    ),
    (
        "BW-FTS-08",
        "Basis Workflow: Submit Draft",
        "modules/filetracking/domain/state_machine.py:17",
    ),
    (
        "CW-FTS-01",
        "Composite Workflow: Routing Cycle",
        "modules/filetracking/tests/test_workflows.py:10",
    ),
    (
        "CW-FTS-02",
        "Composite Workflow: Draft to Circ",
        "modules/filetracking/tests/test_workflows.py:40",
    ),
]


def main():
    errors = 0
    lines = [
        "# File Tracking System (FTS-007) — Specification Traceability Reference",
        "",
        "| Specification ID | Description | Enforcement Location |",
        "| :--- | :--- | :--- |",
    ]

    for spec_id, desc, target in MAPPINGS:
        rel_file, line_str = target.split(":")
        line_no = int(line_str)
        file_path = ROOT / rel_file
        if not file_path.exists():
            print(f"ERROR: File not found: {rel_file}", file=sys.stderr)
            errors += 1
            continue
        file_lines = file_path.read_text().splitlines()
        if line_no > len(file_lines):
            print(f"ERROR: Line {line_no} out of bounds for {rel_file}", file=sys.stderr)
            errors += 1
            continue

        lines.append(f"| `{spec_id}` | {desc} | [`{target}`](../../{target}#L{line_no}) |")

    if errors > 0:
        print(f"Traceability validation failed with {errors} error(s).", file=sys.stderr)
        sys.exit(1)

    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(lines) + "\n")
    print(f"Successfully generated {DOC_PATH.relative_to(ROOT)} with {len(MAPPINGS)} links.")


if __name__ == "__main__":
    main()
