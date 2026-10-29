"""ELM leave-policy rules -- pure Python, no DB (BR-EL-001 through BR-EL-038).

Every function here is a deterministic calculation or validation that can be
tested in milliseconds without Django. The service layer calls these; the
domain layer never imports from ``models`` or ``services``.

Entitlement values come from BR-EL-002 through BR-EL-009.
Counting rules come from BR-EL-010, BR-EL-011.
Overlap rules from BR-EL-012.
Substitute rules from BR-EL-014, BR-EL-015.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple


# -- Leave categories (BR-EL-001) ----------------------------------------------

class LeaveCategory(str, Enum):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    COL = "COL"
    VL = "VL"


# String constants matching category enum values
CL = LeaveCategory.CL.value
RH = LeaveCategory.RH.value
SCL = LeaveCategory.SCL.value
EL = LeaveCategory.EL.value
COL = LeaveCategory.COL.value
VL = LeaveCategory.VL.value

VALID_CATEGORIES = frozenset(c.value for c in LeaveCategory)


# Categories whose counting includes weekends and holidays (BR-EL-011).
CONTINUOUS_COUNT_CATEGORIES = frozenset({LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL})

# Categories that require higher sanction (BR-EL-017, BR-EL-018).
HIGHER_SANCTION_CATEGORIES = frozenset({LeaveCategory.SCL, LeaveCategory.EL,
                                         LeaveCategory.COL, LeaveCategory.VL})

# Categories that support extension while ongoing (BR-EL-025).
EXTENDABLE_CATEGORIES = frozenset({LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL})

# Categories for which resumption review applies (BR-EL-027).
RESUMABLE_CATEGORIES = frozenset({LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL})


# -- Entitlement constants (BR-EL-002 through BR-EL-009) ----------------------

CL_PER_YEAR = 8           # BR-EL-002: 8 CL/year, no carry-forward
RH_PER_YEAR = 2           # BR-EL-003: 2 RH/year, no carry-forward
SCL_PER_YEAR = 15          # BR-EL-004: 15 SCL/year, no carry-forward
SCL_MAX_PER_YEAR = 15
EL_PER_YEAR = 30           # BR-EL-005: 30 EL/year (non-faculty), carry-forward
NON_FACULTY_EL_PER_YEAR = 30
VL_PER_YEAR = 60           # BR-EL-006: 60 VL/year (faculty only), no carry-forward
FACULTY_VL_DAYS = 60
COL_PER_YEAR = 20          # BR-EL-009: 20 COL/year, carry-forward

EL_MAX_ACCUMULATION = 300   # BR-EL-007: max 300 days accumulation
COL_MAX_BALANCE = 20        # BR-EL-009: max 20 days balance
VACATION_TO_EL_RATIO = 2.0  # BR-EL-008: 2 days VL convert to 1 day EL

# Which entitlements carry forward at year end?
CARRY_FORWARD = frozenset({LeaveCategory.EL, LeaveCategory.COL})
# Which lapse at year end?
LAPSE_AT_YEAR_END = frozenset({LeaveCategory.CL, LeaveCategory.RH,
                                LeaveCategory.SCL, LeaveCategory.VL})


def is_substitute_required(category: str) -> bool:
    """Whether substitute arrangement is required for this leave category."""
    return category in {LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL,
                        LeaveCategory.SCL.value, LeaveCategory.EL.value, LeaveCategory.COL.value, LeaveCategory.VL.value}



# -- Half-day support (BR-EL-010) ---------------------------------------------

class DayHalf(str, Enum):
    FULL = "full"
    FIRST_HALF = "first_half"
    SECOND_HALF = "second_half"


# -- Data containers ----------------------------------------------------------

@dataclass(frozen=True)
class LeaveBalance:
    """Current leave balance for one employee, one category."""
    category: str
    available: float   # may be fractional (half-day CL, VL conversion)
    used: float
    carried_forward: float = 0.0


class ExistingLeave(NamedTuple):
    """A leave already in the system (pending or approved)."""
    start: datetime.date
    end: datetime.date
    category: str
    half: str = DayHalf.FULL    # BR-EL-012: half-day CL exception


class ValidationResult(NamedTuple):
    allowed: bool
    reason: str
    days_counted: float = 0.0


# -- Helpers ------------------------------------------------------------------

def is_weekend(date: datetime.date) -> bool:
    """Saturday (5) or Sunday (6)."""
    return date.weekday() >= 5


def count_leave_days(
    start: datetime.date,
    end: datetime.date,
    category: str,
    holidays: list[datetime.date] | None = None,
    half: str = DayHalf.FULL,
) -> float:
    """Count chargeable leave days between start and end (inclusive).

    BR-EL-011: EL, COL, VL count intervening weekends and closed holidays.
               CL, SCL, RH exclude weekends and closed holidays.
    BR-EL-010: Half-day CL consumes 0.5 day.
    """
    if half != DayHalf.FULL and category == LeaveCategory.CL:
        return 0.5   # BR-EL-010

    continuous = category in CONTINUOUS_COUNT_CATEGORIES
    holiday_set = frozenset(holidays or [])


    days = 0
    cur = start
    one_day = datetime.timedelta(days=1)
    while cur <= end:
        if continuous:
            # BR-EL-011: weekends and holidays count as leave days
            days += 1
        else:
            # CL, SCL, RH: skip weekends and holidays
            if not is_weekend(cur) and cur not in holiday_set:
                days += 1
        cur += one_day
    return float(days)


def annual_entitlement(category: str, is_faculty: bool) -> int:
    """Return the per-year entitlement for a category and employee type."""
    if category == LeaveCategory.CL:
        return CL_PER_YEAR
    if category == LeaveCategory.RH:
        return RH_PER_YEAR
    if category == LeaveCategory.SCL:
        return SCL_PER_YEAR
    if category == LeaveCategory.EL:
        return EL_PER_YEAR if not is_faculty else 0  # BR-EL-005
    if category == LeaveCategory.VL:
        return VL_PER_YEAR if is_faculty else 0      # BR-EL-006
    if category == LeaveCategory.COL:
        return COL_PER_YEAR
    return 0


# -- Year-end processing (BR-EL-007, BR-EL-008) ------------------------------

def convert_unused_vl_to_el(unused_vl: float) -> float:
    """BR-EL-007: 2 VL : 1 EL, fractional conversion allowed."""
    return unused_vl / 2.0


def year_end_balances(
    balances: dict[str, float],
    is_faculty: bool,
) -> dict[str, float]:
    """Compute new balances after year-end processing.

    BR-EL-002: CL lapses.
    BR-EL-003: RH lapses.
    BR-EL-004: SCL lapses.
    BR-EL-005: EL carries forward (non-faculty).
    BR-EL-006: VL does not carry forward (faculty).
    BR-EL-007: Unused VL converts to EL at 2:1.
    BR-EL-008: Converted EL is usable and carries forward.
    BR-EL-009: COL carries forward.
    """
    new = {}

    # Lapsing categories reset to their annual entitlement
    new[LeaveCategory.CL] = float(CL_PER_YEAR)
    new[LeaveCategory.RH] = float(RH_PER_YEAR)
    new[LeaveCategory.SCL] = float(SCL_PER_YEAR)

    # COL: carry forward unused + new credit
    old_col = balances.get(LeaveCategory.COL, 0.0)
    new[LeaveCategory.COL] = old_col + float(COL_PER_YEAR)

    if is_faculty:
        # VL -> EL conversion (BR-EL-007)
        unused_vl = balances.get(LeaveCategory.VL, 0.0)
        el_from_vl = convert_unused_vl_to_el(unused_vl)

        # Faculty do not get direct EL credit, but VL-converted EL carries
        old_el = balances.get(LeaveCategory.EL, 0.0)
        new[LeaveCategory.EL] = old_el + el_from_vl   # BR-EL-008

        # VL resets to full annual entitlement (does not carry forward)
        new[LeaveCategory.VL] = float(VL_PER_YEAR)
    else:
        # Non-faculty: EL carries forward + annual credit
        old_el = balances.get(LeaveCategory.EL, 0.0)
        new[LeaveCategory.EL] = old_el + float(EL_PER_YEAR)

        # Non-faculty have no VL
        new[LeaveCategory.VL] = 0.0

    return new


# -- Overlap detection (BR-EL-012) --------------------------------------------

def has_overlap(
    start: datetime.date,
    end: datetime.date,
    half: str,
    existing: list[ExistingLeave],
) -> bool:
    """BR-EL-012: block impermissible overlap.
    Exception: first-half and second-half CL on the same date are non-overlapping.
    """
    for ex in existing:
        # Dates don't intersect at all -> no overlap
        if end < ex.start or start > ex.end:
            continue
        # Same single day -- check half-day exception
        if (start == end == ex.start == ex.end
                and half != DayHalf.FULL and ex.half != DayHalf.FULL
                and half != ex.half):
            continue  # different halves on same date = OK
        return True  # overlap found
    return False


# -- Substitute validation (BR-EL-014) ----------------------------------------

def validate_substitute(
    applicant_id: int,
    substitute_id: int,
    leave_start: datetime.date,
    leave_end: datetime.date,
    substitute_leaves: list[ExistingLeave],
) -> ValidationResult:
    """BR-EL-014: substitute eligibility checks."""
    if substitute_id == applicant_id:
        return ValidationResult(False, "Substitute must not be the applicant")

    if has_overlap(leave_start, leave_end, DayHalf.FULL, substitute_leaves):
        return ValidationResult(
            False,
            "Substitute has overlapping leave during the responsibility period")

    return ValidationResult(True, "Substitute is eligible")


# -- Category eligibility (BR-EL-001, BR-EL-005, BR-EL-006) ------------------

def check_category_eligibility(
    category: str,
    is_faculty: bool,
) -> ValidationResult:
    """BR-EL-001: validate that the employee is eligible for the category."""
    if category not in VALID_CATEGORIES:
        return ValidationResult(False, f"Unknown leave category: {category}")
    if category == LeaveCategory.EL and is_faculty:
        return ValidationResult(False, "Faculty are not eligible for EL")
    if category == LeaveCategory.VL and not is_faculty:
        return ValidationResult(False, "Non-faculty are not eligible for VL")
    return ValidationResult(True, f"Eligible for {category}")


# -- Main validation (combines all rules) -------------------------------------

def validate_leave_request(
    category: str,
    start: datetime.date,
    end: datetime.date,
    is_faculty: bool,
    balance: float,
    existing_leaves: list[ExistingLeave],
    holidays: list[datetime.date],
    half: str = DayHalf.FULL,
) -> ValidationResult:
    """Full pre-submission validation combining BR-EL-001 through BR-EL-012.

    Returns ``(True, reason, days_counted)`` on success or
    ``(False, reason, 0)`` on failure.
    """
    if end < start:
        return ValidationResult(False, "End date is before start date")

    # BR-EL-001: category eligibility
    elig = check_category_eligibility(category, is_faculty)
    if not elig.allowed:
        return elig

    # BR-EL-010, BR-EL-011: count leave days
    days = count_leave_days(start, end, category, holidays, half)

    # Balance check
    if days > balance:
        return ValidationResult(
            False,
            f"Insufficient {category} balance: need {days}, have {balance}")

    # BR-EL-012: overlap check
    if has_overlap(start, end, half, existing_leaves):
        return ValidationResult(
            False,
            "Request overlaps with existing pending or approved leave")

    return ValidationResult(
        True,
        f"{category} for {days} day(s) is allowed",
        days)


# -- Station leave helper (BR-EL-013) ----------------------------------------

def requires_station_leave_info(category: str) -> bool:
    """BR-EL-013: station-leave details are captured within the application."""
    return category in {LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL}


# -- Authority routing helpers ------------------------------------------------

def requires_higher_sanction(category: str) -> bool:
    """BR-EL-016/017: CL and RH are Unit Head final; others need higher."""
    return category in HIGHER_SANCTION_CATEGORIES


def is_extendable(category: str) -> bool:
    """BR-EL-025: only EL, COL, VL may be extended while ongoing."""
    return category in EXTENDABLE_CATEGORIES


def is_resumable(category: str) -> bool:
    """BR-EL-027: formal resumption review applies to EL, COL, VL."""
    return category in RESUMABLE_CATEGORIES


class ApplicationValidation(NamedTuple):
    is_valid: bool
    days_counted: float = 0.0
    errors: list[str] = []


def validate_application(
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    half: str = DayHalf.FULL,
    is_faculty: bool = False,
    substitute_id: int | None = None,
    station_leave_required: bool = False,
    station_leave_address: str = "",
    holidays: list[datetime.date] | None = None,
) -> ApplicationValidation:
    """Validate core application parameters."""
    errors: list[str] = []
    if end_date < start_date:
        errors.append("End date cannot precede start date.")
        return ApplicationValidation(False, 0.0, errors)

    elig = check_category_eligibility(category, is_faculty)
    if not elig.allowed:
        errors.append(elig.reason)

    if station_leave_required and not station_leave_address.strip():
        errors.append("Station leave address is required when station leave is requested.")

    days = count_leave_days(start_date, end_date, category, holidays, half)
    if errors:
        return ApplicationValidation(False, days, errors)

    return ApplicationValidation(True, days, [])

