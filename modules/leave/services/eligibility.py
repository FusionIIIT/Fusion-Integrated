"""Gather the facts `domain.eligibility` needs, and run it.

The domain rules stay free of the database; this is the one place that reads the
balance, the calendar and the person's other leave to fill in `Facts`. Every
check re-runs at submission and at decision, because a draft applied weeks ago
was checked against a policy and a balance that have both since moved.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain import eligibility as domain
from modules.leave.domain import overlap as ov
from modules.leave.models import LeaveBalance, LeaveRequest
from modules.leave.domain import state_machine as sm
from modules.leave.services import calendar, policy

log = logging.getLogger("fusion.leave.eligibility")

Assessment = domain.Assessment
Finding = domain.Outcome


def available_days(*, person_id: int, category: str, year: int) -> Decimal:
    """The projected balance, absent balance read as zero rather than as an
    error: a person who has never taken leave has a balance, it is simply empty.
    """
    row = LeaveBalance.objects.filter(
        user_id=person_id, year=year, category=category).first()
    return Decimal("0") if row is None else Decimal(row.days)


def existing_intervals(*, person_id: int,
                       exclude_request_id: int | None = None) -> list[ov.Interval]:
    """Leave still live for this person: pending or approved and not yet returned."""
    rows = LeaveRequest.objects.filter(user_id=person_id, status__in=sm.CONSUMING)
    if exclude_request_id is not None:
        rows = rows.exclude(pk=exclude_request_id)
    return [ov.Interval(row.start_date, row.end_date, row.category, row.half_day,
                        row.half) for row in rows]


def assess(*, person_id: int, category: str, start_date: date, end_date: date,
           requested_days: Decimal, kind: str, half_day: bool = False,
           half: str = "", exclude_request_id: int | None = None) -> Assessment:
    """Run every pre-condition and report all of them at once."""
    pol = policy.current_policy()
    facts = domain.Facts(
        category=category, kind=kind, start=start_date, end=end_date,
        half_day=half_day, half=half or None,
        available_days=available_days(person_id=person_id, category=category,
                                      year=start_date.year),
        restricted_holidays=_restricted_holidays(category, start_date, end_date),
        vacation_periods=_vacation_periods(category, start_date, end_date),
        existing=_existing_excluding(person_id, exclude_request_id),
    )
    return domain.assess(pol, facts, requested_days)


def blocking(findings: Assessment) -> list[domain.Outcome]:
    """Only a refusal stops a submission; an advisory note does not."""
    return [f for f in findings.outcomes if f.blocking]


def _restricted_holidays(category: str, start: date, end: date) -> set[date]:
    if category != cat.RESTRICTED_HOLIDAY:
        return set()
    return calendar.restricted_holiday_dates(start, end)


def _vacation_periods(category: str, start: date, end: date) -> list[tuple[date, date]]:
    if category != cat.VACATION:
        return []
    return [(row.start_date, row.end_date)
            for row in calendar.vacation_periods(start, end)]


def _existing_excluding(person_id: int,
                        exclude_request_id: int | None) -> list[ov.Interval]:
    """A request re-checked at submission must not collide with its own row."""
    return existing_intervals(person_id=person_id,
                              exclude_request_id=exclude_request_id)


def substitute_eligible(*, nominee_id: int, applicant_id: int, period_start: date,
                        period_end: date, nominee_kind: str,
                        applicant_leave: LeaveRequest | None = None
                        ) -> domain.Outcome | None:
    """BR-EL-014: someone else, an employee, and free for the whole period.
    Returns the refusal when there is one, or None when they may be nominated."""
    intervals = existing_intervals(person_id=nominee_id)
    eligible, reason = domain.substitute_eligible(
        nominee_id=nominee_id, applicant_id=applicant_id,
        period_start=period_start, period_end=period_end,
        nominee_intervals=intervals, kind=nominee_kind)
    if eligible:
        return None
    return domain.Outcome(reason, _SUBSTITUTE_MESSAGES.get(
        reason, "This person cannot be nominated as substitute."))


_SUBSTITUTE_MESSAGES = {
    "nominee_is_applicant": "You cannot nominate yourself as your substitute.",
    "nominee_not_employee": "A substitute must be a faculty member or staff.",
    "nominee_overlapping_leave": "That person is on leave for part of this period.",
}