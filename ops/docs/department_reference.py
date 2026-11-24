#!/usr/bin/env python
"""Write department-reference.md: a file:line link per live spec id; a stale link fails."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "10-department" / "department-reference.md"
M = "modules/department"

DOMAIN_RULES = f"{M}/domain/rules.py"
SM = f"{M}/domain/state_machine.py"
SCOPING = f"{M}/selectors/scoping.py"
ACTORS = f"{M}/selectors/actors.py"
PROFILES = f"{M}/selectors/profiles.py"
ANN = f"{M}/services/announcements.py"
INV = f"{M}/services/inventory.py"
FB = f"{M}/services/feedback.py"
DEPTS = f"{M}/services/departments.py"
RES = f"{M}/services/resources.py"
ROLES = f"{M}/services/roles.py"
NOTIFY = f"{M}/services/notifications.py"
MODELS_INV = f"{M}/models/inventory.py"
MODELS_ROLES = f"{M}/models/roles.py"
REGISTRY = f"{M}/registry.py"
TASKS = f"{M}/tasks.py"

# id -> (file, anchor text, what is enforced there)
LINKS: dict[str, tuple[str, str, str]] = {
    "BR-DEPT-001": (
        REGISTRY,
        '"department.announcement.create",',
        "creation permission granted only to Faculty, Dept_Admin, HOD",
    ),
    "BR-DEPT-002": (SCOPING, "def announcements_for", "relevance filter by role, programme, year"),
    "BR-DEPT-003": (DOMAIN_RULES, "def validate_announcement", "content and target completeness"),
    "BR-DEPT-004": (
        SM,
        "ANNOUNCEMENT_TRANSITIONS:",
        "edit, hide, delete: HOD only, by acting role",
    ),
    "BR-DEPT-005": (SM, "Transition(NONE, STOCK_PENDING", "only Faculty may create a request"),
    "BR-DEPT-006": (SM, "Transition(STOCK_PENDING, STOCK_APPROVED", "only the HOD decides"),
    "BR-DEPT-007": (SM, "STOCK_APPROVED, STOCK_ISSUED", "issue only from approved, by Dept_Admin"),
    "BR-DEPT-008": (SM, "Transition(NONE, FEEDBACK_NEW", "only Students and Faculty submit"),
    "BR-DEPT-009": (
        SM,
        "FEEDBACK_UNDER_REVIEW,\n        FEEDBACK_RESOLVED",
        "terminal disposition by Dept_Admin or HOD",
    ),
    "BR-DEPT-010": (DOMAIN_RULES, "def find_overlaps", "overlapping slots refused"),
    "BR-DEPT-011": (DEPTS, "def propose", "official change stays pending"),
    "BR-DEPT-012": (SCOPING, "def stock_requests_for", "Faculty resource scope"),
    "BR-DEPT-013": (DEPTS, "def decide", "HOD decides official changes"),
    "BR-DEPT-015": (DOMAIN_RULES, "def check_availability", "request-time availability"),
    "BR-DEPT-016": (MODELS_INV, "class StockMovement(models.Model)", "append-only movement log"),
    "BR-DEPT-017": (SCOPING, "def feedback_for", "confidential feedback scope"),
    "BR-DEPT-018": (SM, "FEEDBACK_NEW, FEEDBACK_UNDER_REVIEW", "Dept_Admin initial review first"),
    "BR-DEPT-019": (DOMAIN_RULES, "def tier_for", "profile visibility matrix"),
    "BR-DEPT-021": (ROLES, "def assign", "central authority records tenures"),
    "BR-DEPT-022": (DOMAIN_RULES, "def overlapping", "never two holders at once"),
    "BR-DEPT-023": (MODELS_ROLES, 'name="dept_tenure_interval"', "validity interval required"),
    "BR-DEPT-024": (ACTORS, "def holds_tenure", "access follows the tenure in effect now"),
    "UC-DEPT-001": (
        f"{M}/api/views.py",
        "class AnnouncementListView",
        "view relevant announcements",
    ),
    "UC-DEPT-002": (ANN, "def publish", "create and publish"),
    "UC-DEPT-003": (ANN, "def edit", "edit, hide, delete"),
    "UC-DEPT-004": (INV, "def request_stock", "request stock"),
    "UC-DEPT-005": (INV, "def decide", "approve or reject"),
    "UC-DEPT-006": (INV, "def issue", "issue stock"),
    "UC-DEPT-007": (FB, "def submit", "submit feedback"),
    "UC-DEPT-008": (FB, "def review", "initial review and disposition"),
    "UC-DEPT-009": (RES, "def upload", "manage timetable"),
    "UC-DEPT-010": (DEPTS, "def update_general", "update details"),
    "UC-DEPT-011": (SCOPING, "def lab_resources_for", "view department resources"),
    "UC-DEPT-012": (DEPTS, "def decide", "approve official changes"),
    "UC-DEPT-014": (FB, "def add_note", "HOD oversight"),
    "UC-DEPT-015": (PROFILES, "def profile_views", "view profiles at tier"),
    "UC-DEPT-016": (RES, "def create_profile", "manage profiles"),
    "UC-DEPT-017": (RES, "def save_lab", "manage lab profiles"),
    "UC-DEPT-018": (SCOPING, "def timetable_for", "student timetable and programme view"),
    "UC-DEPT-019": (INV, "def add_item", "manage inventory records"),
    "UC-DEPT-020": (ROLES, "def assign", "maintain role assignments"),
    "UC-DEPT-022": (ROLES, "def apply_transitions", "apply effective transition"),
    "BW-DEPT-01": (SM, "STOCK_TRANSITIONS:", "approved and issued path"),
    "BW-DEPT-02": (SM, "Transition(STOCK_PENDING, STOCK_REJECTED", "rejected path"),
    "CW-DEPT-01": (SM, "STOCK_TRANSITIONS:", "stock lifecycle table"),
    "BW-DEPT-03": (SM, "FEEDBACK_TRANSITIONS:", "Dept_Admin disposition path"),
    "BW-DEPT-04": (SM, "FEEDBACK_TRANSITIONS:", "HOD oversight path"),
    "CW-DEPT-02": (SM, "FEEDBACK_TRANSITIONS:", "feedback lifecycle table"),
    "BW-DEPT-05": (SM, "CHANGE_PENDING, CHANGE_APPROVED", "approved official change"),
    "BW-DEPT-06": (SM, "CHANGE_PENDING, CHANGE_REJECTED", "rejected official change"),
    "CW-DEPT-03": (SM, "OFFICIAL_CHANGE_TRANSITIONS:", "official change lifecycle table"),
    "BW-DEPT-07": (ROLES, "outgoing = [", "HOD reassignment closes the outgoing tenure"),
    "BW-DEPT-08": (ROLES, "outgoing = [", "Dept_Admin reassignment closes the outgoing tenure"),
    "CW-DEPT-04": (ROLES, "def apply_transitions", "reassignment lifecycle takes effect"),
    "CFR-DEPT-001": (ANN, "def publish", "publish and notify"),
    "CFR-DEPT-002": (SCOPING, "def announcements_for", "relevant announcements"),
    "CFR-DEPT-003": (ANN, "def _move", "HOD maintains active announcements, through the table"),
    "CFR-DEPT-004": (INV, "def _receive", "inventory and insertion audit"),
    "CFR-DEPT-005": (INV, "def issue", "request to final outcome"),
    "CFR-DEPT-006": (SCOPING, "def stock_requests_for", "Faculty issued-stock history"),
    "CFR-DEPT-007": (FB, "def submit", "confidential feedback"),
    "CFR-DEPT-008": (FB, "def dispose", "review and resolve"),
    "CFR-DEPT-009": (RES, "def update_profile", "manage profiles"),
    "CFR-DEPT-010": (DOMAIN_RULES, "TIER_FIELDS = {", "profile visibility"),
    "CFR-DEPT-011": (RES, "def _check", "conflict-free timetables"),
    "CFR-DEPT-012": (RES, "def save_lab", "lab resource profiles"),
    "CFR-DEPT-013": (SCOPING, "def timetable_for", "student academic information"),
    "CFR-DEPT-014": (DOMAIN_RULES, "def check_general_update", "general information only"),
    "CFR-DEPT-015": (DOMAIN_RULES, "def validate_official_change", "official changes controlled"),
    "CFR-DEPT-016": (ROLES, "def change", "role assignments and effective access"),
    "AFR-DEPT-001": (ANN, "def publish", "create and publish"),
    "AFR-DEPT-002": (
        SCOPING,
        'relevant = Q(audience_role__in=(ctx.role, "all"))',
        "role, programme, year filter",
    ),
    "AFR-DEPT-003": (f"{M}/api/views.py", "class AnnouncementListView", "authenticated users view"),
    "AFR-DEPT-004": (ANN, "def edit", "HOD edit"),
    "AFR-DEPT-005": (ANN, "def hide", "HOD hide"),
    "AFR-DEPT-006": (ANN, "def delete", "HOD delete (soft, Q7)"),
    "AFR-DEPT-007": (INV, "def add_item", "insert stock"),
    "AFR-DEPT-008": (INV, "def _receive", "current quantity from the ledger"),
    "AFR-DEPT-009": (INV, "def request_stock", "Faculty request"),
    "AFR-DEPT-010": (DOMAIN_RULES, "def check_availability", "quantity validated"),
    "AFR-DEPT-011": (INV, "def decide", "HOD approve or reject"),
    "AFR-DEPT-012": (SM, "STOCK_APPROVED, STOCK_ISSUED", "issue only approved"),
    "AFR-DEPT-013": (INV, "item.current_quantity -= req.quantity", "decrement on issue"),
    "AFR-DEPT-014": (INV, "kind=StockMovement.RECEIPT", "insertion logged"),
    "AFR-DEPT-015": (INV, "kind=StockMovement.ISSUE", "issuance logged"),
    "AFR-DEPT-016": (SCOPING, "def stock_requests_for", "Faculty issued history (Q12)"),
    "AFR-DEPT-017": (FB, "def submit", "Students and Faculty submit"),
    "AFR-DEPT-018": (SCOPING, "def feedback_for", "confidential scope"),
    "AFR-DEPT-019": (FB, "def review", "Dept_Admin initial review"),
    "AFR-DEPT-020": (DOMAIN_RULES, "def check_category", "optional category (Q11)"),
    "AFR-DEPT-021": (FB, "if disposition:", "close a simple issue during review"),
    "AFR-DEPT-022": (FB, "def _dispose", "Resolved or Closed"),
    "AFR-DEPT-023": (
        SCOPING,
        "exclude(status=sm.FEEDBACK_NEW)",
        "HOD sees feedback after initial review",
    ),
    "AFR-DEPT-024": (RES, "def create_profile", "manage profile records"),
    "AFR-DEPT-025": (DOMAIN_RULES, "if viewer_role == STUDENT:", "Students: basic"),
    "AFR-DEPT-026": (
        PROFILES,
        "def taught_cohorts",
        "Faculty on Students in a slot they teach: detailed (Q2)",
    ),
    "AFR-DEPT-027": (
        DOMAIN_RULES,
        'if target_kind != "student":',
        "Faculty on Faculty/Alumni: limited",
    ),
    "AFR-DEPT-028": (
        DOMAIN_RULES,
        "if viewer_role in (HOD, DEPT_ADMIN):",
        "HOD/Dept_Admin: full, no sensitive fields",
    ),
    "AFR-DEPT-029": (RES, "def upload", "upload"),
    "AFR-DEPT-030": (RES, "def modify", "modify"),
    "AFR-DEPT-031": (RES, "def _check", "detect and block overlaps"),
    "AFR-DEPT-034": (RES, "def save_lab", "update lab details"),
    "AFR-DEPT-035": (SCOPING, "def lab_resources_for", "Faculty view labs"),
    "AFR-DEPT-036": (f"{M}/api/views.py", "def _programmes", "programme information (Q9)"),
    "AFR-DEPT-037": (SCOPING, "def timetable_for", "applicable timetable"),
    "AFR-DEPT-038": (DEPTS, "def update_general", "general information"),
    "AFR-DEPT-039": (DEPTS, "def propose", "pending until HOD approval"),
    "AFR-DEPT-040": (DEPTS, "def decide", "HOD approve or reject"),
    "AFR-DEPT-041": (INV, 'topic="stock_request.created"', "notify Dept_Admin of a new request"),
    "AFR-DEPT-042": (INV, 'topic="stock_request.pending_hod"', "notify HOD"),
    "AFR-DEPT-043": (
        INV,
        'topic="stock_request.issued"',
        "notify Faculty on Issued (and on Rejected in decide)",
    ),
    "AFR-DEPT-044": (FB, 'topic="feedback.created"', "notify Dept_Admin of new feedback"),
    "AFR-DEPT-045": (FB, 'topic="feedback.disposed"', "notify the submitter"),
    "AFR-DEPT-046": (NOTIFY, "def announcement_audience", "notify the announcement's audience"),
    "AFR-DEPT-047": (ROLES, "rules.EMPLOYEE_KINDS", "assign to institute employees"),
    "AFR-DEPT-048": (MODELS_ROLES, "valid_to = models.DateTimeField()", "time-bounded validity"),
    "AFR-DEPT-049": (ACTORS, "valid_to__gt=now", "outgoing access ends at valid_to"),
    "AFR-DEPT-050": (ACTORS, "valid_from__lte=now", "incoming access starts at valid_from"),
    "AFR-DEPT-051": (ROLES, 'code="tenure_overlap"', "one HOD in effect"),
    "AFR-DEPT-052": (ROLES, 'code="tenure_overlap"', "one Dept_Admin in effect"),
    "AFR-DEPT-053": (PROFILES, "def headships", "headship derived from the HOD tenure"),
}

LIVE = (
    [f"BR-DEPT-{i:03d}" for i in [*range(1, 14), *range(15, 20), *range(21, 25)]]
    + [f"UC-DEPT-{i:03d}" for i in [*range(1, 13), *range(14, 21), 22]]
    + [f"BW-DEPT-{i:02d}" for i in range(1, 9)]
    + [f"CW-DEPT-{i:02d}" for i in range(1, 5)]
    + [f"CFR-DEPT-{i:03d}" for i in range(1, 17)]
    + [f"AFR-DEPT-{i:03d}" for i in [*range(1, 32), *range(34, 54)]]
)


def resolve(path: str, anchor: str) -> int | None:
    text = (ROOT / path).read_text()
    at = text.find(anchor)
    return None if at < 0 else text.count("\n", 0, at) + 1


def main() -> int:
    problems = [f"{i}: no link" for i in LIVE if i not in LINKS]
    problems += [f"{i}: not a live id" for i in LINKS if i not in LIVE]
    rows = []
    for spec_id in LIVE:
        if spec_id not in LINKS:
            continue
        path, anchor, what = LINKS[spec_id]
        line = resolve(path, anchor)
        if line is None:
            problems.append(f"{spec_id}: {anchor!r} not found in {path}")
            continue
        rows.append(f"| {spec_id} | [{path}:{line}](../../{path}#L{line}) | {what} |")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    OUT.write_text(
        "# Department: where each spec id is enforced\n\n"
        "Written by `ops/docs/department_reference.py`; do not edit by hand.\n\n"
        "| Id | Enforced at | What |\n|---|---|---|\n" + "\n".join(rows) + "\n"
    )
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} ids)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
