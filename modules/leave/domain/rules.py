from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal

# --- Constants and Exceptions ---

class RuleViolation(ValueError):
    """Raised when a leave rule is violated."""

CATEGORIES = ("CL", "RH", "SCL", "EL", "COL", "VL")

# --- Helper Functions ---

def _require_category(code: str):
    """Ensures the provided category code is valid."""
    if code not in CATEGORIES:
        raise RuleViolation(f"Unknown leave category: {code}")

# --- Core Logic Functions ---

def get_annual_entitlement(category_code: str, is_faculty: bool = False) -> Decimal:
    """BR-EL-001: Returns the base annual entitlement for a given leave category."""
    _require_category(category_code)

    if category_code == "CL":
        return Decimal("8.0")
    if category_code == "RH":
        return Decimal("2.0")
    if category_code == "SCL":
        return Decimal("15.0")
    if category_code == "COL":
        return Decimal("20.0")
    if category_code == "EL":
        return Decimal("0.0") if is_faculty else Decimal("30.0")
    if category_code == "VL":
        return Decimal("0.0") if not is_faculty else Decimal("60.0")

    # Should be unreachable due to _require_category
    return Decimal("0.0")

def calculate_leave_days(
    category_code: str,
    start_date: date,
    end_date: date,
    half_day: str | None = None,
    holidays: frozenset[date] = frozenset()
) -> Decimal:
    """BR-EL-011/BR-EL-012: Calculates the number of leave days between two dates."""
    _require_category(category_code)

    if end_date < start_date:
        raise RuleViolation("End date cannot be before start date.")

    if half_day is not None and half_day not in ("first", "second"):
        raise RuleViolation("Invalid half_day value.")

    if half_day is not None:
        # Rule 3: Half day constraints
        if category_code != "CL" or start_date != end_date:
            raise RuleViolation("Half day is only allowed for single-day CL requests.")

        # Check if the date is chargeable (weekday and not holiday)
        if start_date.weekday() >= 5 or start_date in holidays:
            raise RuleViolation("Half day request must be on a chargeable day.")

        return Decimal("0.5")

    # Full day calculation
    total_days = 0

    if category_code in ("EL", "COL", "VL"):
        # Rule 4: EL, COL, VL count all calendar days
        total_days = (end_date - start_date).days + 1
    else:
        # Rule 5: CL, SCL, RH count only weekdays and non-holidays
        current_date = start_date
        while current_date <= end_date:
            # Check if it's a weekday (Monday=0, Sunday=6)
            is_weekday = current_date.weekday() < 5
            is_holiday = current_date in holidays

            if is_weekday and not is_holiday:
                total_days += 1
            current_date = current_date + timedelta(days=1)

    if total_days == 0:
        raise RuleViolation("no chargeable days")

    return Decimal(total_days)

def check_overlap(
    existing: Iterable[tuple[date, date, str | None]],
    new_start: date,
    new_end: date,
    new_half: str | None = None
) -> bool:
    """BR-EL-012: Checks if the new leave period overlaps with any existing leave."""

    for existing_start, existing_end, existing_half in existing:
        # Standard overlap check
        if new_start <= existing_end and new_end >= existing_start:

            # Check for the specific half-day non-overlap exception
            is_same_single_day = (
                new_start == new_end and
                existing_start == existing_end and
                new_start == existing_start
            )

            if (
                is_same_single_day
                and new_half is not None
                and existing_half is not None
                and new_half != existing_half
            ):
                continue  # Skip this existing leave, no overlap

            # If we reach here, there is an overlap (or it's a single day with same half)
            return True

    return False

def convert_vl_to_el(vl_days: Decimal) -> Decimal:
    """BR-EL-007: Converts Vacation Leave (VL) to Earned Leave (EL)."""
    if vl_days < Decimal("0"):
        raise RuleViolation("VL days cannot be negative.")
    return vl_days / Decimal("2")

def has_sufficient_balance(balance: Decimal, requested_days: Decimal) -> bool:
    """Checks if the balance is sufficient for the requested days."""
    if balance < Decimal("0") or requested_days < Decimal("0"):
        raise RuleViolation("Balance and requested days must be non-negative.")
    return balance >= requested_days

def carry_forward_amount(category_code: str, balance: Decimal) -> Decimal:
    """Carries forward leave amounts based on category rules."""
    _require_category(category_code)

    # CL, RH, SCL, VL lapse (carry forward 0)
    if category_code in ("CL", "RH", "SCL", "VL"):
        return Decimal("0")

    # EL and COL carry forward
    return balance
