"""Domain validation rules for ELM.

Pure Python — no Django imports allowed in domain/.
Enforces:
- BR-EL-001: Supported leave-category eligibility
- BR-EL-003: Restricted Holiday entitlement and applicability
- BR-EL-006: Faculty Vacation Leave entitlement and vacation-period applicability
- BR-EL-012: Applicant non-overlap with half-day CL exception
- BR-EL-014: Substitute eligibility
"""
from __future__ import annotations

from collections.abc import Sequence, Set
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from modules.elm.domain.constants import HalfDaySession, LeaveCategory


@dataclass(frozen=True)
class ExistingLeaveInterval:
    start_date: date
    end_date: date
    is_half_day: bool
    half_day_session: str | None
    status: str
    category: str


def validate_category_eligibility(
    category: str | LeaveCategory,
    user_kind: str,
) -> None:
    """Validate that the leave category is valid and eligible for the user type.

    - BR-EL-001: Only CL, RH, SCL, EL, COL, VL supported.
    - BR-EL-006: VL is only eligible for faculty.
    """
    try:
        cat = LeaveCategory(category) if isinstance(category, str) else category
    except ValueError:
        raise ValueError(
            f"Invalid leave category '{category}'. Supported categories are: "
            f"{', '.join(c.value for c in LeaveCategory)}."
        ) from None

    if cat == LeaveCategory.VL and user_kind != "faculty":
        raise ValueError("Vacation Leave (VL) is only available for faculty members.")


def validate_balance_sufficient(
    available_balance: Decimal,
    requested_days: Decimal,
    category: str,
) -> None:
    """Validate that the employee has sufficient balance."""
    if requested_days <= Decimal("0"):
        raise ValueError("Requested leave duration must be greater than zero.")
    if requested_days > available_balance:
        raise ValueError(
            f"Insufficient leave balance for {category}. "
            f"Available: {available_balance}, Requested: {requested_days}."
        )


def validate_overlap(
    existing_leaves: Sequence[ExistingLeaveInterval],
    new_start: date,
    new_end: date,
    *,
    is_half_day: bool = False,
    half_day_session: str | HalfDaySession | None = None,
) -> None:
    """Check for impermissible overlap against active pending/approved leaves.

    BR-EL-012: First-half and second-half CL on the same date are non-overlapping
    when they occupy different halves. Any other overlap is prohibited.
    """
    for ex in existing_leaves:
        # Check date intersection: max(start1, start2) <= min(end1, end2)
        if max(ex.start_date, new_start) <= min(ex.end_date, new_end):
            # Check half-day CL exception:
            if (
                is_half_day
                and ex.is_half_day
                and new_start == new_end == ex.start_date == ex.end_date
            ):
                session_new = (
                    half_day_session.value
                    if isinstance(half_day_session, HalfDaySession)
                    else half_day_session
                )
                session_ex = ex.half_day_session
                if session_new and session_ex and session_new != session_ex:
                    # They occupy different halves on the same date -> permitted!
                    continue

            raise ValueError(
                f"Requested leave period ({new_start} to {new_end}) overlaps with an existing "
                f"{ex.category} leave from {ex.start_date} to {ex.end_date} (status: {ex.status})."
            )


def validate_substitute_eligibility(
    applicant_user_id: int,
    substitute_user_id: int,
    substitute_user_kind: str | None,
    substitute_leaves: Sequence[ExistingLeaveInterval],
    responsibility_start: date,
    responsibility_end: date,
) -> None:
    """Validate substitute eligibility per BR-EL-014.

    Constraints:
    1. Substitute must be another employee (not applicant).
    2. Substitute must have no overlapping pending or approved leave during
       the responsibility period.
    """
    if substitute_user_id == applicant_user_id:
        raise ValueError("The applicant cannot nominate themselves as a substitute.")

    if substitute_user_kind not in ("faculty", "staff"):
        raise ValueError("Substitute must be an active employee (faculty or staff).")

    for ex in substitute_leaves:
        if max(ex.start_date, responsibility_start) <= min(ex.end_date, responsibility_end):
            raise ValueError(
                f"The nominated substitute has an overlapping {ex.category} leave "
                f"from {ex.start_date} to {ex.end_date}."
            )


def validate_rh_date(
    requested_date: date,
    published_rh_dates: Set[date],
) -> None:
    """Validate that the requested date is a published Restricted Holiday.

    BR-EL-003 / BR-EL-031: RH request must correspond to an applicable RH in
    the currently effective published holiday/RH calendar.
    """
    if requested_date not in published_rh_dates:
        raise ValueError(
            f"The date {requested_date} is not listed as an applicable Restricted Holiday "
            f"in the published calendar."
        )


def validate_vacation_period(
    start_date: date,
    end_date: date,
    vacation_intervals: Sequence[tuple[date, date]],
) -> None:
    """Validate that VL falls entirely within an applicable vacation period.

    BR-EL-006: VL may be availed only during an applicable vacation period supplied
    through the institute Academic Calendar.
    """
    falls_within_period = False
    for v_start, v_end in vacation_intervals:
        if v_start <= start_date and end_date <= v_end:
            falls_within_period = True
            break

    if not falls_within_period:
        raise ValueError(
            f"Vacation Leave ({start_date} to {end_date}) must fall entirely within an "
            f"applicable academic vacation period."
        )
