"""Pure leave-policy rules shared by services, API, and scheduled jobs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

SUPPORTED_LEAVE_TYPES = frozenset({"CL", "RH", "SCL", "EL", "COL", "VL"})
HALF_DAY_PARTS = frozenset({"FIRST_HALF", "SECOND_HALF"})
PENDING_STATUSES = frozenset({
    "SUBMITTED",
    "PENDING_SUBSTITUTE",
    "PENDING_UNIT_HEAD",
    "PENDING_ESTABLISHMENT",
    "PENDING_SANCTION",
})


class LeavePolicyError(ValueError):
    """A requested leave operation violates a configured or stated policy."""


@dataclass(frozen=True)
class LeaveInterval:
    leave_type_code: str
    start_date: date
    end_date: date
    day_part: str = "FULL"
    status: str = "SUBMITTED"


def is_category_eligible(leave_type_code: str, employee_kind: str) -> bool:
    """Apply only the category restriction stated by the baseline."""
    if leave_type_code not in SUPPORTED_LEAVE_TYPES:
        return False
    return leave_type_code != "VL" or employee_kind.lower() == "faculty"


def calculate_chargeable_days(
    leave_type_code: str,
    start_date: date,
    end_date: date,
    day_part: str = "FULL",
    configured_days: Decimal | str | int | None = None,
) -> Decimal:
    """Calculate days where the specification defines the counting rule.

    EL/COL/VL count every inclusive calendar date. For CL/SCL/RH, the caller
    supplies the result produced by the applicable configured calendar rule.
    """
    if leave_type_code not in SUPPORTED_LEAVE_TYPES:
        raise LeavePolicyError(f"Unsupported leave type: {leave_type_code}")
    if start_date > end_date:
        raise LeavePolicyError("The end date must be on or after the start date.")
    if day_part not in {"FULL", *HALF_DAY_PARTS}:
        raise LeavePolicyError(f"Unsupported day part: {day_part}")
    if day_part != "FULL" and leave_type_code != "CL":
        raise LeavePolicyError("Half-day requests are supported for CL only.")
    if day_part != "FULL" and start_date != end_date:
        raise LeavePolicyError("A half-day request must be for one date.")

    if day_part in HALF_DAY_PARTS:
        return Decimal("0.5")
    if leave_type_code in {"EL", "COL", "VL"}:
        return Decimal((end_date - start_date).days + 1)
    if configured_days is None:
        raise LeavePolicyError(
            f"Configured calendar day count is required for {leave_type_code}."
        )

    days = Decimal(str(configured_days))
    if days <= 0:
        raise LeavePolicyError("Chargeable leave days must be greater than zero.")
    return days


def intervals_overlap(new: LeaveInterval, existing: LeaveInterval) -> bool:
    """Return whether an active pending or approved interval overlaps."""
    if existing.status not in PENDING_STATUSES | {"APPROVED"}:
        return False
    if new.start_date > new.end_date or existing.start_date > existing.end_date:
        raise LeavePolicyError("Leave intervals must have valid date ranges.")

    same_single_date = (
        new.start_date == new.end_date == existing.start_date == existing.end_date
    )
    different_cl_halves = (
        same_single_date
        and new.leave_type_code == existing.leave_type_code == "CL"
        and new.day_part in HALF_DAY_PARTS
        and existing.day_part in HALF_DAY_PARTS
        and new.day_part != existing.day_part
    )
    if different_cl_halves:
        return False

    return new.start_date <= existing.end_date and existing.start_date <= new.end_date


def require_sufficient_balance(
    available: Decimal | str | int, requested: Decimal | str | int
) -> None:
    available_days = Decimal(str(available))
    requested_days = Decimal(str(requested))
    if requested_days <= 0:
        raise LeavePolicyError("Requested leave days must be greater than zero.")
    if available_days < requested_days:
        raise LeavePolicyError("Insufficient leave balance.")


def convert_vl_to_el(unused_vl: Decimal | str | int) -> Decimal:
    """Convert VL to EL at the exact 2:1 ratio, preserving fractions."""
    vl_days = Decimal(str(unused_vl))
    if vl_days < 0:
        raise LeavePolicyError("Unused VL cannot be negative.")
    return vl_days / Decimal("2")
