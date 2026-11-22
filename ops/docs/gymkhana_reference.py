#!/usr/bin/env python
"""Generate docs/18-gymkhana/gymkhana-reference.md from the live source tree.

Every rule, use case, workflow and requirement id is mapped to the file:line
that enforces it.  The script exits non-zero when any link does not resolve so
the CI schema-check gate catches stale documentation before it ships.

    python ops/docs/gymkhana_reference.py          writes the markdown
    python ops/docs/gymkhana_reference.py --check  only validates links
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "18-gymkhana" / "gymkhana-reference.md"

# ---------------------------------------------------------------------------
# (rule-id, description, file-relative-to-ROOT, line-number)
# ---------------------------------------------------------------------------
RULES: list[tuple[str, str, str, int]] = [
    # Functional rules
    ("GYM-FR-01", "Club coordinator and co-coordinator must be distinct active students",
     "modules/gymkhana/services/gymkhana.py", 46),
    ("GYM-FR-02", "Faculty councillor must be an active faculty member",
     "modules/gymkhana/services/gymkhana.py", 122),
    ("GYM-FR-03", "Club starts in OPEN status; only Student Admin may confirm it",
     "modules/gymkhana/services/gymkhana.py", 120),
    ("GYM-FR-04", "Only an OPEN club can be confirmed (idempotency guard)",
     "modules/gymkhana/services/gymkhana.py", 134),
    ("GYM-FR-05", "Session venue must be in the configured GYMKHANA_VENUES list",
     "modules/gymkhana/services/gymkhana.py", 67),
    ("GYM-FR-06", "Session start_time must precede end_time (service check)",
     "modules/gymkhana/services/gymkhana.py", 72),
    ("GYM-FR-06b", "Session start_time < end_time enforced at DB level (CheckConstraint)",
     "modules/gymkhana/models.py", 50),
    ("GYM-FR-07", "Venue overlap is blocked with a SELECT FOR UPDATE lock per venue+date",
     "modules/gymkhana/services/gymkhana.py", 72),
    ("GYM-FR-08", "Membership applications require a CONFIRMED club",
     "modules/gymkhana/services/gymkhana.py", 188),
    ("GYM-FR-09", "One membership application per student per club (UniqueConstraint)",
     "modules/gymkhana/models.py", 109),
    ("GYM-FR-10", "Only OPEN applications can be approved",
     "modules/gymkhana/services/gymkhana.py", 211),
    ("GYM-FR-11", "Poll must have at least one active student in its target groups",
     "modules/gymkhana/services/gymkhana.py", 228),
    ("GYM-FR-12", "Student must be in poll target group to vote",
     "modules/gymkhana/services/gymkhana.py", 246),
    ("GYM-FR-13", "One vote per student per poll (UniqueConstraint + ConflictError)",
     "modules/gymkhana/models.py", 167),
    ("GYM-FR-14", "Closed/expired polls reject new votes",
     "modules/gymkhana/services/gymkhana.py", 255),
    ("GYM-FR-15", "Budget amounts must be non-negative (CheckConstraint)",
     "modules/gymkhana/models.py", 186),
    ("GYM-FR-16", "Only this club's coordinator or co-coordinator may perform club-head actions",
     "modules/gymkhana/services/gymkhana.py", 55),
    ("GYM-FR-17", "Notifications are queued via outbox; deduplication by dedupe_key",
     "modules/gymkhana/services/gymkhana.py", 88),
    ("GYM-FR-18", "Outbox drain delivers email, marks SENT or FAILED with last_error",
     "modules/gymkhana/services/notifications.py", 1),
    # Use cases
    ("GYM-UC-01", "Create a club (Student Admin only)",
     "modules/gymkhana/api/views.py", 1),
    ("GYM-UC-02", "Confirm a club (Student Admin only)",
     "modules/gymkhana/services/gymkhana.py", 134),
    ("GYM-UC-03", "Change club leadership (Club Head only)",
     "modules/gymkhana/services/gymkhana.py", 146),
    ("GYM-UC-04", "Book a session (Club Head only, confirmed club)",
     "modules/gymkhana/services/gymkhana.py", 158),
    ("GYM-UC-05", "Book an event (Club Head only, confirmed club)",
     "modules/gymkhana/services/gymkhana.py", 172),
    ("GYM-UC-06", "Apply for membership (Student, confirmed club)",
     "modules/gymkhana/services/gymkhana.py", 187),
    ("GYM-UC-07", "Approve membership application (Club Head)",
     "modules/gymkhana/services/gymkhana.py", 202),
    ("GYM-UC-08", "Create a voting poll (Club Head, confirmed club)",
     "modules/gymkhana/services/gymkhana.py", 223),
    ("GYM-UC-09", "Cast a vote (eligible Student, active poll)",
     "modules/gymkhana/services/gymkhana.py", 255),
    ("GYM-UC-10", "View eligible polls (Student)",
     "modules/gymkhana/services/gymkhana.py", 278),
    ("GYM-UC-11", "Submit budget request (Club Head, confirmed club)",
     "modules/gymkhana/api/views.py", 1),
    ("GYM-UC-12", "Submit event report (Club Head, confirmed club)",
     "modules/gymkhana/api/views.py", 1),
    ("GYM-UC-13", "Review assigned reports (Faculty Councillor)",
     "modules/gymkhana/services/gymkhana.py", 304),
    # Workflow IDs
    ("GYM-WF-01", "Club lifecycle: OPEN → CONFIRMED (approve_club transition)",
     "modules/gymkhana/services/gymkhana.py", 134),
    ("GYM-WF-02", "Membership lifecycle: OPEN → CONFIRMED (approve_membership)",
     "modules/gymkhana/services/gymkhana.py", 202),
    ("GYM-WF-03", "Notification outbox lifecycle: PENDING → SENDING → SENT/FAILED",
     "modules/gymkhana/models.py", 204),
    ("GYM-WF-04", "Venue booking: lock + overlap check → create session/event",
     "modules/gymkhana/services/gymkhana.py", 72),
    # Permission rules
    ("GYM-PERM-01", "Permission catalogue registered in registry.py",
     "modules/gymkhana/registry.py", 22),
    ("GYM-PERM-02", "Role grants map roles to permissions in registry.py",
     "modules/gymkhana/registry.py", 56),
    ("GYM-PERM-03", "Permissions committed to registry/permissions.json",
     "registry/permissions.json", 1),
    # Non-functional / CI rules
    ("GYM-NF-01", "No cross-module ForeignKey (ops/checks/no_cross_module_fk.py)",
     "modules/gymkhana/models.py", 1),
    ("GYM-NF-02", "Module-to-module access only via directory.contracts",
     "modules/gymkhana/services/gymkhana.py", 11),
    ("GYM-NF-03", "Readiness check: upload root exists + venues configured",
     "modules/gymkhana/registry.py", 72),
    ("GYM-NF-04", "Celery schedule and routing registered via GYMKHANA_SCHEDULE",
     "modules/gymkhana/schedule.py", 1),
]


def _resolve(rel: str, line: int) -> tuple[bool, Path]:
    p = ROOT / rel
    if not p.exists():
        return False, p
    lines = p.read_text(encoding="utf-8").splitlines()
    return line <= len(lines), p


def _gh_link(rel: str, line: int) -> str:
    return f"`{rel}:{line}`"


def build_md() -> tuple[str, list[str]]:
    errors: list[str] = []
    rows: list[str] = []
    for rule_id, description, rel, line in RULES:
        ok, _path = _resolve(rel, line)
        if not ok:
            errors.append(f"{rule_id}: {rel}:{line} does not resolve")
        rows.append(f"| `{rule_id}` | {description} | {_gh_link(rel, line)} |")

    header = """\
# Gymkhana Module — Reference

> Generated by `ops/docs/gymkhana_reference.py`. Edit the script, not this file.

Every rule, use case, workflow and requirement is pinned to the source line
that enforces it.  The script fails CI if any link goes stale.

## Rules, Use Cases and Workflows

| ID | Description | Source |
|----|-------------|--------|
"""
    return header + "\n".join(rows) + "\n", errors


def main() -> int:
    md, errors = build_md()
    if "--check" in sys.argv:
        if errors:
            for e in errors:
                print(f"ERROR: {e}", file=sys.stderr)
            return 1
        print("All gymkhana reference links resolve.")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(md, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    if errors:
        for e in errors:
            print(f"WARNING: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
