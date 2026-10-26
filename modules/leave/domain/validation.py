"""What a request must satisfy before it progresses (CFR-EL-003, BR-EL-001 to 014, BR-EL-025)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain import counting
from modules.leave.domain import policy as pol
from modules.leave.domain.overlap import Interval, first_collision


@dataclass(frozen=True)
class Problem:
    code: str
    message: str
    field: str = ""


@dataclass(frozen=True)
class Draft:
    category: str
    start: date
    end: date
    half: str = counting.FULL
    purpose: str = ""
    station_leave: bool = False
    station_from: date | None = None
    station_to: date | None = None
    station_address: str = ""
    evidence_reference: str = ""
    substitute_user_id: int | None = None


@dataclass(frozen=True)
class CalendarView:
    """The effective published calendar for the year the leave falls in (BR-EL-031)."""

    published: bool
    closed: frozenset[date] = frozenset()
    restricted: frozenset[date] = frozenset()


@dataclass(frozen=True)
class Context:
    applicant_id: int
    applicant_kind: str
    today: date
    policy: pol.Policy
    calendar: CalendarView
    #: Days still spendable in the charged year: ledger balance less pending requests.
    available: Decimal
    #: The applicant's own pending and approved leave (BR-EL-012).
    existing: list[Interval] = field(default_factory=list)
    vacations: tuple[tuple[date, date], ...] = ()


def chargeable(draft: Draft, ctx: Context) -> Decimal:
    return counting.chargeable_days(
        draft.category, draft.start, draft.end, half=draft.half,
        closed_holidays=ctx.calendar.closed, weekend_days=ctx.policy.weekend_days)


def new_leave_problems(draft: Draft, ctx: Context) -> list[Problem]:
    """Ordered so the first problem is the one the applicant can act on."""
    shape = _shape(draft, ctx)
    if shape:
        return shape
    problems = _calendar(draft, ctx)
    if problems:
        return problems
    days = chargeable(draft, ctx)
    if days <= 0:
        return [Problem("no_chargeable_days",
                        "Those dates are all weekends or closed holidays, so there is no leave "
                        "to apply for.", "start")]
    clash = first_collision(Interval(draft.start, draft.end, draft.half), ctx.existing)
    if clash is not None:
        problems.append(Problem(
            "overlaps_own_leave",
            f"You already have leave from {clash.start} to {clash.end} that overlaps these "
            f"dates. Withdraw or cancel it first, or choose other dates.", "start"))
    if days > ctx.available:
        problems.append(Problem(
            "insufficient_balance",
            f"This needs {days} day(s) of {draft.category} and {ctx.available} remain "
            f"available after your pending requests.", "category"))
    problems.extend(_details(draft, ctx, days))
    return problems


def extension_problems(*, base_category: str, base_start: date, base_effective_end: date,
                       draft: Draft, ctx: Context) -> list[Problem]:
    """BR-EL-025: the base must be ongoing EL/COL/VL and the extra days must follow it directly."""
    rule = cat.get(base_category)
    if not rule.extendable:
        return [Problem("not_extendable",
                        f"{base_category} cannot be extended; only EL, COL and VL can.")]
    if not base_start <= ctx.today <= base_effective_end:
        return [Problem("not_ongoing",
                        "Only leave you are currently on can be extended. Before it starts, "
                        "cancel it and apply afresh; after it ends, submit your resumption.")]
    if draft.start != base_effective_end + timedelta(days=1):
        return [Problem("extension_not_contiguous",
                        f"An extension starts the day after the leave ends, "
                        f"{base_effective_end + timedelta(days=1)}.", "end")]
    if draft.end < draft.start:
        return [Problem("invalid_period", "The extension cannot end before it starts.", "end")]
    return new_leave_problems(draft, ctx)


def substitute_problems(*, applicant_id: int, nominee_id: int | None, nominee_kind: str | None,
                        nominee_active: bool, nominee_leave: list[Interval],
                        period: Interval) -> list[Problem]:
    """BR-EL-014: another employee, not the applicant, and not away themselves."""
    if nominee_id is None:
        return [Problem("substitute_required",
                        "This leave needs a substitute. Nominate a colleague to cover for you.",
                        "substitute_user_id")]
    if nominee_id == applicant_id:
        return [Problem("substitute_is_applicant",
                        "You cannot nominate yourself as your own substitute.",
                        "substitute_user_id")]
    if nominee_kind not in cat.EMPLOYEE_KINDS or not nominee_active:
        return [Problem("substitute_not_employee",
                        "The substitute must be a serving faculty or staff member.",
                        "substitute_user_id")]
    clash = first_collision(period, nominee_leave)
    if clash is not None:
        return [Problem("substitute_on_leave",
                        f"Your nominee has leave from {clash.start} to {clash.end} during this "
                        f"period. Nominate someone who will be present.", "substitute_user_id")]
    return []


def _shape(draft: Draft, ctx: Context) -> list[Problem]:
    if draft.category not in cat.CATEGORIES:
        return [Problem("unknown_category",
                        f"{draft.category} is not a leave category.", "category")]
    if not cat.applicable(draft.category, ctx.applicant_kind):
        return [Problem("category_not_applicable",
                        f"{cat.LABELS[draft.category]} is not available to "
                        f"{ctx.applicant_kind or 'your account'}.", "category")]
    if draft.end < draft.start:
        return [Problem("invalid_period", "The leave cannot end before it starts.", "end")]
    if draft.half not in counting.HALVES:
        return [Problem("invalid_half", "Choose the first or the second half.", "half")]
    if draft.half and not cat.get(draft.category).half_day:
        return [Problem("half_day_not_allowed",
                        "Only Casual Leave can be taken for half a day.", "half")]
    if draft.half and draft.start != draft.end:
        return [Problem("half_day_single_date",
                        "A half day covers a single date; make the start and end the same.",
                        "end")]
    earliest = ctx.today - timedelta(days=ctx.policy.max_backdate_days)
    if draft.start < earliest:
        return [Problem("backdated",
                        "Leave that has already been taken cannot be applied for here. Ask the "
                        "Leave Administrator to record it if it was sanctioned on paper.",
                        "start")]
    if not draft.purpose.strip():
        return [Problem("purpose_required", "State the purpose of the leave.", "purpose")]
    return []


def _calendar(draft: Draft, ctx: Context) -> list[Problem]:
    if not ctx.calendar.published:
        return [Problem("calendar_not_published",
                        f"No holiday calendar is published for {draft.start.year}. Ask the "
                        f"Leave Administrator to publish it before applying.", "start")]
    if draft.category == cat.RH:
        stray = [d for d in counting.days_between(draft.start, draft.end)
                 if d not in ctx.calendar.restricted]
        if stray:
            return [Problem("not_restricted_holiday",
                            f"{stray[0]} is not a Restricted Holiday in the published calendar.",
                            "start")]
    if draft.category == cat.VL:
        inside = any(lo <= draft.start and draft.end <= hi for lo, hi in ctx.vacations)
        if not inside:
            return [Problem("outside_vacation",
                            "Vacation Leave can only be taken inside a vacation period of the "
                            "Academic Calendar.", "start")]
    return []


def _details(draft: Draft, ctx: Context, days: Decimal) -> list[Problem]:
    problems: list[Problem] = []
    # BR-EL-013: Station Leave lives inside this application, never as its own request.
    if draft.station_leave:
        if not (draft.station_from and draft.station_to and draft.station_address.strip()):
            problems.append(Problem(
                "station_details_required",
                "Station Leave needs the dates you will be away from Jabalpur and an address.",
                "station_address"))
        elif draft.station_to < draft.station_from:
            problems.append(Problem("station_period_invalid",
                                    "Station Leave cannot end before it starts.", "station_to"))
        elif draft.station_to < draft.start or draft.station_from > draft.end:
            problems.append(Problem("station_outside_leave",
                                    "Station Leave must fall within or around the leave period.",
                                    "station_from"))
    rule = ctx.policy.rule(draft.category)
    if (rule.evidence_min_days is not None and days >= rule.evidence_min_days
            and not draft.evidence_reference.strip()):
        problems.append(Problem(
            "evidence_required",
            f"{cat.LABELS[draft.category]} of {rule.evidence_min_days} day(s) or more needs a "
            f"medical evidence reference.", "evidence_reference"))
    return problems
