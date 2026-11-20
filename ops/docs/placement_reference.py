"""Write the spec-id-to-code reference; exit non-zero when any link no longer resolves."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "modules" / "placement"
OUT = ROOT / "docs" / "04-placement" / "placement-reference.md"
MACHINE = ROOT / "docs" / "04-placement" / "application-state-machine.md"
DIAGRAM = ROOT / "docs" / "_diagrams" / "application-state-machine.mmd"

S = "services"
D = "domain"
A = "api"

#: id -> (what the spec requires, ["path::symbol", ...]) ; paths are relative to modules/placement.
TRACE: dict[str, tuple[str, list[str]]] = {
    # -- Business rules ----------------------------------------------------------------
    "PC-BR-001": ("Profile completeness before applying",
                  [f"{S}/applications.py::_guard", f"{D}/state_machine.py::TRANSITIONS"]),
    "PC-BR-002": ("Eligibility enforced before applying",
                  [f"{D}/eligibility.py::evaluate", f"{S}/applications.py::evaluate_for"]),
    "PC-BR-003": ("Posting needs description, criteria and deadline",
                  [f"{S}/postings.py::_require_publishable"]),
    "PC-BR-004": ("Criteria use the recorded vocabulary only",
                  [f"{D}/eligibility.py::FIELDS", f"{D}/eligibility.py::validate"]),
    "PC-BR-005": ("TPO posting authority", [f"{S}/postings.py::create", "registry.py::_OFFICER"]),
    "PC-BR-006": ("Company posting authority within scope",
                  [f"{S}/postings.py::create", "selectors/scoping.py::postings_for"]),
    "PC-BR-007": ("Company functions only once approved",
                  ["models/companies.py::can_operate", f"{S}/companies.py::approve"]),
    "PC-BR-009": ("Company sees only its own applications",
                  ["selectors/scoping.py::applications_for"]),
    "PC-BR-010": ("TPO manages applications", [f"{D}/state_machine.py::_review",
                                               f"{S}/applications.py::transition"]),
    "PC-BR-011": ("Interview needs date, slot and mode", [f"{S}/interviews.py::schedule_round"]),
    "PC-BR-012": ("Interview notification", [f"{S}/interviews.py::add_candidates"]),
    "PC-BR-013": ("Offer response within the deadline",
                  [f"{S}/offers.py::respond", f"{S}/offers.py::expire_overdue"]),
    "PC-BR-014": ("Acceptance updates the placement record",
                  [f"{S}/offers.py::_record_acceptance"]),
    "PC-BR-015": ("Multiple offers only by represented policy",
                  [f"{D}/offer_policy.py::can_accept"]),
    "PC-BR-016": ("Students see anonymised statistics", [f"{S}/stats.py::student_view"]),
    "PC-BR-017": ("Announcement topics bounded", ["models/announcements.py::Announcement",
                                                  f"{S}/announcements.py::publish"]),
    "PC-BR-019": ("Alumni read-only access", ["registry.py::_ALUMNI"]),
    "PC-BR-020": ("Alumni kept out of active workflows",
                  ["selectors/scoping.py::applications_for", "registry.py::_ALUMNI"]),
    "PC-BR-021": ("Notifications handed off as email", [f"{S}/notifications.py::deliver_pending"]),
    "PC-BR-022": ("Access by role and scope", ["selectors/scoping.py::is_staff",
                                               f"{S}/authz.py::require"]),
    "PC-BR-023": ("Sensitive data view restricted", ["selectors/scoping.py::may_read_candidate"]),
    "PC-BR-024": ("Sensitive data modify restricted", [f"{S}/authz.py::require"]),
    "PC-BR-025": ("Academic data stays external", [f"{S}/facts.py::academic_facts"]),
    "PC-BR-026": ("Platform auth and RBAC stay external",
                  ["authentication.py::RecruiterAuthentication", "registry.py::ROLE_GRANTS"]),
    "PC-BR-029": ("TPO updates student and alumni records", [f"{S}/records.py::correct"]),
    "PC-BR-030": ("No external recruitment decision made here",
                  [f"{D}/state_machine.py::TRANSITIONS"]),
    # -- Use cases ---------------------------------------------------------------------
    "PC-UC-001": ("Student placement profile", [f"{A}/views.py::MyResumeView",
                                                f"{S}/documents.py::attach_link"]),
    "PC-UC-002": ("Browse opportunities", ["selectors/scoping.py::postings_for"]),
    "PC-UC-003": ("Apply for an eligible posting", [f"{S}/applications.py::apply_to"]),
    "PC-UC-004": ("Track status", [f"{A}/audit.py::ApplicationHistoryView",
                                   "selectors/scoping.py::applications_for"]),
    "PC-UC-005": ("Respond to an offer", [f"{S}/offers.py::respond"]),
    "PC-UC-006": ("TPO manages postings", [f"{S}/postings.py::publish"]),
    "PC-UC-007": ("Automated notifications", [f"{S}/notifications.py::enqueue"]),
    "PC-UC-008": ("TPO reviews and filters applications",
                  ["selectors/scoping.py::applications_for", f"{S}/applications.py::transition"]),
    "PC-UC-009": ("TPO schedules interviews", [f"{S}/interviews.py::add_candidates"]),
    "PC-UC-010": ("TPO maintains placement records", [f"{S}/records.py::correct"]),
    "PC-UC-011": ("TPO reports", [f"{S}/stats.py::staff_view", f"{S}/stats.py::trends"]),
    "PC-UC-012": ("Chairman oversight", [f"{S}/stats.py::staff_view", "registry.py::_CHAIRMAN"]),
    "PC-UC-013": ("Chairman announcements", [f"{S}/announcements.py::publish"]),
    "PC-UC-014": ("Company registers", [f"{A}/views.py::CompanySelfRegisterView",
                                        f"{S}/companies.py::register"]),
    "PC-UC-015": ("Company publishes or submits", [f"{S}/postings.py::submit"]),
    "PC-UC-016": ("Company shortlists or rejects", [f"{S}/applications.py::transition"]),
    "PC-UC-017": ("Alumni restricted access", ["registry.py::_ALUMNI"]),
    "PC-UC-020": ("TPO announcements", [f"{S}/announcements.py::publish"]),
    "PC-UC-021": ("Company schedules an interview", [f"{S}/interviews.py::schedule_round"]),
    "PC-UC-022": ("Company extends an offer", [f"{S}/offers.py::issue"]),
    "PC-UC-023": ("Resume from the profile", [f"{S}/candidates.py::candidate_record"]),
    "PC-UC-024": ("Student statistics", [f"{S}/stats.py::student_view"]),
    # -- Workflows ---------------------------------------------------------------------
    "BW-PC-01": ("TPO publishes, student applies", [f"{S}/postings.py::publish",
                                                    f"{S}/applications.py::apply_to"]),
    "BW-PC-02": ("Company publishes, student applies", [f"{S}/postings.py::publish"]),
    "BW-PC-03": ("Company submits, TPO publishes", [f"{S}/postings.py::submit"]),
    "BW-PC-04": ("Applied to shortlisted", [f"{D}/state_machine.py::TRANSITIONS"]),
    "BW-PC-05": ("Shortlisted to TPO interview", [f"{S}/interviews.py::add_candidates"]),
    "BW-PC-06": ("Shortlisted to company interview", [f"{S}/interviews.py::add_candidates"]),
    "BW-PC-07": ("Offer accepted, record updated", [f"{S}/offers.py::_record_acceptance"]),
    "BW-PC-08": ("Offer rejected", [f"{S}/offers.py::respond"]),
    "CW-PC-01": ("Publication paths to application", [f"{S}/postings.py::publish"]),
    "CW-PC-02": ("Selection and scheduling", [f"{D}/state_machine.py::TRANSITIONS"]),
    "CW-PC-03": ("Offer outcome", [f"{S}/offers.py::respond"]),
    "CW-PC-04": ("End-to-end lifecycle", [f"{D}/state_machine.py::TRANSITIONS"]),
}

#: Requirement id -> the rule or use case id it is enforced through.
AFR_VIA = {
    1: "PC-UC-001", 2: "PC-UC-001", 3: "PC-UC-001", 4: "PC-BR-001", 5: "PC-UC-023",
    6: "PC-UC-002", 7: "PC-UC-003", 8: "PC-BR-002", 9: "PC-UC-004", 10: "PC-UC-004",
    11: "PC-UC-005", 12: "BW-PC-08", 13: "PC-BR-014", 14: "PC-BR-015", 15: "PC-BR-016",
    16: "PC-UC-024", 17: "PC-UC-006", 18: "PC-UC-015", 19: "PC-UC-015", 20: "PC-BR-004",
    21: "PC-BR-003", 22: "PC-BR-004", 23: "PC-UC-008", 24: "PC-UC-008", 25: "PC-BR-010",
    26: "PC-UC-009", 27: "PC-UC-021", 28: "PC-BR-011", 29: "PC-UC-009", 30: "PC-UC-010",
    31: "PC-BR-029", 32: "PC-BR-029", 33: "PC-UC-011", 34: "PC-UC-011", 35: "PC-UC-011",
    36: "PC-UC-011", 37: "PC-UC-012", 38: "PC-UC-012", 39: "PC-UC-012", 40: "PC-UC-020",
    41: "PC-UC-013", 42: "PC-BR-017", 43: "PC-BR-017", 44: "PC-UC-014", 45: "PC-BR-007",
    46: "PC-BR-009", 47: "PC-UC-016", 48: "PC-UC-016", 49: "PC-UC-022", 50: "PC-UC-007",
    51: "PC-UC-007", 52: "PC-UC-007", 53: "PC-UC-007", 54: "PC-BR-012", 55: "PC-UC-022",
    56: "PC-UC-007", 57: "PC-BR-021", 58: "PC-BR-019", 59: "PC-BR-019", 60: "PC-BR-020",
    61: "PC-BR-022", 62: "PC-BR-023", 63: "PC-BR-024", 64: "PC-BR-026",
}
CFR_AFRS = {1: (1, 5), 2: (6, 6), 3: (7, 9), 4: (10, 10), 5: (11, 14), 6: (15, 16),
            7: (17, 22), 8: (23, 25), 9: (26, 29), 10: (30, 32), 11: (33, 36), 12: (37, 39),
            13: (40, 43), 14: (44, 45), 15: (46, 48), 16: (49, 49), 17: (50, 57),
            18: (58, 60), 19: (61, 64)}


def resolve(ref: str) -> str:
    path, symbol = ref.split("::")
    lines = (PKG / path).read_text().splitlines()
    pattern = re.compile(rf"^\s*(def|class)\s+{re.escape(symbol)}\b|^{re.escape(symbol)}\s*[:=]")
    for n, line in enumerate(lines, 1):
        if pattern.search(line):
            return f"[`{path}:{n}`](../../modules/placement/{path}#L{n}) `{symbol}`"
    raise LookupError(ref)


def write_state_machine() -> None:
    sys.path.insert(0, str(ROOT))
    from modules.placement.domain import state_machine as sm

    rows = "\n".join(
        f"| `{t.frm}` | `{t.to}` | {', '.join(sorted(t.actors))} | `{t.permission}` | "
        f"{', '.join(t.guards) or '—'} |" for t in sm.TRANSITIONS)
    terminal = ", ".join(f"`{s}`" for s in sorted(sm.TERMINAL))
    edges = "\n".join(f"    {t.frm} --> {t.to}" for t in sm.TRANSITIONS)
    ends = "\n".join(f"    {s} --> [*]" for s in sorted(sm.TERMINAL))
    DIAGRAM.write_text(
        "%% Generated from domain/state_machine.py TRANSITIONS by ops/docs/placement_reference.py\n"
        f"stateDiagram-v2\n    [*] --> draft\n{edges}\n{ends}\n")
    MACHINE.write_text(
        "# Application state machine\n\n"
        "Generated from `modules/placement/domain/state_machine.py` by "
        "`ops/docs/placement_reference.py`. Do not edit by hand.\n"
        "Every status change goes through `services/applications.transition` or the offer "
        "services, which resolve the move against this table first, so a move not listed "
        "here cannot happen.\n"
        "The spec's states map as follows: Applied is `submitted`, Shortlisted is "
        "`shortlisted`, Interview Scheduled is `interview_scheduled`, Offer Extended is "
        "`offer_issued`, Offer Accepted is `offer_accepted`, Offer Rejected is "
        "`offer_declined` (CW-PC-04).\n\n"
        f"Terminal states: {terminal}.\n\n"
        "| From | To | Who may | Permission | Guards |\n|---|---|---|---|---|\n"
        + rows + "\n")


def main() -> int:
    rows, broken = [], []
    for sid, (what, refs) in TRACE.items():
        links = []
        for ref in refs:
            try:
                links.append(resolve(ref))
            except (LookupError, FileNotFoundError):
                broken.append(f"{sid}: {ref}")
        rows.append(f"| {sid} | {what} | {'<br>'.join(links)} |")
    for n, via in AFR_VIA.items():
        rows.append(f"| PC-AFR-{n:03d} | Enforced through {via} | see {via} |")
    for n, (lo, hi) in CFR_AFRS.items():
        rows.append(f"| PC-CFR-{n:03d} | Consolidates PC-AFR-{lo:03d} to PC-AFR-{hi:03d} | "
                    f"see those requirements |")
    if broken:
        print("unresolved links:\n  " + "\n  ".join(broken), file=sys.stderr)
        return 1
    OUT.write_text(
        "# Placement Cell: specification reference\n\n"
        "Generated by `ops/docs/placement_reference.py`. Do not edit by hand.\n"
        "Each live id of the PC specification v1.3 links to the code that enforces it.\n\n"
        "| Id | What the spec requires | Enforced at |\n|---|---|---|\n"
        + "\n".join(rows) + "\n")
    write_state_machine()
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} ids, and the state machine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
