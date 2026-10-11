"""What makes a request able to progress (BR-EL-001..013, BR-EL-031).

Every check returns a `Failure` instead of raising, so a caller can report all
the problems at once — a validation screen that reveals one error per attempt
is how a five-minute form becomes a twenty-minute one. The service turns the
list into a 409 with the failures as details.

Pure Python: the employee, balance, calendar and existing leave arrive as
arguments.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain import counting


@dataclass(frozen=True)
class Failure:
    code: str
    message: str
    details: dict | None = None


@dataclass(frozen=True)
class Interval:
    """One request's occupancy of the calendar, for the overlap check."""

    start: date
    end: date
    category: str = ""
    half: str = ""


def category_applicability(category: str, employee_kind: str) -> Failure | None:
    """BR-EL-001 / BR-EL-006 — is this category available to this employee?"""
    if category not in cat.CATEGORIES:
        return Failure("unsupported_category",
                       f"{category!r} is not a leave category in this baseline.",
                       {"supported": list(cat.CATEGORIES)})
    if not cat.may_be_used_by(category, employee_kind):
        return Failure(
            "category_not_applicable",
            f"{cat.LABELS[category]} is not available to {employee_kind} employees.",
            {"category": category, "employee_kind": employee_kind})
    return None


def balance_sufficient(category: str, requested: Decimal,
                       available: Decimal) -> Failure | None:
    """AFR-EL-003.2 — does the account cover what is being asked for?"""
    if requested <= 0:
        return None
    if available < requested:
        return Failure(
            "insufficient_balance",
            f"Only {available} {cat.LABELS[category]} day(s) are available; "
            f"{requested} requested.",
            {"requested": str(requested), "available": str(available)})
    return None


def rh_applicability(days: Iterable[date],
                     rh_dates: Iterable[date]) -> Failure | None:
    """BR-EL-003 / BR-EL-031 — an RH request must match the effective calendar."""
    allowed = set(rh_dates)
    unmatched = sorted(d for d in days if d not in allowed)
    if unmatched:
        return Failure(
            "rh_not_in_calendar",
            "A Restricted Holiday request must correspond to a Restricted "
            "Holiday in the currently effective published calendar.",
            {"dates_not_restricted_holidays": [d.isoformat() for d in unmatched]})
    return None


def vl_vacation_applicability(start: date, end: date,
                              vacation_periods: Sequence[tuple[date, date]]
                              ) -> Failure | None:
    """BR-EL-006 — VL only inside a vacation period from the Academic Calendar."""
    if not vacation_periods:
        return Failure(
            "vacation_calendar_unavailable",
            "No vacation periods are available for this period, so Vacation "
            "Leave cannot be validated.")
    for period_start, period_end in vacation_periods:
        if start >= period_start and end <= period_end:
            return None
    return Failure(
        "vl_outside_vacation_period",
        "Vacation Leave may be availed only during an applicable vacation "
        "period supplied through the institute Academic Calendar.",
        {"period_from": start.isoformat(), "period_to": end.isoformat()})


def halves_overlap(a_half: str, b_half: str) -> bool:
    """BR-EL-012 — two CL halves on one date do not overlap.

    A full day overlaps either half; two halves overlap only when they are the
    same half.
    """
    if not a_half or not b_half:
        return True
    return a_half == b_half


def overlap(candidate: Interval, existing: Sequence[Interval]) -> Failure | None:
    """BR-EL-012 — impermissible overlap with pending or approved leave.

    `existing` is the employee's own active pending or approved leave, so this
    is about one person's calendar, not about authority.
    """
    clashing: list[dict] = []
    for other in existing:
        if candidate.end < other.start or other.end < candidate.start:
            continue
        same_day = candidate.start == candidate.end == other.start == other.end
        if (candidate.category == cat.CL and other.category == cat.CL and same_day
                and not halves_overlap(candidate.half, other.half)):
            continue                     # first half + second half on one date
        clashing.append({
            "category": other.category,
            "from": other.start.isoformat(),
            "to": other.end.isoformat(),
            "half": other.half,
        })
    if not clashing:
        return None
    return Failure(
        "overlapping_leave",
        "This request overlaps leave that is already pending or approved.",
        {"overlapping": clashing})


