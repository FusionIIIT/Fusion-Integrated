"""Offline-sanctioned leave synchronization service (BR-EL-029 / EL-UC-016)."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.elm.domain.policy import (
    ApplicationStatus,
    calculate_leave_days,
)
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveType
from modules.elm.services.application_service import _check_applicant_no_overlap


@transaction.atomic
def record_offline_sanctioned_leave(
    user_id: int,
    leave_type_code: str,
    start_date: date,
    end_date: date,
    sanction_reference: str,
    sanction_date: date,
    sanction_authority_name: str,
    reason: str = "",
    recorder_user_id: int = 0,
) -> LeaveApplication:
    """Retrospectively record leave already sanctioned through an offline process (BR-EL-029).

    - Requires valid sanction reference and authority evidence.
    - Rejects duplicate sanction references for the same employee, even across
      non-overlapping dates.
    - Validates date overlap with existing leave applications.
    - Applies exactly one balance deduction.
    - Does NOT initiate a second approval workflow.
    """
    if not sanction_reference.strip():
        raise ValueError("Sanction reference is required for offline-sanctioned leave (BR-EL-029).")

    if not sanction_authority_name.strip():
        raise ValueError("Sanction authority name is required for offline-sanctioned leave.")

    # Reject duplicate sanction reference for the same employee (BR-EL-029)
    if LeaveApplication.objects.filter(
        user_id=user_id,
        sanction_reference=sanction_reference.strip(),
    ).exists():
        raise ValueError(
            f"Sanction reference '{sanction_reference}' has already been recorded for user "
            f"{user_id} (BR-EL-029 duplicate rejection rule)."
        )

    leave_type = LeaveType.objects.filter(code=leave_type_code, is_active=True).first()
    if not leave_type:
        raise ValueError(f"Leave type '{leave_type_code}' does not exist or is inactive.")

    total_days = calculate_leave_days(start_date, end_date)

    # Validate no date overlap with existing active leaves
    _check_applicant_no_overlap(user_id, start_date, end_date)

    # Check and deduct leave balance directly (exactly once)
    balance = (
        LeaveBalance.objects.select_for_update()
        .filter(user_id=user_id, leave_type=leave_type, year=start_date.year)
        .first()
    )
    if not balance:
        raise ValueError(
            f"No leave balance record found for user {user_id}, type {leave_type_code}, "
            f"year {start_date.year}."
        )

    if balance.remaining < total_days:
        raise ValueError(
            f"Insufficient leave balance for offline entry: required {total_days} days, "
            f"but remaining balance is {balance.remaining} days."
        )

    # Balance deduction: directly into used
    balance.used += Decimal(str(total_days))
    balance.save(update_fields=["used", "updated_at"])

    # Create approved offline leave record without initiating approval workflow
    return LeaveApplication.objects.create(
        user_id=user_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        half_day=False,
        station_leave=False,
        reason=reason,
        status=ApplicationStatus.APPROVED.value,
        is_offline=True,
        sanction_reference=sanction_reference.strip(),
        sanction_date=sanction_date,
        sanction_authority_name=sanction_authority_name.strip(),
        reviewer_user_id=recorder_user_id,
        decided_at=timezone.now(),
    )
