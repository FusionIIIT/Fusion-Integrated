"""Leave extension service for Employee Leave Management (CW-EL-03 / BR-EL-025)."""
from datetime import date
from decimal import Decimal

from django.db import transaction

from modules.elm.domain.policy import (
    ApplicationStatus,
    LeaveCategory,
    calculate_leave_days,
    validate_leave_extension_dates,
    validate_substitute_nomination,
)
from modules.elm.models import LeaveApplication, LeaveBalance
from modules.elm.services.application_service import (
    _check_applicant_no_overlap,
    _get_substitute_active_leaves,
)


@transaction.atomic
def request_extension(
    original_application_id: int,
    user_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    reason: str = "",
    substitute_user_id: int | None = None,
    applicant_user_id: int | None = None,
) -> LeaveApplication:
    """Request an extension to an existing approved leave application per CW-EL-03 / BR-EL-025.

    - Extension is available only for EL, COL, and VL (BR-EL-025).
    - Links to original application.
    - Validates date continuity and balance for incremental days.
    - Reserves incremental balance in pending. Original leave is not modified.
    """
    effective_user_id = user_id if user_id is not None else applicant_user_id
    if effective_user_id is None or start_date is None or end_date is None:
        raise ValueError("Missing required fields for extension request.")
    user_id = effective_user_id
    original = LeaveApplication.objects.select_for_update().get(pk=original_application_id)
    if original.user_id != user_id:
        raise ValueError("You can only request an extension for your own leave application.")

    if original.status != ApplicationStatus.APPROVED.value:
        raise ValueError(
            f"Extension can only be requested for an approved leave (got '{original.status}')."
        )

    allowed_types = (
        LeaveCategory.EL.value,
        LeaveCategory.COL.value,
        LeaveCategory.VL.value,
    )
    if original.leave_type.code not in allowed_types:
        raise ValueError(
            f"Leave extension is permitted only for ongoing EL, COL, and VL (BR-EL-025). "
            f"Current leave type is {original.leave_type.code}."
        )

    # Validate dates
    validate_leave_extension_dates(original.end_date, start_date, end_date)
    incremental_days = calculate_leave_days(start_date, end_date)

    # Check for applicant overlap with other leaves (excluding original)
    _check_applicant_no_overlap(user_id, start_date, end_date, exclude_id=original.pk)

    # Validate substitute nomination if required
    requires_sub = original.leave_type.requires_substitute
    if requires_sub or substitute_user_id is not None:
        sub_leaves = (
            _get_substitute_active_leaves(substitute_user_id) if substitute_user_id else []
        )
        validate_substitute_nomination(
            applicant_id=user_id,
            substitute_id=substitute_user_id,
            requires_substitute=requires_sub,
            start_date=start_date,
            end_date=end_date,
            substitute_active_leaves=sub_leaves,
        )

    # Check balance for incremental days only
    balance = (
        LeaveBalance.objects.select_for_update()
        .filter(user_id=user_id, leave_type=original.leave_type, year=start_date.year)
        .first()
    )
    if not balance:
        raise ValueError(
            f"No leave balance record found for user {user_id}, type {original.leave_type.code}, "
            f"year {start_date.year}."
        )

    if balance.remaining < incremental_days:
        raise ValueError(
            f"Insufficient leave balance for extension: requested {incremental_days} "
            f"additional days, but remaining balance is {balance.remaining} days."
        )

    # Initial routing status for extension (CW-EL-03 rows 1-2)
    if requires_sub and substitute_user_id is not None:
        ext_status = ApplicationStatus.AWAITING_SUBSTITUTE.value
        sub_status = "pending"
    else:
        ext_status = ApplicationStatus.AWAITING_UNIT_HEAD.value
        sub_status = "none"

    # Reserve incremental days in pending balance
    balance.pending += Decimal(str(incremental_days))
    balance.save(update_fields=["pending", "updated_at"])

    # Create linked extension application
    return LeaveApplication.objects.create(
        user_id=user_id,
        leave_type=original.leave_type,
        start_date=start_date,
        end_date=end_date,
        half_day=False,
        station_leave=original.station_leave,
        station_address=original.station_address,
        reason=reason,
        substitute_user_id=substitute_user_id,
        substitute_status=sub_status,
        status=ext_status,
        original_application=original,
        is_extension=True,
    )
