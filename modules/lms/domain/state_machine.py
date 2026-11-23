"""Closed lifecycle tables: absent edges are refused, never inferred."""

from types import MappingProxyType

from .rules import RuleViolation

CONTENT_TRANSITIONS = MappingProxyType(
    {
        ("DRAFT", "publish", "FACULTY"): "LIVE",
        ("DRAFT", "schedule", "FACULTY"): "SCHEDULED",
        ("SCHEDULED", "schedule", "FACULTY"): "SCHEDULED",
        ("SCHEDULED", "withdraw", "FACULTY"): "DRAFT",
        ("SCHEDULED", "release", "SYSTEM"): "LIVE",
    }
)
GRADE_TRANSITIONS = MappingProxyType(
    {
        ("ABSENT", "save", "FACULTY"): "DRAFT",
        ("ABSENT", "save", "TA"): "DRAFT",
        ("DRAFT", "save", "FACULTY"): "DRAFT",
        ("DRAFT", "save", "TA"): "DRAFT",
        ("DRAFT", "release", "FACULTY"): "RELEASED",
        ("RELEASED", "save", "FACULTY"): "RELEASED",
    }
)


def transition(table, state, event, role, *, now=None, release_at=None):
    target = table.get((state, event, role))
    if target is None:
        raise RuleViolation(
            "Refresh this item and choose an action allowed in its current state.",
            "LMS_STATE_CONFLICT",
        )
    if event == "schedule" and (
        release_at is None or release_at.utcoffset() is None or release_at <= now
    ):
        raise RuleViolation("Choose a future scheduled release time.")
    if (
        event == "release"
        and table is CONTENT_TRANSITIONS
        and (release_at is None or release_at > now)
    ):
        raise RuleViolation("Wait until the scheduled release time before retrying.")
    return target
