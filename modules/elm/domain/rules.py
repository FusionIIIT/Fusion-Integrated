"""Pure-Python business rules and calculations for ELM.

Strictly NO Django imports in this module.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, Sequence

from .entities import CountingMethod, LeaveCategory, LeaveStatus
from .errors import (
    InsufficientLeaveBalance,
    InvalidLeaveDatesError,
    InvalidSubstituteError,
    OverlappingLeaveError,
    PolicyValidationError,
)

DEFAULT_ENTITLEMENTS = {
    LeaveCategory.CL: Decimal("8.0"),
    LeaveCategory.RH: Decimal("2.0"),
    LeaveCategory.SCL: Decimal("15.0"),
    LeaveCategory.EL: Decimal("30.0"),  # non-faculty default
    LeaveCategory.COL: Decimal("20.0"),
    LeaveCategory.VL: Decimal("60.0"),  # faculty default
}


def calculate_duration_days(
    start_date: date,
    end_date: date,
    category: str,
    is_half_day: bool = False,
    holiday_calendar_dates: set[date] | None = None,
) -> Decimal:
    """Calculate the leave days consumed per BR-EL-010 and BR-EL-011.

    - Half-day CL: exactly 0.5 days (BR-EL-010).
    - Continuous (EL, COL, VL): every calendar day between start and end inclusive counts (BR-EL-011).
    - Non-continuous (CL, SCL, RH): working days only. Saturdays (day 5), Sundays (day 6),
      and published closed holidays inside the interval are excluded (BR-EL-011).
    """
    if start_date > end_date:
        raise InvalidLeaveDatesError(f"Start date {start_date} is after end date {end_date}.")

    if is_half_day:
        if category != LeaveCategory.CL:
            raise PolicyValidationError("Half-day leave is only permitted for Casual Leave (CL).")
        if start_date != end_date:
            raise InvalidLeaveDatesError("Half-day leave must be on a single date.")
        return Decimal("0.5")

    holiday_dates = holiday_calendar_dates or set()

    # Continuous counting for EL, COL, VL
    if category in (LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL):
        days_count = (end_date - start_date).days + 1
        return Decimal(days_count)

    # Non-continuous (working days only) for CL, SCL, RH
    working_days = 0
    cur = start_date
    one_day = timedelta(days=1)
    while cur <= end_date:
        # 5 = Saturday, 6 = Sunday
        if cur.weekday() < 5 and cur not in holiday_dates:
            working_days += 1
        cur += one_day

    return Decimal(working_days)


def validate_balance_available(current_balance: Decimal, required_days: Decimal) -> None:
    """Validate sufficient leave balance is available (BR-EL-002–009)."""
    if current_balance < required_days:
        raise InsufficientLeaveBalance(
            f"Insufficient leave balance: available {current_balance}d, required {required_days}d."
        )


def validate_no_overlap(
    start_date: date,
    end_date: date,
    is_half_day: bool,
    half_day: str,
    existing_leaves: Sequence[dict],
) -> None:
    """Validate no overlapping active or pending leave (BR-EL-012).

    Exception: morning and afternoon CL on the same date are non-overlapping.
    """
    terminal_statuses = {LeaveStatus.REJECTED, LeaveStatus.WITHDRAWN, LeaveStatus.CANCELLED}

    for item in existing_leaves:
        if item.get("status") in terminal_statuses:
            continue

        ex_start: date = item["leave_start"]
        ex_end: date = item["leave_end"]
        ex_is_half_day: bool = item.get("is_half_day", False)
        ex_half_day: str = item.get("half_day", "")

        # Check interval intersection
        if not (end_date < ex_start or start_date > ex_end):
            # Same single day and both half-days
            if (
                is_half_day
                and ex_is_half_day
                and start_date == end_date == ex_start == ex_end
            ):
                if half_day and ex_half_day and half_day != ex_half_day:
                    # One morning, one afternoon: permissible exception
                    continue

            raise OverlappingLeaveError(
                f"Requested interval {start_date} to {end_date} overlaps with existing leave #{item.get('id')} ({ex_start} to {ex_end})."
            )


def validate_substitute(
    applicant_id: int,
    substitute_id: int | None,
    start_date: date,
    end_date: date,
    substitute_leaves: Sequence[dict] | None = None,
) -> None:
    """Validate substitute eligibility per BR-EL-014.

    - Must be another employee (not applicant).
    - Must not have overlapping active leave during responsibility period.
    """
    if substitute_id is None:
        return

    if substitute_id == applicant_id:
        raise InvalidSubstituteError("Applicant cannot nominate themselves as substitute.")

    if substitute_leaves:
        terminal_statuses = {LeaveStatus.REJECTED, LeaveStatus.WITHDRAWN, LeaveStatus.CANCELLED}
        for item in substitute_leaves:
            if item.get("status") in terminal_statuses:
                continue
            ex_start: date = item["leave_start"]
            ex_end: date = item["leave_end"]
            if not (end_date < ex_start or start_date > ex_end):
                raise InvalidSubstituteError(
                    f"Nominated substitute #{substitute_id} has overlapping leave from {ex_start} to {ex_end}."
                )


def convert_vl_to_el(unused_vl: Decimal) -> Decimal:
    """Convert unused faculty VL to EL at 2 VL : 1 EL ratio (BR-EL-007).

    Supports fractional conversion (e.g. 5 VL -> 2.5 EL).
    """
    if unused_vl <= 0:
        return Decimal("0.0")
    return (unused_vl / Decimal("2.0")).quantize(Decimal("0.01"))


def resolve_approval_chain(
    category: str,
    applicant_role: str,
    applicant_id: int,
    unit_head_id: int,
    higher_authorities: Sequence[tuple[str, int]] | None = None,
) -> list[dict]:
    """Resolve approval steps per BR-EL-016, 017, 018, 019, 020.

    - Director applicant: Director self-sanction (BR-EL-020).
    - CL / RH: Unit Head final approve/reject (BR-EL-016).
    - SCL, EL, COL, VL: Unit Head recommendation (BR-EL-017) -> higher authority final decision (BR-EL-018/019).
    """
    steps = []

    # Director self-sanction
    if applicant_role == "director":
        steps.append({
            "step_order": 1,
            "assigned_user_id": applicant_id,
            "assigned_role": "director",
            "step_type": "final_decision",
        })
        return steps

    # CL and RH: Unit Head has final authority
    if category in (LeaveCategory.CL, LeaveCategory.RH):
        steps.append({
            "step_order": 1,
            "assigned_user_id": unit_head_id,
            "assigned_role": "unit_head",
            "step_type": "final_decision",
        })
        return steps

    # Higher-sanction categories: SCL, EL, COL, VL
    # Step 1: Unit Head recommendation
    steps.append({
        "step_order": 1,
        "assigned_user_id": unit_head_id,
        "assigned_role": "unit_head",
        "step_type": "recommendation",
    })

    # Steps 2+: Configured higher authorities (e.g. DR Estt, Dean/Registrar, Director)
    authorities = list(higher_authorities or [("director", 1)])
    for idx, (role, user_id) in enumerate(authorities, start=2):
        is_last = idx == (len(authorities) + 1)
        step_type = "final_decision" if is_last else "recommendation"
        steps.append({
            "step_order": idx,
            "assigned_user_id": user_id,
            "assigned_role": role,
            "step_type": step_type,
        })

    return steps
