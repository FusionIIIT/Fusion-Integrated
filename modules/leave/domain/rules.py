"""Pure-python leave business rules and calculation logic."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, Sequence

from .constants import (
    HALF_DAY_FIRST,
    HALF_DAY_FULL,
    HALF_DAY_SECOND,
    LEAVE_CL,
    LEAVE_COL,
    LEAVE_EL,
    LEAVE_RH,
    LEAVE_SCL,
    LEAVE_VL,
    STATUS_APPROVED,
    STATUS_AWAITING_DIRECTOR_SELF_SANCTION,
    STATUS_AWAITING_ESTABLISHMENT,
    STATUS_AWAITING_FINAL_SANCTION,
    STATUS_AWAITING_SUBSTITUTE,
    STATUS_AWAITING_UNIT_HEAD,
    STATUS_DRAFT,
    TERMINAL_STATUSES,
)


class LeaveValidationError(Exception):
    """Raised when a leave business rule constraint is violated."""


def calculate_leave_days(
    category: str,
    start_date: date,
    end_date: date,
    half_day: str = HALF_DAY_FULL,
    closed_holidays: set[date] | None = None,
    restricted_holidays: set[date] | None = None,
    vacation_dates: set[date] | None = None,
) -> Decimal:
    """Calculate chargeable leave days according to BR-EL-010, BR-EL-011, BR-EL-003, BR-EL-006."""
    if start_date > end_date:
        raise LeaveValidationError("Start date cannot be after end date.")

    closed = closed_holidays or set()
    restricted = restricted_holidays or set()
    vacation = vacation_dates or set()

    # BR-EL-010: Half-day CL
    if half_day in (HALF_DAY_FIRST, HALF_DAY_SECOND):
        if category != LEAVE_CL:
            raise LeaveValidationError("Half-day leave is only permitted for Casual Leave (CL).")
        if start_date != end_date:
            raise LeaveValidationError("Half-day CL must have start and end date on the same day.")
        return Decimal("0.5")

    # BR-EL-003: RH validation against calendar
    if category == LEAVE_RH:
        cur = start_date
        while cur <= end_date:
            if cur not in restricted:
                raise LeaveValidationError(f"Date {cur} is not in the published Restricted Holiday calendar.")
            cur += timedelta(days=1)

    # BR-EL-006: VL availed only in published vacation period
    if category == LEAVE_VL:
        cur = start_date
        while cur <= end_date:
            if cur not in vacation:
                raise LeaveValidationError(f"Date {cur} is not within a published vacation period.")
            cur += timedelta(days=1)

    # BR-EL-011: Continuing leave counting
    # For EL, COL, and VL: intervening weekends and closed holidays inside the continuous interval count as leave days.
    # For CL, RH, and SCL: weekends and closed holidays do NOT count.
    is_continuous_counting = category in (LEAVE_EL, LEAVE_COL, LEAVE_VL)

    total_days = Decimal("0.0")
    cur = start_date
    while cur <= end_date:
        is_weekend = cur.weekday() in (5, 6)  # Saturday, Sunday
        is_closed = cur in closed
        if is_continuous_counting:
            total_days += Decimal("1.0")
        else:
            if not is_weekend and not is_closed:
                total_days += Decimal("1.0")
        cur += timedelta(days=1)

    if total_days == Decimal("0.0"):
        raise LeaveValidationError("The selected period contains no chargeable working days.")

    return total_days


def check_non_overlap(
    existing_leaves: Sequence[dict],
    new_start: date,
    new_end: date,
    new_half_day: str = HALF_DAY_FULL,
    exclude_request_id: int | None = None,
) -> None:
    """Validate that new leave does not impermissibly overlap (BR-EL-012, BR-EL-034)."""
    for leave in existing_leaves:
        if exclude_request_id is not None and leave.get("id") == exclude_request_id:
            continue
        if leave.get("status") in TERMINAL_STATUSES:
            continue

        l_start = leave["start_date"]
        l_end = leave["end_date"]
        l_half = leave.get("half_day", HALF_DAY_FULL)

        # Check date intersection
        if not (new_end < l_start or new_start > l_end):
            # Intersection exists
            if new_start == new_end and l_start == l_end and new_start == l_start:
                # BR-EL-034: Different halves on same date are permitted
                if (new_half_day == HALF_DAY_FIRST and l_half == HALF_DAY_SECOND) or (
                    new_half_day == HALF_DAY_SECOND and l_half == HALF_DAY_FIRST
                ):
                    continue
            raise LeaveValidationError(
                f"Requested leave from {new_start} to {new_end} overlaps with active leave "
                f"from {l_start} to {l_end}."
            )


def can_modify_pending(status: str) -> bool:
    """BR-EL-021: Pending requests can be modified only before final approval."""
    return status in (
        STATUS_DRAFT,
        STATUS_AWAITING_SUBSTITUTE,
        STATUS_AWAITING_UNIT_HEAD,
        STATUS_AWAITING_ESTABLISHMENT,
        STATUS_AWAITING_FINAL_SANCTION,
        STATUS_AWAITING_DIRECTOR_SELF_SANCTION,
    )


def can_withdraw_pending(status: str) -> bool:
    """BR-EL-022: Can withdraw at any time before final approval."""
    return status not in (STATUS_APPROVED, *TERMINAL_STATUSES)


def can_cancel_approved(status: str, start_date: date, today: date) -> bool:
    """BR-EL-023: Approved leave can only be cancelled before it starts."""
    return status == STATUS_APPROVED and today < start_date


def can_extend(category: str, status: str) -> bool:
    """BR-EL-025, SRS-EL-071: Only ongoing approved EL, COL, and VL may be extended."""
    return status == STATUS_APPROVED and category in (LEAVE_EL, LEAVE_COL, LEAVE_VL)


def can_resume(category: str, status: str) -> bool:
    """BR-EL-027: Resumption is required for EL, COL, and VL after approval."""
    return status == STATUS_APPROVED and category in (LEAVE_EL, LEAVE_COL, LEAVE_VL)


def convert_vl_to_el(unused_vl: Decimal) -> Decimal:
    """BR-EL-007: 2 VL to 1 EL conversion at year end with fractional support."""
    if unused_vl <= Decimal("0.0"):
        return Decimal("0.0")
    return unused_vl / Decimal("2.0")


def calculate_early_resumption_restoration(
    category: str,
    approved_start: date,
    approved_end: date,
    actual_resumption_date: date,
    closed_holidays: set[date] | None = None,
) -> Decimal:
    """BR-EL-028: Calculate unused leave to restore when employee resumes duty early."""
    if actual_resumption_date > approved_end:
        return Decimal("0.0")
    if actual_resumption_date <= approved_start:
        restore_start = approved_start
    else:
        restore_start = actual_resumption_date

    # Restore from actual_resumption_date through approved_end
    return calculate_leave_days(
        category=category,
        start_date=restore_start,
        end_date=approved_end,
        half_day=HALF_DAY_FULL,
        closed_holidays=closed_holidays,
    )
