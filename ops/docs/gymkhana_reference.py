#!/usr/bin/env python
"""Write docs/18-gymkhana/gymkhana-reference.md: every live spec id linked to its enforcing line."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "18-gymkhana" / "gymkhana-reference.md"
G = "modules/gymkhana"

RULES = f"{G}/domain/rules.py"
SM = f"{G}/domain/state_machine.py"
SCOPE = f"{G}/selectors/scoping.py"
CLUBS = f"{G}/services/clubs.py"
LEAD = f"{G}/services/leadership.py"
MEM = f"{G}/services/memberships.py"
BOOK = f"{G}/services/bookings.py"
POLL = f"{G}/services/polls.py"
BUD = f"{G}/services/budget.py"
REP = f"{G}/services/reports.py"
PEOPLE = f"{G}/services/people.py"
NOTE = f"{G}/services/notifications.py"
VIEWS = f"{G}/api/views.py"
MODELS = f"{G}/models"

# (id, what it requires, file, the text on the enforcing line)
REFERENCE = [
    ("BR-GYM-001", "Leaders are valid students", PEOPLE, "def require_students("),
    ("BR-GYM-002", "Councillor is valid faculty", PEOPLE, "def require_faculty("),
    ("BR-GYM-003", "Category is Technical, Sports or Cultural", RULES, "def check_category("),
    ("BR-GYM-004", "Open on creation, confirmed by Student Admin", SM,
     "Transition(CLUB, OPEN, APPROVE, STUDENT_ADMIN, CONFIRMED"),
    ("BR-GYM-005", "Start before end", RULES, "def check_time_range("),
    ("BR-GYM-006", "No overlap in a venue on a date", BOOK,
     "VenueDay.objects.select_for_update().get("),
    ("BR-GYM-007", "Apply only to a confirmed club", MEM,
     "club = scoping.clubs_for(actor).filter(pk=club_id, status=sm.CONFIRMED).first()"),
    ("BR-GYM-008", "Different clubs remain open", f"{MODELS}/memberships.py",
     'fields=["club", "user_id"]'),
    ("BR-GYM-009", "No duplicate same-club application", f"{MODELS}/memberships.py",
     'name="gym_membership_one_per_club"'),
    ("BR-GYM-010", "Only the club's current leaders act as Club Head", SCOPE,
     "def led_clubs("),
    ("BR-GYM-011", "Approval moves open to confirmed with remarks", MEM,
     "t = sm.resolve(sm.MEMBERSHIP, membership.status, sm.APPROVE, sm.CLUB_HEAD)"),
    ("BR-GYM-012", "At least two choices", RULES, "def check_choices("),
    ("BR-GYM-013", "Poll audience by batch and branch", RULES, "def in_audience("),
    ("BR-GYM-014", "Only an active, unexpired poll", POLL,
     "if not rules.poll_is_active(poll.expires_on, timezone.localdate()):"),
    ("BR-GYM-015", "One vote per student per poll", f"{MODELS}/polls.py",
     'name="gym_vote_one_per_student"'),
    ("BR-GYM-016", "Superseded leaders stop being current", LEAD, "valid_to=now, updated_at=now)"),
    ("BR-GYM-017", "Budget amount zero or more", RULES, "def check_amount("),
    ("BR-GYM-018", "Budget needs its supporting file", BUD,
     'missing_code="supporting_file_required"'),
    ("BR-GYM-019", "Report needs its file", REP, 'missing_code="report_file_required"'),
    ("BR-GYM-020", "Configured venue only", BOOK, "def _venue("),
    ("BR-GYM-021", "Councillor reads only their club's reports", SCOPE, "def reports_for("),
    ("UC-GYM-001", "Create New Club", CLUBS, "def create_club("),
    ("UC-GYM-002", "Book Club Session", BOOK, "def book_session("),
    ("UC-GYM-003", "Book Club Event", BOOK, "def book_event("),
    ("UC-GYM-004", "Apply for Club Membership", MEM, "def apply("),
    ("UC-GYM-005", "Approve Club Membership", MEM, "def approve_many("),
    ("UC-GYM-006", "Create Voting Poll", POLL, "def create_poll("),
    ("UC-GYM-007", "Vote in Poll", POLL, "def cast_vote("),
    ("UC-GYM-008", "Change Club Leadership", LEAD, "def change_leadership("),
    ("UC-GYM-009", "Request Club Budget", BUD, "def submit("),
    ("UC-GYM-010", "Submit Club Event Report", REP, "def submit("),
    ("UC-GYM-011", "Approve Club", CLUBS, "def approve_club("),
    ("UC-GYM-012", "Review Club Event Report", VIEWS, "class ReportDetailView("),
    ("BW-GYM-01", "Club Membership Enrollment", SM,
     "Transition(MEMBERSHIP, NONE, APPLY, STUDENT, OPEN"),
    ("BW-GYM-02", "Targeted Poll Participation", POLL, "def cast_vote("),
    ("BW-GYM-03", "Club Establishment and Confirmation", SM,
     "Transition(CLUB, NONE, CREATE, STUDENT_ADMIN, OPEN"),
    ("CFR-GYM-001", "Club establishment", CLUBS, "def create_club("),
    ("CFR-GYM-002", "Leadership change", LEAD, "def change_leadership("),
    ("CFR-GYM-003", "Session and event booking", BOOK, "def _book("),
    ("CFR-GYM-004", "Membership enrolment", MEM, "def apply("),
    ("CFR-GYM-005", "Targeted polling", POLL, "def create_poll("),
    ("CFR-GYM-006", "Budget request submission", BUD, "def submit("),
    ("CFR-GYM-007", "Event reports and councillor review", SCOPE, "def reports_for("),
    ("AFR-GYM-001", "Create club with its fields", CLUBS, "club = Club.objects.create("),
    ("AFR-GYM-002", "Leaders valid students at creation", CLUBS, "(people.require_students,"),
    ("AFR-GYM-003", "Councillor valid faculty", CLUBS, "(people.require_faculty,"),
    ("AFR-GYM-004", "Category restricted", f"{MODELS}/clubs.py", 'name="gym_club_category_valid"'),
    ("AFR-GYM-005", "New club recorded open", CLUBS, "status=sm.OPEN, faculty_councillor_user_id"),
    ("AFR-GYM-006", "Student Admin confirms", CLUBS, "club.status = t.to"),
    ("AFR-GYM-007", "Club Head replaces leaders", LEAD, "def change_leadership("),
    ("AFR-GYM-008", "New leaders valid students", LEAD, "people.require_students("),
    ("AFR-GYM-009", "Only current leaders remain", f"{MODELS}/clubs.py",
     'name="gym_leader_one_current_per_role"'),
    ("AFR-GYM-010", "Book a session", BOOK, "def book_session("),
    ("AFR-GYM-011", "Start precedes end", RULES, "def check_time_range("),
    ("AFR-GYM-012", "No overlapping booking", BOOK, "clash = rules.find_conflict("),
    ("AFR-GYM-013", "Notify on session booked", BOOK, "def _notify("),
    ("AFR-GYM-014", "Book an event", BOOK, "def book_event("),
    ("AFR-GYM-015", "Notify on event booked", BOOK, "notifications.EVENT_BOOKED"),
    ("AFR-GYM-016", "Apply to a confirmed club", MEM, "def apply("),
    ("AFR-GYM-017", "Applications to several clubs", f"{MODELS}/memberships.py",
     'fields=["club", "user_id"]'),
    ("AFR-GYM-018", "No duplicate application", MEM, 'code="duplicate_application")\n'),
    ("AFR-GYM-019", "Application recorded open", MEM,
     "description=text, status=sm.OPEN)"),
    ("AFR-GYM-020", "Club Head sees pending applications", SCOPE, "def memberships_for("),
    ("AFR-GYM-021", "Approve with optional remarks", MEM, "membership.remarks = remarks"),
    ("AFR-GYM-022", "Approved becomes confirmed", MEM, "membership.status = t.to"),
    ("AFR-GYM-023", "Create a poll", POLL, "def create_poll("),
    ("AFR-GYM-024", "At least two choices", RULES, "MIN_CHOICES = 2"),
    ("AFR-GYM-025", "Notify target students", NOTE, "def _expand("),
    ("AFR-GYM-026", "Eligible student sees active polls", SCOPE, "def polls_targeting("),
    ("AFR-GYM-027", "Eligible student casts one choice", POLL, "def cast_vote("),
    ("AFR-GYM-028", "No second vote; counted tally", f"{G}/selectors/polls.py", "def tallies("),
    ("AFR-GYM-029", "Submit a budget request", BUD, "def submit("),
    ("AFR-GYM-030", "Reject negative or missing file", BUD, "rules.check_amount(amount)"),
    ("AFR-GYM-031", "Stored open, no approval", f"{MODELS}/budget.py",
     'name="gym_budget_status_open"'),
    ("AFR-GYM-032", "Submit an event report", REP, "def submit("),
    ("AFR-GYM-033", "Report file required", REP, 'missing_code="report_file_required"'),
    ("AFR-GYM-034", "Assigned councillor reviews reports", SCOPE, "def councillor_clubs("),
]

LIVE = ([f"BR-GYM-{i:03d}" for i in range(1, 22)] + [f"UC-GYM-{i:03d}" for i in range(1, 13)]
        + [f"BW-GYM-{i:02d}" for i in range(1, 4)] + [f"CFR-GYM-{i:03d}" for i in range(1, 8)]
        + [f"AFR-GYM-{i:03d}" for i in range(1, 35)])


def line_of(path: str, needle: str) -> int | None:
    text = (ROOT / path).read_text()
    at = text.find(needle)
    return None if at < 0 else text.count("\n", 0, at) + 1


def main() -> int:
    problems = sorted(set(LIVE) - {r[0] for r in REFERENCE})
    problems = [f"{i}: no reference entry" for i in problems]
    rows = []
    for spec_id, what, path, needle in REFERENCE:
        line = line_of(path, needle)
        if line is None:
            problems.append(f"{spec_id}: {needle!r} not found in {path}")
            continue
        rows.append(f"| {spec_id} | {what} | [{path}:{line}](../../{path}#L{line}) |")
    if problems:
        print("gymkhana reference does not resolve:\n  " + "\n  ".join(problems))
        return 1
    OUT.write_text("# Gymkhana: where each spec id is enforced\n\n"
                   "Written by `ops/docs/gymkhana_reference.py`; do not edit by hand.\n\n"
                   "| Id | Requires | Enforced at |\n|---|---|---|\n" + "\n".join(rows) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} ids)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
