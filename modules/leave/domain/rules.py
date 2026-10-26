"""Business rules and validations adhering to ELM Specifications (v1.4)."""

from datetime import date
from decimal import Decimal

from .entities import HalfDayType, LeaveCategory, LeaveStatus
from .errors import (
    IneligibleSubstituteError,
    InsufficientBalanceError,
    InvalidDateRangeError,
    InvalidStateTransitionError,
    OverlappingLeaveError,
    RestrictedHolidayMismatchError,
    VacationCalendarMismatchError,
)


def validate_category_eligibility(user_kind: str, category: str) -> None:
    """Validate that the employee kind is eligible for the requested category.

    - Staff receives EL directly (30 days/year); Faculty receives VL (60 days/year)
      and converts unused VL to EL at year-end.
    - Both receive CL, RH, SCL, COL.
    """
    if user_kind == "faculty" and category == LeaveCategory.EL.value:
        # Faculty can only avail EL if they have a converted EL balance, which is allowed.
        pass
    if user_kind == "staff" and category == LeaveCategory.VL.value:
        raise InvalidStateTransitionError("Vacation Leave (VL) is only available for Faculty.")


def validate_rh_date(start_date: date, end_date: date, rh_dates: set[date]) -> None:
    """BR-EL-003: An RH request must be for a single day and match a published RH date."""
    if start_date != end_date:
        raise RestrictedHolidayMismatchError(
            "Restricted Holiday (RH) must be requested for a single day."
        )
    if start_date not in rh_dates:
        raise RestrictedHolidayMismatchError(
            f"Date {start_date} is not listed in the published Restricted Holiday calendar."
        )


def validate_positive_leave_days(days_count: Decimal) -> None:
    """BR-EL-011: Leave request duration must be strictly positive (at least 0.5 days)."""
    if days_count <= Decimal("0.0"):
        raise InvalidDateRangeError(
            "Requested leave period has 0 working days (weekends or closed holidays)."
        )


def validate_vacation_period(
    start_date: date,
    end_date: date,
    vacation_periods: list[tuple[date, date]],
) -> None:
    """BR-EL-006: VL may be availed only during an applicable academic vacation period."""
    in_vacation = False
    for v_start, v_end in vacation_periods:
        if v_start <= start_date and end_date <= v_end:
            in_vacation = True
            break
    if not in_vacation:
        raise VacationCalendarMismatchError(
            f"Requested VL period {start_date} to {end_date} does not fall "
            f"within a published vacation period."
        )


def validate_substitute_eligibility(
    applicant_user_id: int,
    substitute_user_id: int | None,
    substitute_active_leaves: list[tuple[date, date]],
    requested_start: date,
    requested_end: date,
) -> None:
    """BR-EL-014: Substitute must be another employee, not the applicant, and not on leave."""
    if substitute_user_id is None:
        return
    if substitute_user_id == applicant_user_id:
        raise IneligibleSubstituteError("Applicant cannot nominate themselves as substitute.")

    for l_start, l_end in substitute_active_leaves:
        if not (requested_end < l_start or requested_start > l_end):
            raise IneligibleSubstituteError(
                "Nominated substitute has active leave during the requested coverage period."
            )


def validate_no_overlap(
    existing_leaves: list[dict],
    new_start: date,
    new_end: date,
    new_category: str,
    new_half_day: str = HalfDayType.FULL.value,
) -> None:
    """BR-EL-012: A new request shall not impermissibly overlap active pending or approved leave.

    First-half and second-half CL on the same date are permitted.
    """
    for ex in existing_leaves:
        ex_start = ex["start_date"]
        ex_end = ex["end_date"]
        ex_cat = ex["leave_type"]
        ex_half = ex.get("half_day_type", HalfDayType.FULL.value)

        # Check date overlap
        if not (new_end < ex_start or new_start > ex_end):
            # Same day CL half-day exception
            if (
                new_start == new_end == ex_start == ex_end
                and new_category == LeaveCategory.CL.value
                and ex_cat == LeaveCategory.CL.value
                and new_half_day in (HalfDayType.FIRST_HALF.value, HalfDayType.SECOND_HALF.value)
                and ex_half in (HalfDayType.FIRST_HALF.value, HalfDayType.SECOND_HALF.value)
                and new_half_day != ex_half
            ):
                continue
            raise OverlappingLeaveError(
                f"Requested period overlaps with existing leave ({ex_cat}: {ex_start} to {ex_end})."
            )