def extension_window(*, category: str, base_from: date, base_to: date,
                     requested_from: date, requested_to: date) -> Failure | None:
    """BR-EL-025 — an extension is additional EL/COL/VL while it is ongoing."""
    if category not in cat.EXTENDABLE:
        return Failure(
            "extension_not_available",
            f"{cat.LABELS[category]} cannot be extended; extension applies to "
            "ongoing EL, COL or VL.",
            {"extendable": sorted(cat.EXTENDABLE)})
    if requested_to <= base_to:
        return Failure(
            "extension_not_incremental",
            "An extension must add time beyond the end of the ongoing leave.",
            {"ongoing_to": base_to.isoformat(),
             "requested_to": requested_to.isoformat()})
    if requested_from > requested_to:
        return Failure("period_invalid", "The requested period is not a valid range.")
    return None


def cancellation_window(*, approved_start: date, today: date) -> Failure | None:
    """BR-EL-023 — cancellation exists only before the approved start date."""
    if today >= approved_start:
        return Failure(
            "leave_already_started",
            "Cancellation is available only before the approved start date; "
            "once leave has begun the extension or resumption process applies.",
            {"approved_start": approved_start.isoformat()})
    return None


def resumption_window(*, category: str) -> Failure | None:
    """BR-EL-027 — formal resumption review applies to EL, COL and VL."""
    if category not in cat.RESUMPTION_REVIEWED:
        return Failure(
            "resumption_review_not_applicable",
            "Resumption review applies to EL, COL and VL.",
            {"applicable": sorted(cat.RESUMPTION_REVIEWED)})
    return None


def substitute_eligibility(*, applicant_user_id: int, nominee_user_id: int,
                           nominee_exists: bool,
                           nominee_leave: Sequence[Interval]) -> Failure | None:
    """BR-EL-014 — one eligible substitute, not the applicant, free at the time."""
    if not nominee_exists:
        return Failure("substitute_not_employee",
                       "The nominated substitute must be another employee.")
    if nominee_user_id == applicant_user_id:
        return Failure("substitute_is_applicant",
                       "The applicant cannot be their own substitute.")
    clashing = [
        {"from": i.start.isoformat(), "to": i.end.isoformat(),
         "category": i.category}
        for i in nominee_leave
    ]
    if clashing:
        return Failure(
            "substitute_unavailable",
            "The nominated substitute has pending or approved leave during the "
            "responsibility period.",
            {"overlapping": clashing})
    return None


def validate_new_request(*, category: str, employee_kind: str, start: date,
                         end: date, half: str, days: Decimal,
                         available: Decimal, existing: Sequence[Interval],
                         rh_dates: Iterable[date] = (),
                         vacation_periods: Sequence[tuple[date, date]] = ()
                         ) -> list[Failure]:
    """The whole gate for a new application, in the order EL-UC-001 M4 lists it."""
    failures: list[Failure] = []
    if end < start:
        failures.append(Failure("period_invalid",
                                "The requested period is not a valid range."))
        return failures

    applicability = category_applicability(category, employee_kind)
    if applicability:
        failures.append(applicability)

    if half and (not cat.supports_half_day(category) or start != end):
        failures.append(Failure(
            "half_day_not_supported",
            "A half day is available for Casual Leave on a single date only."))

    count = counting.chargeable_days(category=category, start=start, end=end,
                                     half=half)
    if category == cat.RH:
        rh_failure = rh_applicability(count.charged, rh_dates)
        if rh_failure:
            failures.append(rh_failure)
    if category == cat.VL:
        vl_failure = vl_vacation_applicability(start, end, vacation_periods)
        if vl_failure:
            failures.append(vl_failure)

    cover = balance_sufficient(category, days, available)
    if cover:
        failures.append(cover)

    clash = overlap(Interval(start, end, category, half), existing)
    if clash:
        failures.append(clash)
    return failures
