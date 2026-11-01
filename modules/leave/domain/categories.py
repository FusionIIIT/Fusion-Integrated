"""Leave categories as data: entitlement, counting, year-end outcome.

Everything here is a lookup or a pure function over dates — no Django, no I/O,
so the rules test in milliseconds with no database. The numbers themselves
(policy supplies 8, 2, 15, 30, 60, 20) arrive as arguments, because the baseline
says validation uses the CURRENT CONFIGURED values (BR-EL-030) rather than a
published version.

    CL   8 days, first/second half, lapses
    RH   2 days, must match the published RH calendar, lapses
    SCL  15 days, admissibility is the authority's judgement, lapses
    EL   30 days for non-faculty, carries forward
    VL   60 days for faculty, vacation-period bound, converts to EL 2:1
    COL  20 days, medical/balance controlled, carries forward
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

CL = "cl"
RH = "rh"
SCL = "scl"
EL = "el"
COL = "col"
VL = "vl"

CATEGORIES: tuple[str, ...] = (CL, RH, SCL, EL, COL, VL)

LABELS = {
    CL: "Casual Leave",
    RH: "Restricted Holiday",
    SCL: "Special Casual Leave",
    EL: "Earned Leave",
    COL: "Commuted Leave",
    VL: "Vacation Leave",
}

FACULTY = "faculty"
STAFF = "staff"
EMPLOYEE_KINDS = (FACULTY, STAFF)

FIRST_HALF = "first"
SECOND_HALF = "second"
HALVES = (FIRST_HALF, SECOND_HALF)

#: Year-end treatment, one per category (BR-EL-002..009).
LAPSE = "lapse"
CARRY_FORWARD = "carry_forward"
CONVERT = "convert"


@dataclass(frozen=True)
class Category:
    code: str
    label: str
    #: Days credited at the start of the leave year, to each eligible employee.
    annual_days: int
    #: Weekends and closed holidays inside the interval count as leave
    #: (BR-EL-011). False for CL, SCL and RH.
    continuous_counting: bool
    #: Unused balance crosses the year boundary (BR-EL-005, BR-EL-009).
    carries_forward: bool
    #: First-half / second-half requests, 0.5 each (BR-EL-010).
    allows_half_day: bool
    #: EL/COL/VL may be extended while ongoing, and are formally resumed.
    extension_eligible: bool
    resumption_applies: bool
    #: The Unit Head is the FINAL authority, not a recommender (BR-EL-016).
    unit_head_final: bool
    #: Who may hold it. VL is faculty-only; the 30-day EL credit is
    #: non-faculty-only, though faculty do hold EL once VL has converted.
    kinds: tuple[str, ...]
    #: VL may be availed only inside a vacation period (BR-EL-006).
    requires_vacation_period: bool = False


CATEGORY_TABLE: tuple[Category, ...] = (
    Category(CL, LABELS[CL], 8, False, False, True, False, False, True,
             EMPLOYEE_KINDS),
    Category(RH, LABELS[RH], 2, False, False, False, False, False, True,
             EMPLOYEE_KINDS),
    Category(SCL, LABELS[SCL], 15, False, False, False, False, False, False,
             EMPLOYEE_KINDS),
    Category(EL, LABELS[EL], 30, True, True, False, True, True, False,
             (STAFF,)),
    Category(COL, LABELS[COL], 20, True, True, False, True, True, False,
             EMPLOYEE_KINDS),
    Category(VL, LABELS[VL], 60, True, False, False, True, True, False,
             (FACULTY,), requires_vacation_period=True),
)

_BY_CODE = {c.code: c for c in CATEGORY_TABLE}


def category(code: str) -> Category:
    """Look a category up. An unknown code is a programming error, not a
    user-visible one — the serializer validates against CATEGORIES first."""
    try:
        return _BY_CODE[code]
    except KeyError as exc:
        raise LookupError(f"Unknown leave category {code!r}.") from exc


def eligible_categories(kind: str) -> tuple[str, ...]:
    """Categories an employee of this kind may apply for (BR-EL-001)."""
    return tuple(c.code for c in CATEGORY_TABLE if kind in c.kinds)


def annual_credit(code: str, kind: str) -> int:
    """Days credited at the start of the leave year. Zero means the category
    is not credited to this employee — faculty take VL and receive EL only
    through conversion (BR-EL-008)."""
    c = category(code)
    return c.annual_days if kind in c.kinds else 0


def weekend_dates(start: date, end: date) -> set[date]:
    """Saturday and Sunday inside the interval, inclusive."""
    out, d = set(), start
    while d <= end:
        if d.weekday() >= 5:
            out.add(d)
        d = date.fromordinal(d.toordinal() + 1)
    return out


def span_days(start: date, end: date) -> int:
    """Calendar days, both ends included."""
    return (end - start).days + 1


@dataclass(frozen=True)
class Interval:
    """A requested period. `half` is set only for a half-day CL."""

    start: date
    end: date
    half: str | None = None

    @property
    def days(self) -> Decimal:
        if self.half:
            return Decimal("0.5")
        return Decimal(span_days(self.start, self.end))

    def overlaps(self, other: Interval) -> bool:
        """BR-EL-012. Two CL halves on the same date do not overlap when they
        occupy different halves — that is the one exception."""
        if self.end < other.start or other.end < self.start:
            return False
        same_day = (self.start == self.end == other.start == other.end)
        different_cl_halves = bool(self.half and other.half
                                   and self.half != other.half)
        return not (same_day and different_cl_halves)


def leave_days(*, code: str, start: date, end: date, half: str | None = None,
               closed_dates: frozenset[date] = frozenset()) -> Decimal:
    """Days a request consumes (BR-EL-010, BR-EL-011).

    EL/COL/VL count continuously, so a weekend or closed holiday inside the
    interval is a leave day. CL, SCL and RH count duty days only — for those,
    weekends and closed holidays drop out.
    """
    c = category(code)
    if c.allows_half_day and half:
        return Decimal("0.5")
    if c.continuous_counting:
        return Decimal(span_days(start, end))
    duty = span_days(start, end) - len(weekend_dates(start, end) | set(closed_dates))
    return Decimal(max(duty, 0))


@dataclass(frozen=True)
class YearEndAction:
    kind: str
    #: Days lapsed, carried forward, or converted out of the category.
    amount: Decimal
    #: Where converted days land: EL for VL (BR-EL-007).
    target: str | None = None


def year_end_action(code: str, available: Decimal, *,
                    vl_per_el: int = 2) -> YearEndAction:
    """What happens to an unused balance at the year-end boundary (EL-UC-020).

    Unused CL, RH and SCL lapse. Unused VL converts to EL at 2:1, fractions
    included, and the resulting EL is ordinary EL afterwards. EL and COL carry
    forward.
    """
    if available <= 0:
        return YearEndAction("none", available)
    c = category(code)
    if code == VL:
        return YearEndAction(CONVERT, available / Decimal(vl_per_el), target=EL)
    if c.carries_forward:
        return YearEndAction(CARRY_FORWARD, available)
    return YearEndAction(LAPSE, available)
