"""Business rules for Employee Leave Management."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from decimal import Decimal

from .errors import (
    IneligibleCategoryError,
    IneligibleSubstituteError,
    InsufficientBalanceError,
    LeavePolicyViolationError,
    OverlappingLeaveError,
)

SUPPORTED_CATEGORIES = frozenset({"CL", "RH", "SCL", "EL", "COL", "VL"})
FACULTY_ONLY_CATEGORIES = frozenset({"VL"})
NON_FACULTY_DIRECT_CATEGORIES = frozenset({"EL"})


def validate_category_eligibility(category: str, is_faculty: bool) -> None:
    """Enforces category applicability under BR-EL-001, BR-EL-005, and BR-EL-006."""
    if category not in SUPPORTED_CATEGORIES:
        raise IneligibleCategoryError(f"Category '{category}' is not supported.")
    if category == "VL" and not is_faculty:
        raise IneligibleCategoryError("Vacation Leave (VL) is admissible only for faculty.")


def validate_balance(available: Decimal, requested: Decimal) -> None:
    """Enforces balance availability constraint."""
    if requested > available:
        raise InsufficientBalanceError(
            f"Requested {requested} days exceeds available balance {available}."
        )


def validate_restricted_holiday(
    starts_on: datetime.date,
    ends_on: datetime.date,
    available_rh_dates: Sequence[datetime.date],
) -> None:
    """Enforces RH matching against the published RH calendar under BR-EL-003."""
    if starts_on != ends_on:
        raise LeavePolicyViolationError("Restricted Holiday can only be availed for a single day.")
    if starts_on not in available_rh_dates:
        raise LeavePolicyViolationError(
            f"{starts_on} is not a gazetted Restricted Holiday in the published calendar."
        )


def validate_vacation_period(
    starts_on: datetime.date,
    ends_on: datetime.date,
    vacation_ranges: Sequence[tuple[datetime.date, datetime.date]],
) -> None:
    """Enforces VL applicability to academic vacation periods under BR-EL-006."""
    in_range = any(
        vac_start <= starts_on and ends_on <= vac_end for vac_start, vac_end in vacation_ranges
    )
    if not in_range:
        raise LeavePolicyViolationError(
            "Vacation Leave may be availed only during an applicable academic vacation period."
        )


def validate_substitute(applicant_id: int, substitute_id: int | None) -> None:
    """Enforces substitute nomination eligibility under BR-EL-014."""
    if substitute_id is not None and substitute_id == applicant_id:
        raise IneligibleSubstituteError("An employee cannot nominate themselves as substitute.")


def validate_overlap(
    starts_on: datetime.date,
    ends_on: datetime.date,
    half: str,
    existing_leaves: Sequence[tuple[datetime.date, datetime.date, str]],
) -> None:
    """Validates non-overlap with the BR-EL-012 half-day CL exception."""
    for ex_start, ex_end, ex_half in existing_leaves:
        if ex_start <= ends_on and starts_on <= ex_end:
            # Check for the same date half-day CL non-overlap exception
            if (
                starts_on == ends_on == ex_start == ex_end
                and half in ("first_half", "second_half")
                and ex_half in ("first_half", "second_half")
                and half != ex_half
            ):
                continue
            raise OverlappingLeaveError(
                "Requested leave period overlaps with existing active leave."
            )


def validate_cancellation_before_start(starts_on: datetime.date, today: datetime.date) -> None:
    """Enforces pre-start cancellation boundary under BR-EL-023."""
    if today >= starts_on:
        raise LeavePolicyViolationError(
            "Approved leave cannot be cancelled once the leave start date is reached."
        )


def validate_extension_admissibility(
    category: str, starts_on: datetime.date, today: datetime.date
) -> None:
    """Enforces ongoing EL/COL/VL extension constraint under BR-EL-025."""
    if category not in ("EL", "COL", "VL"):
        raise LeavePolicyViolationError(
            f"Extension is admissible only for EL, COL, or VL; not {category}."
        )
    if today < starts_on:
        raise LeavePolicyViolationError(
            "Cannot request extension before the leave period has commenced."
        )


def convert_vl_to_el(vl_balance: Decimal, ratio: Decimal = Decimal("2.0")) -> Decimal:
    """Converts unused faculty VL to EL at ratio (default 2:1) under BR-EL-007."""
    if vl_balance <= Decimal("0"):
        return Decimal("0")
    return vl_balance / ratio
