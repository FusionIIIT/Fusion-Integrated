#!/usr/bin/env python
"""Generate docs/09-fts/fts-reference.md linking live spec IDs to enforcing code.

Enforces Step 7.6 of new-module-prompt.md.
Exits 0 if all links resolve; exits non-zero if any link does not exist.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC_PATH = ROOT / "docs" / "09-fts" / "fts-reference.md"

# Mapping of live spec IDs to target file and symbol/pattern
SPEC_MAP = [
    # Business Rules
    ("BR-FTS-001", "modules/fts/domain/state_machine.py", "STATE_CIRCULATED", "Single holder"),
    ("BR-FTS-002", "modules/fts/services/files.py", "create_file", "Owner retains ownership"),
    ("BR-FTS-003", "modules/fts/services/movements.py", "forward_file", "Forward custody transfer"),
    ("BR-FTS-004", "modules/fts/services/movements.py", "return_file", "Return custody back"),
    ("BR-FTS-005", "modules/fts/services/archival.py", "archive_file", "Owner-only archival"),
    ("BR-FTS-006", "modules/fts/services/movements.py", "forward_file", "Mandatory remarks"),
    ("BR-FTS-007", "modules/fts/services/files.py", "update_draft", "Draft editable pre-circ"),
    ("BR-FTS-008", "modules/fts/services/files.py", "discard_draft", "Discard draft transition"),
    ("BR-FTS-009", "modules/fts/selectors/history.py", "get_file_history", "Sequential ordering"),
    ("BR-FTS-010", "modules/fts/selectors/scoping.py", "get_file_for_user", "Scoped access"),
    ("BR-FTS-011", "modules/fts/models/attachments.py", "FileAttachment", "Attachment limit"),
    ("BR-FTS-012", "modules/fts/selectors/audit.py", "get_audit_logs", "Immutable audit log"),
    ("BR-FTS-013", "modules/fts/tasks.py", "dispatch_pending_notifications", "Notification tasks"),
    ("BR-FTS-014", "modules/fts/tasks.py", "verify_audit_integrity", "Audit continuity check"),

    # Use Cases
    ("FTS-UC-001", "modules/fts/services/files.py", "create_file", "Create institute file note"),
    ("FTS-UC-002", "modules/fts/services/files.py", "create_file", "Save file as draft"),
    ("FTS-UC-003", "modules/fts/services/files.py", "update_draft", "Edit pre-circulation draft"),
    ("FTS-UC-004", "modules/fts/services/files.py", "discard_draft", "Discard uncirculated draft"),
    ("FTS-UC-005", "modules/fts/services/movements.py", "forward_file", "Forward active file"),
    ("FTS-UC-006", "modules/fts/services/movements.py", "return_file", "Return active file"),
    ("FTS-UC-007", "modules/fts/services/archival.py", "archive_file", "Archive completed file"),
    ("FTS-UC-008", "modules/fts/selectors/files.py", "get_inbox_files", "View user file inbox"),
    ("FTS-UC-009", "modules/fts/selectors/files.py", "get_outbox_files", "View user file outbox"),
    ("FTS-UC-010", "modules/fts/selectors/audit.py", "get_audit_logs", "Governance view"),

    # Workflows
    ("BW-FTS-01", "modules/fts/services/files.py", "create_file", "File immediate circulation"),
    ("BW-FTS-02", "modules/fts/services/movements.py", "forward_file", "Sequential forwarding"),
    ("BW-FTS-03", "modules/fts/services/movements.py", "return_file", "File return to sender"),
    ("BW-FTS-04", "modules/fts/services/archival.py", "archive_file", "Owner archival"),
    ("BW-FTS-05", "modules/fts/services/files.py", "discard_draft", "Draft discard workflow"),
    ("BW-FTS-06", "modules/fts/selectors/history.py", "get_file_history", "History inspection"),
    ("BW-FTS-07", "modules/fts/services/files.py", "discard_draft", "Soft-delete draft"),
    ("BW-FTS-08", "modules/fts/contracts.py", "create_module_tracked_file", "Module integration"),

    # Requirements (CFR / AFR)
    ("CFR-FTS-01", "modules/fts/services/files.py", "create_file", "Core File Creation"),
    ("CFR-FTS-02", "modules/fts/services/movements.py", "forward_file", "Core Forwarding"),
    ("CFR-FTS-03", "modules/fts/services/movements.py", "return_file", "Core File Return"),
    ("CFR-FTS-04", "modules/fts/services/archival.py", "archive_file", "Core Archival"),
    ("CFR-FTS-05", "modules/fts/selectors/audit.py", "get_audit_logs", "Core Audit"),
    ("AFR-FTS-011", "modules/fts/models/files.py", "reference_number", "Reference generation"),
    ("AFR-FTS-012", "modules/fts/domain/entities.py", "FileDTO", "Subject and metadata"),
    ("AFR-FTS-013", "modules/fts/models/attachments.py", "FileAttachment", "Attachment upload"),
    ("AFR-FTS-014", "modules/fts/domain/state_machine.py", "STATE_DRAFT", "Draft capability"),
    ("AFR-FTS-015", "modules/fts/services/files.py", "update_draft", "Draft modification"),
    ("AFR-FTS-016", "modules/fts/services/files.py", "discard_draft", "Draft discarding"),
    ("AFR-FTS-021", "modules/fts/services/movements.py", "forward_file", "Forward to employee"),
    ("AFR-FTS-022", "modules/fts/services/movements.py", "forward_file", "Mandatory forward note"),
    ("AFR-FTS-023", "modules/fts/domain/state_machine.py", "transition_state", "Forward custody"),
    ("AFR-FTS-024", "modules/fts/services/notifications.py", "trigger_notification", "Notify"),
    ("AFR-FTS-031", "modules/fts/services/movements.py", "return_file", "Return to handler"),
    ("AFR-FTS-032", "modules/fts/services/movements.py", "return_file", "Mandatory return note"),
    ("AFR-FTS-033", "modules/fts/domain/state_machine.py", "transition_state", "Return custody"),
    ("AFR-FTS-041", "modules/fts/services/archival.py", "archive_file", "Archival by owner"),
    ("AFR-FTS-042", "modules/fts/domain/state_machine.py", "STATE_ARCHIVED", "Archived status"),
    ("AFR-FTS-043", "modules/fts/domain/state_machine.py", "transition_state", "Archived lock"),
    ("AFR-FTS-051", "modules/fts/selectors/history.py", "get_file_history", "History retrieval"),
    ("AFR-FTS-052", "modules/fts/selectors/audit.py", "get_usage_metrics", "Governance metrics"),
    ("AFR-FTS-053", "modules/fts/selectors/audit.py", "get_audit_logs", "Audit trail"),
    ("AFR-FTS-054", "modules/fts/services/audit.py", "record_audit", "Immutable logging"),
]


def resolve_line(rel_path: str, pattern: str) -> int:
    path = ROOT / rel_path
    if not path.exists():
        raise FileNotFoundError(f"Missing referenced file: {rel_path}")
    lines = path.read_text().splitlines()
    for idx, line in enumerate(lines, start=1):
        if pattern in line:
            return idx
    raise ValueError(f"Pattern {pattern!r} not found in {rel_path}")


def main() -> int:
    resolved_entries = []
    errors = []

    for spec_id, rel_path, pattern, description in SPEC_MAP:
        try:
            line_no = resolve_line(rel_path, pattern)
            resolved_entries.append((spec_id, rel_path, line_no, description))
        except (FileNotFoundError, ValueError) as e:
            errors.append(f"{spec_id} -> {rel_path}: {e}")

    if errors:
        print(f"Error: {len(errors)} spec links failed to resolve:")
        for err in errors:
            print(f"  - {err}")
        return 1

    content_lines = [
        "# FTS Specification Implementation Reference",
        "",
        "This document is automatically generated and verified by `ops/docs/fts_reference.py`.",
        "It maps every live specification identifier (CFR, AFR, BR, UC, BW) to its code.",
        "",
        "| Spec ID | Description | Enforcing Code Location |",
        "|---|---|---|",
    ]

    for spec_id, rel_path, line_no, desc in resolved_entries:
        link = f"[{rel_path}#L{line_no}]({rel_path}#L{line_no})"
        content_lines.append(f"| `{spec_id}` | {desc} | {link} |")

    content_lines.append("")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(content_lines))
    print(
        f"Successfully verified {len(resolved_entries)} spec links "
        f"and updated {DOC_PATH.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
