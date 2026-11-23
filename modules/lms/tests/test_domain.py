from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import product

import pytest

from modules.lms.domain import rules
from modules.lms.domain.state_machine import CONTENT_TRANSITIONS, GRADE_TRANSITIONS, transition

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("value", [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity")])
def test_points_refuse_invalid(value):
    with pytest.raises(rules.RuleViolation):
        rules.points(value)


@pytest.mark.parametrize(
    "kind,text,url,file,material",
    [
        ("TEXT", "Work", "", False, False),
        ("NOTE", "Notes", "", False, True),
        ("LINK", "", "https://example.org/task", False, False),
        ("FILE", "", "", True, False),
    ],
)
def test_payload_variants(kind, text, url, file, material):
    rules.payload(kind, text, url, file, material=material)


@pytest.mark.parametrize(
    "kind,text,url,file",
    [
        ("TEXT", " ", "", False),
        ("TEXT", "x", "https://example.org", False),
        ("FILE", "x", "", True),
        ("LINK", "", "javascript:alert(1)", False),
        ("LINK", "", "https://user:password@example.org", False),
        ("LINK", "", "https:///", False),
        ("OTHER", "", "", False),
    ],
)
def test_payload_refusals(kind, text, url, file):
    with pytest.raises(rules.RuleViolation):
        rules.payload(kind, text, url, file)


def test_br_lms_013_deadline_is_inclusive_and_type_checked():
    rules.submission("TEXT", "TEXT", NOW, NOW)
    with pytest.raises(rules.RuleViolation, match="due date"):
        rules.submission("TEXT", "TEXT", NOW + timedelta(microseconds=1), NOW)
    with pytest.raises(rules.RuleViolation, match="type"):
        rules.submission("FILE", "TEXT", NOW, NOW)


@pytest.mark.parametrize(
    "field,value",
    [
        ("instructions", " "),
        ("due_at", None),
        ("due_at", NOW.replace(tzinfo=None)),
        ("submission_type", "OTHER"),
        ("points_possible", Decimal("-1")),
    ],
)
def test_br_lms_009_assignment_configuration(field, value):
    data = {
        "instructions": "Work",
        "due_at": NOW,
        "submission_type": "TEXT",
        "points_possible": Decimal("0"),
    }
    rules.assignment(**data)
    data[field] = value
    with pytest.raises(rules.RuleViolation):
        rules.assignment(**data)


def test_edit_guards_cover_each_boundary():
    old = {"submission_type": "TEXT", "due_at": NOW, "points_possible": Decimal(10)}
    rules.edit_assignment(
        old,
        {**old, "due_at": NOW + timedelta(days=1)},
        has_submissions=True,
        has_grades=False,
        last_submission_at=NOW,
    )
    for change, submitted, graded, last in [
        ({"submission_type": "FILE"}, True, False, None),
        ({"due_at": NOW - timedelta(seconds=1)}, True, False, None),
        ({"due_at": NOW}, True, False, NOW + timedelta(seconds=1)),
        ({"points_possible": Decimal(20)}, False, True, None),
    ]:
        with pytest.raises(rules.RuleViolation):
            rules.edit_assignment(
                old,
                {**old, **change},
                has_submissions=submitted,
                has_grades=graded,
                last_submission_at=last,
            )
    rules.edit_assignment(
        old, {**old, "submission_type": "FILE"}, has_submissions=False, has_grades=False
    )


@pytest.mark.parametrize(
    "table,states,events",
    [
        (
            CONTENT_TRANSITIONS,
            ("DRAFT", "SCHEDULED", "PUBLISHED", "AVAILABLE"),
            ("publish", "schedule", "withdraw", "release"),
        ),
        (GRADE_TRANSITIONS, ("ABSENT", "DRAFT", "RELEASED"), ("save", "release")),
    ],
)
def test_state_tables_exhaustively_refuse_missing_edges(table, states, events):
    for state, event, role in product(
        states, events, ("STUDENT", "FACULTY", "TA", "OBSERVER", "SYSTEM")
    ):
        kwargs = {
            "now": NOW,
            "release_at": NOW + timedelta(seconds=1) if event == "schedule" else NOW,
        }
        if (state, event, role) in table:
            assert transition(table, state, event, role, **kwargs) == table[state, event, role]
        else:
            with pytest.raises(rules.RuleViolation):
                transition(table, state, event, role, **kwargs)


@pytest.mark.parametrize("at", [None, NOW, NOW - timedelta(seconds=1), NOW.replace(tzinfo=None)])
def test_schedule_requires_future_aware_time(at):
    with pytest.raises(rules.RuleViolation):
        transition(CONTENT_TRANSITIONS, "DRAFT", "schedule", "FACULTY", now=NOW, release_at=at)


@pytest.mark.parametrize("at", [None, NOW + timedelta(seconds=1)])
def test_system_cannot_release_early(at):
    with pytest.raises(rules.RuleViolation):
        transition(CONTENT_TRANSITIONS, "SCHEDULED", "release", "SYSTEM", now=NOW, release_at=at)


def test_role_refusal_names_excluded_actors():
    rules.require_role("FACULTY", ("FACULTY",))
    for role in ("STUDENT", "TA", "OBSERVER", "UNKNOWN"):
        with pytest.raises(rules.RuleViolation):
            rules.require_role(role, ("FACULTY",))
