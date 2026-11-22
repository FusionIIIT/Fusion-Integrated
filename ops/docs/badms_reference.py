#!/usr/bin/env python
"""Generate BADMS specification-to-code traceability reference documentation.

Runs as part of review and CI quality gates.
Validates that every cited file:line link resolves in the codebase.
Outputs docs/24-badms/badms-reference.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs" / "24-badms"
OUT_FILE = DOCS_DIR / "badms-reference.md"

# Registry of live specification IDs to their concrete implementation file and line
TRACEABILITY: list[dict[str, str]] = [
    # Business Rules
    {
        "id": "BR-BA-001",
        "name": "Manual Backup Trigger Authorization",
        "file": "modules/badms/services/backups.py",
        "line": "19",
    },
    {
        "id": "BR-BA-002",
        "name": "Respective HoD Approval for Secure Archival",
        "file": "modules/badms/services/archival.py",
        "line": "79",
    },
    {
        "id": "BR-BA-003",
        "name": "IT Security Encryption Authority",
        "file": "modules/badms/services/archival.py",
        "line": "153",
    },
    {
        "id": "BR-BA-004",
        "name": "SysAdmin Authoritative Classification",
        "file": "modules/badms/services/archival.py",
        "line": "116",
    },
    {
        "id": "BR-BA-005",
        "name": "Sensitive Restoration Approval",
        "file": "modules/badms/services/restoration.py",
        "line": "42",
    },
    {
        "id": "BR-BA-006",
        "name": "Initial Data Classification and Default",
        "file": "modules/badms/models/archival.py",
        "line": "44",
    },
    {
        "id": "BR-BA-007",
        "name": "Sensitive Data Encryption",
        "file": "modules/badms/domain/crypto.py",
        "line": "60",
    },
    {
        "id": "BR-BA-008",
        "name": "Retention by Classification",
        "file": "modules/badms/domain/retention.py",
        "line": "25",
    },
    {
        "id": "BR-BA-009",
        "name": "HoD Approval for Storage Extension",
        "file": "modules/badms/services/storage.py",
        "line": "69",
    },
    {
        "id": "BR-BA-010",
        "name": "HoD Department Scope",
        "file": "modules/badms/selectors/scoping.py",
        "line": "33",
    },
    {
        "id": "BR-BA-011",
        "name": "Local Schedule Overrides Global",
        "file": "modules/badms/domain/schedules.py",
        "line": "23",
    },
    {
        "id": "BR-BA-012",
        "name": "Schedule Parameter Validation",
        "file": "modules/badms/domain/schedules.py",
        "line": "14",
    },
    {
        "id": "BR-BA-013",
        "name": "Scheduled Repository Reachability",
        "file": "modules/badms/services/backups.py",
        "line": "45",
    },
    {
        "id": "BR-BA-014",
        "name": "Backup Failure Alert SLA",
        "file": "modules/badms/services/notifications.py",
        "line": "4",
    },
    {
        "id": "BR-BA-015",
        "name": "Repeated Failure Escalation",
        "file": "modules/badms/services/notifications.py",
        "line": "9",
    },
    {
        "id": "BR-BA-016",
        "name": "Storage-Extension Usage Validation",
        "file": "modules/badms/domain/storage.py",
        "line": "29",
    },
    {
        "id": "BR-BA-017",
        "name": "Storage-Extension Decision Criteria",
        "file": "modules/badms/services/storage.py",
        "line": "87",
    },
    {
        "id": "BR-BA-018",
        "name": "Special Archival Super Admin Authority",
        "file": "modules/badms/services/archival.py",
        "line": "184",
    },
    {
        "id": "BR-BA-019",
        "name": "Super Admin Global Backup Authority",
        "file": "modules/badms/services/schedules.py",
        "line": "14",
    },
    {
        "id": "BR-BA-020",
        "name": "Protected Information Access Scope",
        "file": "modules/badms/selectors/scoping.py",
        "line": "48",
    },
    {
        "id": "BR-BA-021",
        "name": "IT Security RBAC Authority",
        "file": "modules/badms/registry.py",
        "line": "158",
    },
    # Use Cases
    {
        "id": "BA-UC-001",
        "name": "Trigger Manual Backup",
        "file": "modules/badms/api/views.py",
        "line": "36",
    },
    {
        "id": "BA-UC-002",
        "name": "Submit Secure Archival Request",
        "file": "modules/badms/api/views.py",
        "line": "119",
    },
    {
        "id": "BA-UC-003",
        "name": "Decide Secure Archival Request",
        "file": "modules/badms/api/views.py",
        "line": "135",
    },
    {
        "id": "BA-UC-004",
        "name": "Classify Archival Request",
        "file": "modules/badms/api/views.py",
        "line": "147",
    },
    {
        "id": "BA-UC-005",
        "name": "Configure Sensitive Encryption",
        "file": "modules/badms/api/views.py",
        "line": "161",
    },
    {
        "id": "BA-UC-006",
        "name": "Define Backup Schedule",
        "file": "modules/badms/api/views.py",
        "line": "62",
    },
    {
        "id": "BA-UC-007",
        "name": "Submit Storage Extension Request",
        "file": "modules/badms/api/views.py",
        "line": "226",
    },
    {
        "id": "BA-UC-008",
        "name": "Decide Storage Extension Request",
        "file": "modules/badms/api/views.py",
        "line": "238",
    },
    {
        "id": "BA-UC-009",
        "name": "Perform Special Archival",
        "file": "modules/badms/api/views.py",
        "line": "173",
    },
    {
        "id": "BA-UC-010",
        "name": "Submit Restoration Request",
        "file": "modules/badms/api/views.py",
        "line": "281",
    },
    {
        "id": "BA-UC-011",
        "name": "Decide Restoration Request",
        "file": "modules/badms/api/views.py",
        "line": "297",
    },
    {
        "id": "BA-UC-012",
        "name": "Execute Data Restoration",
        "file": "modules/badms/api/views.py",
        "line": "309",
    },
    {
        "id": "BA-UC-013",
        "name": "Automatic Scheduled Backup Dispatch",
        "file": "modules/badms/tasks.py",
        "line": "15",
    },
    {
        "id": "BA-UC-014",
        "name": "Enforce Failure Alert SLA",
        "file": "modules/badms/tasks.py",
        "line": "36",
    },
    {
        "id": "BA-UC-015",
        "name": "Monitor User Storage Thresholds",
        "file": "modules/badms/tasks.py",
        "line": "52",
    },
    {
        "id": "BA-UC-016",
        "name": "Purge Expired Archives",
        "file": "modules/badms/tasks.py",
        "line": "65",
    },
    {
        "id": "BA-UC-017",
        "name": "Query Backup Records",
        "file": "modules/badms/api/views.py",
        "line": "24",
    },
    {
        "id": "BA-UC-018",
        "name": "Query Archival Requests",
        "file": "modules/badms/api/views.py",
        "line": "107",
    },
    {
        "id": "BA-UC-019",
        "name": "Query Storage Extension Requests",
        "file": "modules/badms/api/views.py",
        "line": "214",
    },
    {
        "id": "BA-UC-020",
        "name": "Query Restoration Requests",
        "file": "modules/badms/api/views.py",
        "line": "269",
    },
    {
        "id": "BA-UC-021",
        "name": "Query Audit Events",
        "file": "modules/badms/api/views.py",
        "line": "321",
    },
    {
        "id": "BA-UC-022",
        "name": "Query Departmental Reports",
        "file": "modules/badms/api/views.py",
        "line": "333",
    },
    {
        "id": "BA-UC-023",
        "name": "Query User Quota Status",
        "file": "modules/badms/api/views.py",
        "line": "253",
    },
    # Composite Functional Requirements
    {
        "id": "CFR-BA-001",
        "name": "Point-in-Time Database Backup",
        "file": "modules/badms/services/backups.py",
        "line": "19",
    },
    {
        "id": "CFR-BA-002",
        "name": "Automated Scheduled Backup Dispatch",
        "file": "modules/badms/tasks.py",
        "line": "15",
    },
    {
        "id": "CFR-BA-003",
        "name": "Data Retention Policy Enforcement",
        "file": "modules/badms/domain/retention.py",
        "line": "25",
    },
    {
        "id": "CFR-BA-004",
        "name": "Post-Dump Checksum Verification",
        "file": "modules/badms/domain/crypto.py",
        "line": "46",
    },
    {
        "id": "CFR-BA-005",
        "name": "Backup Failure Alert SLA Notification",
        "file": "modules/badms/services/notifications.py",
        "line": "4",
    },
    {
        "id": "CFR-BA-006",
        "name": "Data Restoration Execution",
        "file": "modules/badms/services/restoration.py",
        "line": "67",
    },
    {
        "id": "CFR-BA-007",
        "name": "Sensitive Restoration Approval Workflow",
        "file": "modules/badms/services/restoration.py",
        "line": "42",
    },
    {
        "id": "CFR-BA-008",
        "name": "Structured Departmental Archival",
        "file": "modules/badms/services/archival.py",
        "line": "20",
    },
    {
        "id": "CFR-BA-009",
        "name": "Multi-Tier Data Classification",
        "file": "modules/badms/services/archival.py",
        "line": "116",
    },
    {
        "id": "CFR-BA-010",
        "name": "Sensitive Archive AES-256 Encryption",
        "file": "modules/badms/services/archival.py",
        "line": "153",
    },
    {
        "id": "CFR-BA-011",
        "name": "User Storage Quota Tracking",
        "file": "modules/badms/services/storage.py",
        "line": "21",
    },
    {
        "id": "CFR-BA-012",
        "name": "Storage Extension Request Lifecycle",
        "file": "modules/badms/services/storage.py",
        "line": "60",
    },
    {
        "id": "CFR-BA-013",
        "name": "Policy-Governed Archive Purge",
        "file": "modules/badms/tasks.py",
        "line": "65",
    },
    {
        "id": "CFR-BA-014",
        "name": "Scoped Search and Filter Catalog",
        "file": "modules/badms/selectors/scoping.py",
        "line": "33",
    },
    {
        "id": "CFR-BA-015",
        "name": "Tamper-Evident Audit Logging",
        "file": "modules/badms/services/audit.py",
        "line": "10",
    },
    {
        "id": "CFR-BA-016",
        "name": "Departmental Backup Analytics",
        "file": "modules/badms/api/views.py",
        "line": "333",
    },
    {
        "id": "CFR-BA-017",
        "name": "Role-Based Access Control Delegation",
        "file": "modules/badms/registry.py",
        "line": "165",
    },
    {
        "id": "CFR-BA-018",
        "name": "Super Admin Global Authority",
        "file": "modules/badms/services/schedules.py",
        "line": "14",
    },
    {
        "id": "CFR-BA-019",
        "name": "Special Offline Archival Handling",
        "file": "modules/badms/services/archival.py",
        "line": "184",
    },
]


def validate_links() -> None:
    errors: list[str] = []
    for item in TRACEABILITY:
        target_path = ROOT / item["file"]
        if not target_path.exists():
            errors.append(f"File not found for {item['id']}: {item['file']}")
            continue
        try:
            line_no = int(item["line"])
            lines = target_path.read_text(encoding="utf-8").splitlines()
            if line_no > len(lines):
                errors.append(
                    f"Line {line_no} out of bounds for {item['id']} "
                    f"in {item['file']} ({len(lines)} lines)"
                )
        except ValueError:
            errors.append(f"Invalid line number {item['line']} for {item['id']}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)


def generate_reference_markdown() -> str:
    md = [
        "# BADMS Specification Traceability Reference",
        "",
        "This document is automatically generated by `ops/docs/badms_reference.py`.",
        "It maps every live requirement, rule, and use case ID to its concrete implementation.",
        "",
        "| ID | Requirement / Rule / Use Case Name | Implementation File & Line |",
        "|---|---|---|",
    ]
    for item in TRACEABILITY:
        link = f"[{item['file']}:{item['line']}](../../{item['file']}#L{item['line']})"
        md.append(f"| `{item['id']}` | {item['name']} | {link} |")
    md.append("")
    return "\n".join(md)


def main():
    validate_links()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    content = generate_reference_markdown()
    OUT_FILE.write_text(content, encoding="utf-8")
    print(f"Generated {OUT_FILE} with {len(TRACEABILITY)} resolved traceability links.")


if __name__ == "__main__":
    main()
