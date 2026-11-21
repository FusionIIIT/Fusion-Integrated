#!/usr/bin/env python
"""Generate the FTS architecture & traceability reference document.

Validates that every live CFR, AFR, Use Case, Business Rule, and Workflow
identifier resolves to an exact file and line in modules/fts/.
Exits non-zero if any resolution fails.

Usage:
    .venv/bin/python ops/docs/fts_reference.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS_FILE = ROOT / "docs" / "07-fts" / "fts-reference.md"

# 12 Consolidated Requirements (CFRs)
CFRS = [
    (
        "CFR-FTS-001",
        "Persistent Collaborative Record Lifecycle",
        "modules/fts/models.py",
        14,
        "FTSFile composite record",
    ),
    (
        "CFR-FTS-002",
        "Employee Operational Access vs Admin Governance",
        "modules/fts/registry.py",
        53,
        "Role grants and permissions",
    ),
    (
        "CFR-FTS-003",
        "File Creation with Initial Comment and Attachments",
        "modules/fts/services/drafts.py",
        22,
        "create_file_draft service",
    ),
    (
        "CFR-FTS-004",
        "Pre-Circulation Draft Management and Transition",
        "modules/fts/services/drafts.py",
        99,
        "update_file_draft service",
    ),
    (
        "CFR-FTS-005",
        "File Forwarding and Return Movement Handling",
        "modules/fts/services/movements.py",
        22,
        "forward_file service",
    ),
    (
        "CFR-FTS-006",
        "Inbox and Outbox Circulation Management",
        "modules/fts/selectors/inbox_outbox.py",
        13,
        "get_user_inbox_files selector",
    ),
    (
        "CFR-FTS-007",
        "Complete Chronological Movement Tracking History",
        "modules/fts/selectors/movements.py",
        9,
        "get_file_movement_history selector",
    ),
    (
        "CFR-FTS-008",
        "Owner-Controlled Archival of Completed Files",
        "modules/fts/services/archival.py",
        17,
        "archive_file service",
    ),
    (
        "CFR-FTS-009",
        "Role-Based and File-Association Authorization",
        "modules/fts/domain/workflow.py",
        89,
        "can_forward_file domain guard",
    ),
    (
        "CFR-FTS-010",
        "Audit Records and Chronological Versioning",
        "modules/fts/models.py",
        66,
        "FTSMovement audit trail model",
    ),
    (
        "CFR-FTS-011",
        "File and Role Notification Event Triggers",
        "modules/fts/services/movements.py",
        94,
        "return_file service",
    ),
    (
        "CFR-FTS-012",
        "Inter-Module Workflow Support APIs",
        "modules/fts/contracts.py",
        29,
        "get_files_by_uins contract",
    ),
]

# 72 Atomic Requirements (AFRs)
AFRS = [
    ("AFR-FTS-001", "Persistent composite file object", "modules/fts/models.py", 14),
    ("AFR-FTS-002", "Preserve circulated file contents", "modules/fts/models.py", 14),
    ("AFR-FTS-003", "Owner-controlled file archival", "modules/fts/services/archival.py", 17),
    ("AFR-FTS-004", "Lifecycle traceability of files", "modules/fts/selectors/movements.py", 9),
    ("AFR-FTS-005", "Institute employee operational users", "modules/fts/registry.py", 72),
    ("AFR-FTS-006", "System admin governance context", "modules/fts/registry.py", 53),
    ("AFR-FTS-007", "System admin usage monitoring", "modules/fts/selectors/inbox_outbox.py", 13),
    ("AFR-FTS-008", "System admin audit oversight", "modules/fts/selectors/movements.py", 9),
    (
        "AFR-FTS-009",
        "Admin excluded from routine file processing",
        "modules/fts/domain/workflow.py",
        89,
    ),
    ("AFR-FTS-010", "Role context selection for employees", "modules/fts/api/views.py", 38),
    (
        "AFR-FTS-011",
        "Employee file creation under assigned role",
        "modules/fts/services/drafts.py",
        22,
    ),
    ("AFR-FTS-012", "Mandatory initial comment on creation", "modules/fts/domain/workflow.py", 41),
    ("AFR-FTS-013", "Optional attachments on file creation", "modules/fts/models.py", 121),
    ("AFR-FTS-014", "Save newly created file as draft", "modules/fts/services/drafts.py", 22),
    ("AFR-FTS-015", "Edit saved draft before submission", "modules/fts/services/drafts.py", 99),
    ("AFR-FTS-016", "Discard draft before submission", "modules/fts/services/drafts.py", 148),
    ("AFR-FTS-017", "Prevent deletion of circulated files", "modules/fts/domain/workflow.py", 180),
    (
        "AFR-FTS-018",
        "Transition draft to circulated state",
        "modules/fts/services/movements.py",
        22,
    ),
    (
        "AFR-FTS-019",
        "Preserve comments and attachments after circulation",
        "modules/fts/models.py",
        96,
    ),
    (
        "AFR-FTS-020",
        "Send file to another institute employee",
        "modules/fts/services/movements.py",
        22,
    ),
    (
        "AFR-FTS-021",
        "Send file regardless of receiver role",
        "modules/fts/services/movements.py",
        22,
    ),
    (
        "AFR-FTS-022",
        "Mandatory movement comment for forward and return",
        "modules/fts/domain/workflow.py",
        89,
    ),
    ("AFR-FTS-023", "Optional attachments during file movement", "modules/fts/models.py", 121),
    ("AFR-FTS-024", "Recipient forward received file", "modules/fts/domain/workflow.py", 89),
    (
        "AFR-FTS-025",
        "Recipient return received file to sender",
        "modules/fts/domain/workflow.py",
        120,
    ),
    (
        "AFR-FTS-026",
        "Record forward action chronologically",
        "modules/fts/services/movements.py",
        22,
    ),
    (
        "AFR-FTS-027",
        "Record return action chronologically",
        "modules/fts/services/movements.py",
        94,
    ),
    (
        "AFR-FTS-028",
        "Update current holder after movement",
        "modules/fts/services/movements.py",
        22,
    ),
    ("AFR-FTS-029", "Show received files in Inbox", "modules/fts/selectors/inbox_outbox.py", 13),
    ("AFR-FTS-030", "Show sent files in Outbox", "modules/fts/selectors/inbox_outbox.py", 43),
    ("AFR-FTS-031", "View and open files from Inbox", "modules/fts/selectors/inbox_outbox.py", 13),
    ("AFR-FTS-032", "View and open files from Outbox", "modules/fts/selectors/inbox_outbox.py", 43),
    (
        "AFR-FTS-033",
        "Act on actionable files from Inbox/Outbox",
        "modules/fts/domain/workflow.py",
        89,
    ),
    (
        "AFR-FTS-034",
        "Keep files accessible until owner archives",
        "modules/fts/selectors/inbox_outbox.py",
        13,
    ),
    (
        "AFR-FTS-035",
        "Complete movement history from creation onward",
        "modules/fts/selectors/movements.py",
        9,
    ),
    ("AFR-FTS-036", "Record sender details for movement event", "modules/fts/models.py", 66),
    ("AFR-FTS-037", "Record receiver details for movement event", "modules/fts/models.py", 66),
    ("AFR-FTS-038", "Record timestamps for movement event", "modules/fts/models.py", 66),
    ("AFR-FTS-039", "Record comments at each movement event", "modules/fts/models.py", 96),
    ("AFR-FTS-040", "Record attachments at each movement event", "modules/fts/models.py", 121),
    (
        "AFR-FTS-041",
        "Allow associated users to view tracking history",
        "modules/fts/selectors/movements.py",
        9,
    ),
    ("AFR-FTS-042", "Allow file owner to archive file", "modules/fts/services/archival.py", 17),
    (
        "AFR-FTS-043",
        "Prevent non-owners from archiving file",
        "modules/fts/domain/workflow.py",
        154,
    ),
    (
        "AFR-FTS-044",
        "Archival completes collaborative workflow",
        "modules/fts/services/archival.py",
        17,
    ),
    ("AFR-FTS-045", "Permanently store readable archived files", "modules/fts/models.py", 14),
    (
        "AFR-FTS-046",
        "Prevent modification of archived files",
        "modules/fts/domain/workflow.py",
        180,
    ),
    ("AFR-FTS-047", "Prevent forwarding of archived files", "modules/fts/domain/workflow.py", 89),
    ("AFR-FTS-048", "Role-based access control for file operations", "modules/fts/registry.py", 53),
    ("AFR-FTS-049", "Access only authorized files", "modules/fts/selectors/inbox_outbox.py", 13),
    ("AFR-FTS-050", "Act only on authorized files", "modules/fts/domain/workflow.py", 89),
    ("AFR-FTS-051", "Preserve file ownership across role switching", "modules/fts/models.py", 14),
    ("AFR-FTS-052", "Preserve audit history across role switching", "modules/fts/models.py", 66),
    ("AFR-FTS-053", "Restrict sensitive actions by assigned roles", "modules/fts/registry.py", 53),
    ("AFR-FTS-054", "Audit log for file creation", "modules/fts/services/drafts.py", 22),
    ("AFR-FTS-055", "Audit log for comments added", "modules/fts/models.py", 96),
    ("AFR-FTS-056", "Audit log for attachments added", "modules/fts/models.py", 121),
    ("AFR-FTS-057", "Audit log for forwarding actions", "modules/fts/services/movements.py", 22),
    ("AFR-FTS-058", "Audit log for return actions", "modules/fts/services/movements.py", 94),
    ("AFR-FTS-059", "Audit log for archival actions", "modules/fts/services/archival.py", 17),
    (
        "AFR-FTS-060",
        "Implicit versioning via chronological updates",
        "modules/fts/selectors/movements.py",
        9,
    ),
    (
        "AFR-FTS-061",
        "Generate notification when file is received",
        "modules/fts/services/movements.py",
        22,
    ),
    (
        "AFR-FTS-062",
        "Generate notification when file is forwarded",
        "modules/fts/services/movements.py",
        22,
    ),
    (
        "AFR-FTS-063",
        "Generate notification when file is returned",
        "modules/fts/services/movements.py",
        94,
    ),
    (
        "AFR-FTS-064",
        "Generate notification when file is archived",
        "modules/fts/services/archival.py",
        17,
    ),
    (
        "AFR-FTS-065",
        "Generate notification on role assignment/reassignment",
        "modules/fts/registry.py",
        72,
    ),
    (
        "AFR-FTS-066",
        "Deliver notifications via integrated mechanism",
        "modules/fts/services/movements.py",
        22,
    ),
    ("AFR-FTS-067", "APIs for module-specific workflows", "modules/fts/contracts.py", 29),
    ("AFR-FTS-068", "APIs for approval chains", "modules/fts/contracts.py", 54),
    ("AFR-FTS-069", "APIs for file-based request tracking", "modules/fts/contracts.py", 29),
    ("AFR-FTS-070", "Apply RBAC to inter-module integrations", "modules/fts/contracts.py", 29),
    (
        "AFR-FTS-071",
        "Apply audit requirements to inter-module integrations",
        "modules/fts/contracts.py",
        54,
    ),
    (
        "AFR-FTS-072",
        "Consuming modules define domain-specific approval policy",
        "modules/fts/contracts.py",
        29,
    ),
]

# 10 Active Use Cases
USE_CASES = [
    (
        "FTS-UC-001",
        "Create New File",
        "modules/fts/services/drafts.py",
        22,
        "create_file_draft",
    ),
    (
        "FTS-UC-002",
        "Edit or Discard Draft File",
        "modules/fts/services/drafts.py",
        99,
        "update_file_draft and discard_file_draft",
    ),
    (
        "FTS-UC-003",
        "Send / Forward File to Employee",
        "modules/fts/services/movements.py",
        22,
        "forward_file",
    ),
    (
        "FTS-UC-004",
        "Return Received File",
        "modules/fts/services/movements.py",
        94,
        "return_file",
    ),
    (
        "FTS-UC-005",
        "View Inbox, Outbox, and Open Files",
        "modules/fts/selectors/inbox_outbox.py",
        13,
        "get_user_inbox_files and get_user_outbox_files",
    ),
    (
        "FTS-UC-006",
        "View File Tracking History",
        "modules/fts/selectors/movements.py",
        9,
        "get_file_movement_history",
    ),
    (
        "FTS-UC-007",
        "Archive Completed File",
        "modules/fts/services/archival.py",
        17,
        "archive_file",
    ),
    (
        "FTS-UC-008",
        "Select Assigned Role Context for FTS",
        "modules/fts/api/views.py",
        38,
        "_get_current_user_id and role switching",
    ),
    (
        "FTS-UC-009",
        "Administer FTS User Access Context",
        "modules/fts/registry.py",
        53,
        "PERMISSIONS and ROLE_GRANTS governance",
    ),
    (
        "FTS-UC-010",
        "Use FTS Workflow-Support APIs",
        "modules/fts/contracts.py",
        29,
        "get_files_by_uins and get_active_inbox_files_for_employees",
    ),
]

# 14 Active Business Rules
BUSINESS_RULES = [
    (
        "BR-FTS-001",
        "Institute Employee Operational Access Rule",
        "modules/fts/registry.py",
        72,
        "ROLE_GRANTS restriction to faculty and staff",
    ),
    (
        "BR-FTS-002",
        "Role Switching Preservation Rule",
        "modules/fts/models.py",
        14,
        "Immutable creator_id and audit trail across role switch",
    ),
    (
        "BR-FTS-003",
        "Persistent Composite File Rule",
        "modules/fts/models.py",
        14,
        "FTSFile persistence with comments and attachments",
    ),
    (
        "BR-FTS-004",
        "Initial Comment Requirement",
        "modules/fts/domain/workflow.py",
        41,
        "validate_initial_file_data mandatory comment check",
    ),
    (
        "BR-FTS-005",
        "Draft Boundary Rule",
        "modules/fts/domain/workflow.py",
        180,
        "can_edit_draft state check",
    ),
    (
        "BR-FTS-006",
        "File-Movement Comment Requirement",
        "modules/fts/domain/workflow.py",
        89,
        "can_forward_file and can_return_file comment check",
    ),
    (
        "BR-FTS-007",
        "Receiver and Return Eligibility Rule",
        "modules/fts/domain/workflow.py",
        120,
        "can_return_file predecessor check",
    ),
    (
        "BR-FTS-008",
        "Chronological Movement Record Rule",
        "modules/fts/services/movements.py",
        22,
        "forward_file movement and comment creation",
    ),
    (
        "BR-FTS-009",
        "Associated File Access Rule",
        "modules/fts/selectors/inbox_outbox.py",
        13,
        "Inbox and Outbox user association query",
    ),
    (
        "BR-FTS-010",
        "Role-Based Access and Sensitive Action Rule",
        "modules/fts/registry.py",
        53,
        "PERMISSIONS list definition",
    ),
    (
        "BR-FTS-011",
        "Audit Log and Chronological Versioning Rule",
        "modules/fts/selectors/movements.py",
        9,
        "get_file_movement_history chronological ordering",
    ),
    (
        "BR-FTS-012",
        "Archival Rule",
        "modules/fts/domain/workflow.py",
        154,
        "can_archive_file owner-only check",
    ),
    (
        "BR-FTS-013",
        "Notification Trigger and Delivery Boundary Rule",
        "modules/fts/services/movements.py",
        94,
        "return_file and forward_file event points",
    ),
    (
        "BR-FTS-014",
        "FTS Integration Boundary Rule",
        "modules/fts/contracts.py",
        29,
        "Plural contract endpoints without consuming logic",
    ),
]

# 8 Basis + 2 Composite Workflows
WORKFLOWS = [
    (
        "BW-FTS-01",
        "Forward File to Recipient — Zero Onward Traversal",
        "Basis",
        "modules/fts/services/movements.py",
        22,
        "Single-hop forward transition",
    ),
    (
        "BW-FTS-02",
        "Onward Forwarding — One Loop Traversal",
        "Basis",
        "modules/fts/services/movements.py",
        22,
        "Multi-hop onward forward loop",
    ),
    (
        "BW-FTS-03",
        "Return File to Previous Sender",
        "Basis",
        "modules/fts/services/movements.py",
        94,
        "Return transition to predecessor",
    ),
    (
        "BW-FTS-04",
        "Archive Completed Circulated File",
        "Basis",
        "modules/fts/services/archival.py",
        17,
        "Lifecycle-closing archival transition",
    ),
    (
        "BW-FTS-05",
        "Prepare and Circulate New File — Zero Draft-Edit Traversal",
        "Basis",
        "modules/fts/services/drafts.py",
        22,
        "Direct draft to circulation",
    ),
    (
        "BW-FTS-06",
        "Prepare and Circulate New File — One Draft-Edit Traversal",
        "Basis",
        "modules/fts/services/drafts.py",
        99,
        "Draft edit then circulation",
    ),
    (
        "BW-FTS-07",
        "Create and Discard Draft — Zero Draft-Edit Traversal",
        "Basis",
        "modules/fts/services/drafts.py",
        148,
        "Immediate draft discard",
    ),
    (
        "BW-FTS-08",
        "Edit Once and Discard Draft — One Draft-Edit Traversal",
        "Basis",
        "modules/fts/services/drafts.py",
        148,
        "Draft edit then discard",
    ),
    (
        "CW-FTS-01",
        "Collaborative File Circulation and Completion",
        "Composite",
        "modules/fts/services/movements.py",
        22,
        "Forward, return, and archive sequence",
    ),
    (
        "CW-FTS-02",
        "New File Preparation and Initial Outcome",
        "Composite",
        "modules/fts/services/drafts.py",
        22,
        "Draft creation, edit, and outcome sequence",
    ),
]


def verify_links() -> list[str]:
    """Verifies that every declared file and line link physically resolves."""
    errors = []
    all_items = []
    all_items.extend([(i[0], i[2], i[3]) for i in CFRS])
    all_items.extend([(i[0], i[2], i[3]) for i in AFRS])
    all_items.extend([(i[0], i[2], i[3]) for i in USE_CASES])
    all_items.extend([(i[0], i[2], i[3]) for i in BUSINESS_RULES])
    all_items.extend([(i[0], i[3], i[4]) for i in WORKFLOWS])

    for item_id, rel_path, line_no in all_items:
        path = ROOT / rel_path
        if not path.exists():
            errors.append(f"{item_id}: file {rel_path} does not exist.")
            continue
        try:
            line_count = len(path.read_text().splitlines())
            if line_no < 1 or line_no > line_count:
                errors.append(
                    f"{item_id}: line {line_no} out of bounds for {rel_path} ({line_count} lines)."
                )
        except OSError as e:
            errors.append(f"{item_id}: error reading {rel_path}: {e}")

    return errors


def generate_markdown() -> str:
    """Generates the reference markdown content."""
    lines = [
        "# File Tracking System (FTS) — Implementation Reference",
        "",
        "This document provides the authoritative bidirectional traceability links between",
        "all live specification identifiers (CFR, AFR, UC, BR, WF) and their concrete code",
        "enforcement points within `modules/fts/`. Compiled by `ops/docs/fts_reference.py`.",
        "",
        "## 1. Consolidated Requirements (CFRs)",
        "",
        "| CFR ID | Title | Layer | Enforcement Point | Description |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for cid, title, rel_path, line_no, desc in CFRS:
        layer = rel_path.split("/")[2] if len(rel_path.split("/")) > 2 else "module"
        lines.append(
            f"| `{cid}` | {title} | `{layer}` | "
            f"[`{rel_path}:{line_no}`](../../{rel_path}#L{line_no}) | {desc} |"
        )

    lines.extend(
        [
            "",
            "## 2. Atomic Requirements (AFRs)",
            "",
            "| AFR ID | Requirement Statement | Enforcement Point |",
            "| :--- | :--- | :--- |",
        ]
    )
    for aid, stmt, rel_path, line_no in AFRS:
        lines.append(
            f"| `{aid}` | {stmt} | [`{rel_path}:{line_no}`](../../{rel_path}#L{line_no}) |"
        )

    lines.extend(
        [
            "",
            "## 3. Use Case Specifications",
            "",
            "| Use Case ID | Name | Primary Implementation | Target Function / Construct |",
            "| :--- | :--- | :--- | :--- |",
        ]
    )
    for ucid, name, rel_path, line_no, target in USE_CASES:
        lines.append(
            f"| `{ucid}` | {name} | [`{rel_path}:{line_no}`](../../{rel_path}#L{line_no}) | "
            f"`{target}` |"
        )

    lines.extend(
        [
            "",
            "## 4. Business Rule Specifications",
            "",
            "| Rule ID | Rule Name | Enforcement Point | Rule Scope & Mechanism |",
            "| :--- | :--- | :--- | :--- |",
        ]
    )
    for brid, name, rel_path, line_no, scope in BUSINESS_RULES:
        lines.append(
            f"| `{brid}` | {name} | [`{rel_path}:{line_no}`](../../{rel_path}#L{line_no}) | "
            f"{scope} |"
        )

    lines.extend(
        [
            "",
            "## 5. Workflow Specifications",
            "",
            "| Workflow ID | Workflow Name | Category | Primary Enforcement | Description |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
    )
    for wfid, name, cat, rel_path, line_no, desc in WORKFLOWS:
        lines.append(
            f"| `{wfid}` | {name} | {cat} | "
            f"[`{rel_path}:{line_no}`](../../{rel_path}#L{line_no}) | {desc} |"
        )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    errors = verify_links()
    if errors:
        print(f"Error: {len(errors)} reference links failed to resolve:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    content = generate_markdown()
    DOCS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DOCS_FILE.write_text(content)
    print(f"Successfully validated all 118 links and updated {DOCS_FILE.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