def validate_balance_sufficient(
    requested_days: Decimal,
    available_balance: Decimal,
) -> None:
    """BR-EL-002: Ensure available balance is sufficient."""
    if requested_days > available_balance:
        raise InsufficientBalanceError(
            f"Requested {requested_days} days exceeds available balance "
            f"of {available_balance} days."
        )


def validate_cancellation_allowed(
    leave_status: str,
    start_date: date,
    today: date,
) -> None:
    """BR-EL-023: Cancellation only before the approved leave begins."""
    if leave_status != LeaveStatus.APPROVED.value:
        raise InvalidStateTransitionError("Only approved leave can be cancelled.")
    if today >= start_date:
        raise InvalidStateTransitionError(
            "Approved leave cannot be cancelled on or after its start date. "
            "Extension or Resumption applies."
        )


def validate_extension_allowed(
    leave_status: str,
    category: str,
    start_date: date,
    end_date: date,
    today: date,
) -> None:
    """BR-EL-025: Extension available only for ongoing EL, COL, or VL."""
    if leave_status != LeaveStatus.APPROVED.value:
        raise InvalidStateTransitionError("Only approved leave can be extended.")
    if category not in (LeaveCategory.EL.value, LeaveCategory.COL.value, LeaveCategory.VL.value):
        raise InvalidStateTransitionError(
            f"Extension is only permitted for EL, COL, or VL (not {category})."
        )
    if today < start_date or today > end_date:
        raise InvalidStateTransitionError("Extension can only be requested while leave is ongoing.")


def validate_resumption_allowed(
    approved_start: date,
    actual_resumption_date: date,
) -> None:
    """BR-EL-027: Resumption date must not precede the leave start date."""
    if actual_resumption_date < approved_start:
        raise InvalidStateTransitionError(
            "Actual resumption date cannot be earlier than leave start date."
        )


def calculate_resumption_adjustment(
    approved_start: date,
    approved_end: date,
    actual_resumption_date: date,
    category: str,
    closed_holiday_dates: set[date] | None = None,
) -> Decimal:
    """BR-EL-028 / BR-EL-029: Calculate balance adjustment for resumption.

    Returns:
    - 0 if resumed on approved_end date.
    - Negative Decimal (credit back) if resumed earlier than approved_end.
    - Positive Decimal (deduct further) if resumed later than approved_end.
    """
    if actual_resumption_date == approved_end:
        return Decimal("0.0")

    from .counting import calculate_leave_days

    approved_days = calculate_leave_days(
        category, approved_start, approved_end, closed_holiday_dates=closed_holiday_dates
    )
    actual_days = calculate_leave_days(
        category, approved_start, actual_resumption_date, closed_holiday_dates=closed_holiday_dates
    )

    # Difference: positive means more days used (deduct), negative means fewer used (refund)
    return actual_days - approved_days


def calculate_year_end_conversions(
    balances: dict[str, Decimal],
    is_faculty: bool,
) -> tuple[dict[str, Decimal], Decimal]:
    """BR-EL-003, BR-EL-004, BR-EL-007, BR-EL-008: Year-end processing outcomes.

    - CL, RH, SCL: unused balances lapse to 0.
    - VL (Faculty): converts to EL at 2 VL : 1 EL (including 0.5 fractions).
      Unused VL itself becomes 0.
    - EL, COL: carry forward.

    Returns (new_balances, vl_to_el_credit).
    """
    new_balances = dict(balances)

    # Lapse CL, RH, SCL
    new_balances[LeaveCategory.CL.value] = Decimal("0.0")
    new_balances[LeaveCategory.RH.value] = Decimal("0.0")
    new_balances[LeaveCategory.SCL.value] = Decimal("0.0")

    vl_converted_to_el = Decimal("0.0")
    if is_faculty and LeaveCategory.VL.value in balances:
        unused_vl = max(Decimal("0.0"), balances[LeaveCategory.VL.value])
        vl_converted_to_el = (unused_vl / Decimal("2")).quantize(Decimal("0.1"))
        new_balances[LeaveCategory.VL.value] = Decimal("0.0")
        current_el = new_balances.get(LeaveCategory.EL.value, Decimal("0.0"))
        new_balances[LeaveCategory.EL.value] = current_el + vl_converted_to_el

    return new_balances, vl_converted_to_el
