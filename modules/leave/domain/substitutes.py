"""Substitute nomination and the consent gate (BR-EL-014, BR-EL-015)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from modules.leave.domain.errors import RuleViolation


@dataclass(frozen=True)
class Interval:
    """One active leave interval of one person, pending or approved."""

    start: date
    end: date
    category: str = ""
    half: str = ""


@dataclass(frozen=True)
class NominationFacts:
    applicant_id: int
    nominee_id: int | None
    nominee_is_employee: bool
    nominee_is_active: bool
    period: Interval
    nominee_intervals: tuple[Interval, ...] = field(default_factory=tuple)


def validate_nomination(facts: NominationFacts) -> None:
    """Refuse an ineligible nominee, naming the one condition that failed."""
    if facts.nominee_id is None:
        raise RuleViolation("Nominate one substitute for the responsibility period.",
                            code="substitute_required")
    if facts.nominee_id == facts.applicant_id:
        raise RuleViolation("You cannot nominate yourself as your own substitute.",
                            code="substitute_is_applicant")
    if not facts.nominee_is_employee:
        raise RuleViolation("A substitute must be a faculty or staff employee.",
                            code="substitute_not_employee")
    if not facts.nominee_is_active:
        raise RuleViolation("That employee's account is not active.",
                            code="substitute_inactive")
    clash = overlapping(facts.period, facts.nominee_intervals)
    if clash is not None:
        raise RuleViolation(
            "Your substitute already has leave from "
            f"{clash.start.isoformat()} to {clash.end.isoformat()}.",
            code="substitute_unavailable")


def overlapping(period: Interval, others: tuple[Interval, ...]) -> Interval | None:
    """The first overlapping interval, or None. Touching periods are not overlap."""
    for other in others:
        if other.end < period.start or other.start > period.end:
            continue
        return other
    return None
