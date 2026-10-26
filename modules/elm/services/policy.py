"""Deterministic leave-policy calculations for Employee Leave Management.

Calendar and account data are external inputs: this module never guesses the
effective holiday calendar, Academic Calendar, or an employee's live balance.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

SUPPORTED_LEAVE_TYPES = frozenset({"CL", "RH", "SCL", "EL", "COL", "VL"})
ANNUAL_ENTITLEMENTS = {
    "CL": Decimal("8"),
    "RH": Decimal("2"),
    "SCL": Decimal("15"),
    "EL": Decimal("30"),  # non-faculty only
    "COL": Decimal("20"),
    "VL": Decimal("60"),  # faculty only; also limited by Academic Calendar
}
CONTINUOUS_COUNT_TYPES = frozenset({"EL", "COL", "VL"})
NO_CARRY_FORWARD_TYPES = frozenset({"CL", "RH", "SCL"})


class PolicyValidationError(ValueError):
    """A leave request violates a deterministic ELM policy constraint."""


@dataclass(frozen=True)
class LeaveInterval:
    start_date: date
    end_date: date
    leave_type: str
    status: str
    start_half: str = ""
    end_half: str = ""

    def __post_init__(self):
        if self.end_date < self.start_date:
            raise PolicyValidationError("End date cannot precede start date.")


def count_leave_days(
    leave_type: str,
    start_date: date,
    end_date: date,
    *,
    start_half: str = "",
    end_half: str = "",
    excluded_dates: Iterable[date] = (),
) -> Decimal:
    """Count continuous EL/COL/VL days; exclude weekends/holidays for CL/SCL/RH."""
    kind = leave_type.upper().strip()
    if kind not in SUPPORTED_LEAVE_TYPES:
        raise PolicyValidationError(f"Unsupported leave category: {leave_type!r}.")
    if end_date < start_date:
        raise PolicyValidationError("End date cannot precede start date.")
    if kind == "CL" and start_date == end_date and (start_half or end_half):
        if start_half not in {"first", "second", ""} or end_half not in {"first", "second", ""}:
            raise PolicyValidationError("CL half must be 'first' or 'second'.")
        if start_half and end_half and start_half != end_half:
            raise PolicyValidationError("A single-date half-day CL request must select one half.")
        return Decimal("0.5")
    if start_half or end_half:
        raise PolicyValidationError("Half-day selection is supported only for single-date CL.")
    days = (end_date - start_date).days + 1
    if kind in CONTINUOUS_COUNT_TYPES:
        return Decimal(days)
    excluded = set(excluded_dates)
    return Decimal(sum(
        1 for offset in range(days)
        if (current := start_date + timedelta(days=offset)).weekday() < 5
        and current not in excluded
    ))


def intervals_overlap(left: LeaveInterval, right: LeaveInterval) -> bool:
    """Opposite half-day CL requests on the same date do not overlap."""
    if left.end_date < right.start_date or right.end_date < left.start_date:
        return False
    if (
        left.leave_type == right.leave_type == "CL"
        and left.start_date == left.end_date == right.start_date == right.end_date
        and left.start_half in {"first", "second"}
        and right.start_half in {"first", "second"}
        and left.start_half != right.start_half
    ):
        return False
    return True


def year_end_outcome(leave_type: str, unused_balance: Decimal) -> dict:
    """Return the baseline year-end treatment; caller persists resulting ledger entries."""
    kind = leave_type.upper().strip()
    balance = Decimal(unused_balance)
    if balance < 0:
        raise PolicyValidationError("Unused leave balance cannot be negative.")
    if kind in NO_CARRY_FORWARD_TYPES:
        return {"action": "lapse", "lapsed": balance, "credited_el": Decimal("0")}
    if kind == "VL":
        return {"action": "convert_to_el", "lapsed": balance, "credited_el": balance / Decimal("2")}
    if kind in {"EL", "COL"}:
        return {"action": "carry_forward", "lapsed": Decimal("0"), "credited_el": Decimal("0")}
    raise PolicyValidationError(f"Unsupported leave category: {leave_type!r}.")
