"""Whether a request may proceed, decided before anything is written (CFR-EL-003).

Every check fails closed: an absent fact is a refusal with a named reason, never
a default that quietly passes. The service layer turns these into
DomainError subclasses with actionable messages.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain import overlap as ov
from modules.leave.domain.policy import Policy


@dataclass(frozen=True)
class Outcome:
    reason: str
    message: str
    #: An advisory finding is shown to the applicant but does not stop submission.
    #: Every check here blocks today; the flag exists so a future non-blocking
    #: check does not have to change this contract.
    blocking: bool = True


@dataclass
class Assessment:
    is_valid: bool
    outcomes: list[Outcome] = field(default_factory=list)

    @property
    def reasons(self) -> list[str]:
        return [o.reason for o in self.outcomes]


@dataclass(frozen=True)
class Facts:
    """Everything the rules need, gathered once by the service layer."""
    category: str
    kind: str
    start: date
    end: date
    half_day: bool = False
    half: str | None = None
    available_days: Decimal = Decimal("0")
    restricted_holidays: set[date] = field(default_factory=set)
    vacation_periods: list[tuple[date, date]] = field(default_factory=list)
    existing: list[ov.Interval] = field(default_factory=list)


def _check_category(policy: Policy, facts: Facts, out: list[Outcome]) -> None:
    if facts.category not in cat.CATEGORIES:
        out.append(Outcome("unknown_category",
                           "That leave category is not one this system supports."))
        return
    permitted = policy.kinds_permitted(facts.category)
    if facts.kind not in permitted:
        out.append(Outcome(
            "category_not_applicable",
            f"{facts.category} is not available to a {facts.kind} employee."))


def _check_entitlement(policy: Policy, facts: Facts, requested: Decimal,
                       out: list[Outcome]) -> None:
    if facts.available_days < requested:
        out.append(Outcome(
            "insufficient_balance",
            f"This request needs {requested} days but only "
            f"{facts.available_days} are available."))


def _check_calendar(facts: Facts, out: list[Outcome]) -> None:
    """RH and VL both depend on a calendar, so neither may fall back to dates."""
    if facts.category == cat.RESTRICTED_HOLIDAY and not facts.restricted_holidays:
        out.append(Outcome(
            "no_published_calendar",
            "No published Restricted Holiday calendar is available to check "
            "this request against."))
    if facts.category == cat.VACATION and not facts.vacation_periods:
        out.append(Outcome(
            "no_vacation_periods",
            "No vacation period is configured, so Vacation Leave cannot be "
            "checked for this period."))
    if facts.category == cat.VACATION and facts.vacation_periods:
        inside = any(start <= facts.start and facts.end <= end
                     for start, end in facts.vacation_periods)
        if not inside:
            out.append(Outcome(
                "outside_vacation_period",
                "Vacation Leave may only be availed inside a configured "
                "vacation period."))


def _check_overlap(facts: Facts, out: list[Outcome]) -> None:
    candidate = ov.Interval(facts.start, facts.end, facts.category,
                            facts.half_day, facts.half)
    clash = ov.find_conflict(candidate, facts.existing)
    if clash is not None:
        out.append(Outcome(
            "overlapping_leave",
            f"This period overlaps leave already recorded from "
            f"{clash.start:%d %b %Y} to {clash.end:%d %b %Y}."))


def assess(policy: Policy, facts: Facts, requested: Decimal) -> Assessment:
    """Run every rule and report all failures, so one round trip tells the
    applicant everything that is wrong rather than the first thing."""
    out: list[Outcome] = []
    _check_category(policy, facts, out)
    _check_entitlement(policy, facts, requested, out)
    _check_calendar(facts, out)
    _check_overlap(facts, out)
    return Assessment(is_valid=not out, outcomes=out)


def substitute_eligible(*, nominee_id: int, applicant_id: int,
                        period_start: date, period_end: date,
                        nominee_intervals: list[ov.Interval],
                        kind: str) -> tuple[bool, str]:
    """BR-EL-014: another employee, not the applicant, free for the period."""
    if nominee_id == applicant_id:
        return False, "nominee_is_applicant"
    if kind not in cat.EMPLOYEE_KINDS:
        return False, "nominee_not_employee"
    clash = ov.find_conflict(
        ov.Interval(period_start, period_end, cat.CASUAL), nominee_intervals)
    if clash is not None:
        return False, "nominee_overlapping_leave"
    return True, ""