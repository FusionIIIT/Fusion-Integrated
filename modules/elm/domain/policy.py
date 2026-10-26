"""Pure Python domain policy and calculation rules for Employee Leave Management (ELM).

Per the architecture contract, domain modules must never import Django, DRF, or Celery.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum


class LeaveCategory(StrEnum):
    CL = "CL"      # Casual Leave (8 days/year, lapses at year end)
    RH = "RH"      # Restricted Holiday (2 days/year, calendar restricted, lapses)
    SCL = "SCL"    # Special Casual Leave (15 days/year, lapses)
    EL = "EL"      # Earned Leave (30 days/year non-faculty, carried forward, max 300 cap)
    COL = "COL"    # Commuted Leave (20 days/year, medical evidence, carried forward)
    VL = "VL"      # Vacation Leave (60 days/year faculty, converts 2:1 to EL, no carry)


class ApplicationStatus(StrEnum):
    PENDING = "pending"
    AWAITING_SUBSTITUTE = "awaiting_substitute"
    APPLICANT_ACTION_REQUIRED = "applicant_action_required"
    AWAITING_UNIT_HEAD = "awaiting_unit_head"
    AWAITING_FINAL_SANCTION = "awaiting_final_sanction"
    AWAITING_DIRECTOR = "awaiting_director"
    RECOMMENDED = "recommended"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CANCELLATION_PENDING_UNIT_HEAD = "cancellation_pending_unit_head"
    CANCELLATION_PENDING_FINAL = "cancellation_pending_final"
    CANCELLED = "cancelled"


class RecommendationChoice(StrEnum):
    RECOMMENDED = "recommended"
    NOT_RECOMMENDED = "not_recommended"


class ResumptionOutcome(StrEnum):
    NORMAL = "reviewed_normal"
    EARLY = "reviewed_early"
    LATE = "reviewed_late"


# Standard maximum accumulation for Earned Leave under institute leave policy
MAX_EL_CARRY_FORWARD_CAP = Decimal("300.0")

# Annual entitlements
ANNUAL_QUOTAS: dict[str, Decimal] = {
    LeaveCategory.CL.value: Decimal("8.0"),
    LeaveCategory.RH.value: Decimal("2.0"),
    LeaveCategory.SCL.value: Decimal("15.0"),
    LeaveCategory.EL.value: Decimal("30.0"),    # non-faculty
    LeaveCategory.COL.value: Decimal("20.0"),
    LeaveCategory.VL.value: Decimal("60.0"),    # faculty
}


def calculate_leave_days(start_date: date, end_date: date, half_day: bool = False) -> Decimal:
    """Calculate the total leave days for a requested date range.

    Half-day leave applies only to a single day (BR-EL-010).
    """
    if end_date < start_date:
        raise ValueError("End date cannot be earlier than start date.")

    calendar_days = (end_date - start_date).days + 1
    if half_day:
        if calendar_days != 1:
            raise ValueError(
                "Half-day leave is permissible only for a single-day request (BR-EL-010)."
            )
        return Decimal("0.5")
    return Decimal(str(calendar_days))


def convert_vl_to_el(unused_vl: Decimal) -> Decimal:
    """Convert unused faculty Vacation Leave (VL) to Earned Leave (EL) at 2 VL : 1 EL.

    BR-EL-007: 'At year end, all unused faculty VL shall convert to EL at 2 VL : 1 EL
    including fractional conversion, and VL itself shall not carry forward.'

    Uses exact Decimal arithmetic so fractions (e.g. 15 VL -> 7.5 EL) are preserved
    without integer truncation.
    """
    if unused_vl < Decimal("0"):
        raise ValueError(f"Unused VL cannot be negative: {unused_vl}")
    return (unused_vl / Decimal("2.0")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def calculate_resumption_adjustment(
    approved_start: date,
    approved_end: date,
    actual_resumption_date: date,
) -> tuple[ResumptionOutcome, Decimal]:
    """Calculate duty resumption outcome and day adjustments (BR-EL-027, BR-EL-028).

    - Normal: actual_resumption_date == approved_end.
      No day adjustment (Decimal('0.0')).
    - Early: actual_resumption_date < approved_end.
      Employee returned early; days between actual and approved end are unused and
      should be refunded. Returns (ResumptionOutcome.EARLY, Decimal(unused_days)).
    - Late: actual_resumption_date > approved_end.
      Employee returned late; days beyond approved end are additional and must be
      deducted. Returns (ResumptionOutcome.LATE, Decimal(extra_days)).
    """
    if actual_resumption_date < approved_start:
        raise ValueError("Resumption date cannot be earlier than the approved leave start date.")

    if actual_resumption_date == approved_end:
        return ResumptionOutcome.NORMAL, Decimal("0.0")

    if actual_resumption_date < approved_end:
        unused_days = Decimal(str((approved_end - actual_resumption_date).days))
        return ResumptionOutcome.EARLY, unused_days

    extra_days = Decimal(str((actual_resumption_date - approved_end).days))
    return ResumptionOutcome.LATE, extra_days


def is_unit_head_final_authority(leave_type_code: str, is_director: bool = False) -> bool:
    """Determine whether the Unit Head is the final authority for the leave category.

    BR-EL-016: 'For CL and RH, including associated Station Leave, the applicant's
    Unit Head is the final approve/reject authority except for the Director-specific
    self-sanction case.'
    """
    if is_director:
        return False
    return leave_type_code in (LeaveCategory.CL.value, LeaveCategory.RH.value)


def requires_higher_sanction(leave_type_code: str, is_director: bool = False) -> bool:
    """Determine whether higher sanction is required.

    BR-EL-017, BR-EL-018: SCL, EL, COL, and VL require higher sanction.
    Unit Head records Recommended or Not Recommended, and both continue to final sanction.
    """
    if is_director:
        return False
    return leave_type_code in (
        LeaveCategory.SCL.value,
        LeaveCategory.EL.value,
        LeaveCategory.COL.value,
        LeaveCategory.VL.value,
    )


def validate_substitute_nomination(
    applicant_id: int,
    substitute_id: int | None,
    requires_substitute: bool,
    start_date: date,
    end_date: date,
    substitute_active_leaves: list[tuple[date, date]] | None = None,
) -> None:
    """Validate substitute eligibility per BR-EL-014.

    - When required, exactly one substitute is nominated.
    - Substitute must not be the applicant.
    - Substitute must not have overlapping pending or approved leave.
    """
    if not requires_substitute and substitute_id is None:
        return

    if requires_substitute and substitute_id is None:
        raise ValueError("A substitute is required for this leave type (BR-EL-014).")

    if substitute_id == applicant_id:
        raise ValueError(
            "Applicant cannot nominate themselves as their own substitute (BR-EL-014)."
        )

    if substitute_active_leaves:
        for s_start, s_end in substitute_active_leaves:
            # Overlap condition: start <= s_end and end >= s_start
            if start_date <= s_end and end_date >= s_start:
                raise ValueError(
                    f"Nominated substitute has overlapping leave from {s_start} to {s_end} "
                    "(BR-EL-014)."
                )


def validate_leave_extension_dates(
    original_end_date: date,
    extension_start_date: date,
    extension_end_date: date,
) -> None:
    """Validate requested dates for leave extension (BR-EL-025, CW-EL-03).

    Extension must start immediately on the next day following original leave end date,
    or be contiguous with the original leave.
    """
    if extension_end_date < extension_start_date:
        raise ValueError("Extension end date cannot be earlier than extension start date.")

    expected_start = original_end_date + timedelta(days=1)
    if extension_start_date != expected_start:
        raise ValueError(
            f"Extension start date must be {expected_start} "
            f"(contiguous to original end date {original_end_date})."
        )


@dataclass(frozen=True)
class RolloverCalculationResult:
    user_id: int
    year: int
    cl_lapsed: Decimal
    rh_lapsed: Decimal
    scl_lapsed: Decimal
    vl_converted: Decimal
    el_credited_from_vl: Decimal
    el_carried_forward: Decimal
    col_carried_forward: Decimal
    next_year_balances: dict[str, Decimal]


def compute_year_end_rollover(
    user_id: int,
    year: int,
    current_balances: dict[str, tuple[Decimal, Decimal]],  # code -> (allocated, used)
    is_faculty: bool,
    max_el_cap: Decimal = MAX_EL_CARRY_FORWARD_CAP,
) -> RolloverCalculationResult:
    """Compute year-end leave balance rollover per BR-EL-002 through BR-EL-009.

    - CL (BR-EL-002): unused lapses. Next year receives fresh 8 CL.
    - RH (BR-EL-003): unused lapses. Next year receives fresh 2 RH.
    - SCL (BR-EL-004): unused lapses. Next year receives fresh 15 SCL.
    - VL (BR-EL-007, BR-EL-008): faculty only; unused VL converts to EL at 2:1.
      VL does not carry forward. Faculty receives fresh 60 VL for next year.
    - EL (BR-EL-005):
      - Non-faculty: unused carries forward + 30 fresh quota, subject to cap.
      - Faculty: unused carried forward + converted EL, subject to cap.
    - COL (BR-EL-009): unused carries forward + 20 fresh quota.
    """
    def _unused(code: str) -> Decimal:
        alloc, used = current_balances.get(code, (Decimal("0.0"), Decimal("0.0")))
        u = alloc - used
        if u < Decimal("0.0"):
            raise ValueError(
                f"Balance inconsistency for {code}: allocated ({alloc}) < used ({used})"
            )
        return u

    cl_unused = _unused(LeaveCategory.CL.value)
    rh_unused = _unused(LeaveCategory.RH.value)
    scl_unused = _unused(LeaveCategory.SCL.value)

    vl_unused = _unused(LeaveCategory.VL.value) if is_faculty else Decimal("0.0")
    el_unused = _unused(LeaveCategory.EL.value)
    col_unused = _unused(LeaveCategory.COL.value)

    # Lapsing
    cl_lapsed = cl_unused
    rh_lapsed = rh_unused
    scl_lapsed = scl_unused

    # VL Conversion
    vl_converted = vl_unused
    el_credited_from_vl = convert_vl_to_el(vl_converted) if is_faculty else Decimal("0.0")

    # EL Calculation
    if is_faculty:
        total_el_before_cap = el_unused + el_credited_from_vl
    else:
        total_el_before_cap = el_unused + ANNUAL_QUOTAS[LeaveCategory.EL.value]

    el_carried = min(total_el_before_cap, max_el_cap)

    # COL Calculation (unused + 20 fresh annual credit)
    col_carried = col_unused + ANNUAL_QUOTAS[LeaveCategory.COL.value]

    next_year_balances: dict[str, Decimal] = {
        LeaveCategory.CL.value: ANNUAL_QUOTAS[LeaveCategory.CL.value],
        LeaveCategory.RH.value: ANNUAL_QUOTAS[LeaveCategory.RH.value],
        LeaveCategory.SCL.value: ANNUAL_QUOTAS[LeaveCategory.SCL.value],
        LeaveCategory.EL.value: el_carried,
        LeaveCategory.COL.value: col_carried,
    }
    if is_faculty:
        next_year_balances[LeaveCategory.VL.value] = ANNUAL_QUOTAS[LeaveCategory.VL.value]

    return RolloverCalculationResult(
        user_id=user_id,
        year=year,
        cl_lapsed=cl_lapsed,
        rh_lapsed=rh_lapsed,
        scl_lapsed=scl_lapsed,
        vl_converted=vl_converted,
        el_credited_from_vl=el_credited_from_vl,
        el_carried_forward=el_carried,
        col_carried_forward=col_carried,
        next_year_balances=next_year_balances,
    )
