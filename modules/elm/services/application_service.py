"""Core application service for Employee Leave Management (CW-EL-01)."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.elm.domain.policy import (
    ApplicationStatus,
    calculate_leave_days,
    is_unit_head_final_authority,
    validate_substitute_nomination,
)
from modules.elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveType,
)


def _check_applicant_no_overlap(
    user_id: int, start_date: date, end_date: date, exclude_id: int | None = None
) -> None:
    """Verify applicant has no overlapping active or pending leave applications."""
    qs = LeaveApplication.objects.filter(
        user_id=user_id,
        status__in=[
            ApplicationStatus.PENDING.value,
            ApplicationStatus.AWAITING_SUBSTITUTE.value,
            ApplicationStatus.APPLICANT_ACTION_REQUIRED.value,
            ApplicationStatus.AWAITING_UNIT_HEAD.value,
            ApplicationStatus.AWAITING_FINAL_SANCTION.value,
            ApplicationStatus.AWAITING_DIRECTOR.value,
            ApplicationStatus.RECOMMENDED.value,
            ApplicationStatus.APPROVED.value,
        ],
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)
    if qs.exists():
        overlap = qs.first()
        raise ValueError(
            f"You already have an active leave application ({overlap.pk}) "
            f"overlapping with {start_date} to {end_date}."
        )


def _get_substitute_active_leaves(substitute_id: int) -> list[tuple[date, date]]:
    """Retrieve all active or pending leave date ranges for the nominated substitute."""
    leaves = LeaveApplication.objects.filter(
        user_id=substitute_id,
        status__in=[
            ApplicationStatus.PENDING.value,
            ApplicationStatus.AWAITING_SUBSTITUTE.value,
            ApplicationStatus.AWAITING_UNIT_HEAD.value,
            ApplicationStatus.AWAITING_FINAL_SANCTION.value,
            ApplicationStatus.AWAITING_DIRECTOR.value,
            ApplicationStatus.RECOMMENDED.value,
            ApplicationStatus.APPROVED.value,
        ],
    ).values_list("start_date", "end_date")
    return list(leaves)


@transaction.atomic
def apply_leave(
    user_id: int,
    leave_type_code: str,
    start_date: date,
    end_date: date,
    half_day: bool = False,
    station_leave: bool = False,
    station_address: str = "",
    reason: str = "",
    substitute_user_id: int | None = None,
    is_director: bool = False,
) -> LeaveApplication:
    """Submit a new leave application per CW-EL-01 / EL-UC-001."""
    leave_type = LeaveType.objects.filter(code=leave_type_code, is_active=True).first()
    if not leave_type:
        raise ValueError(f"Leave type '{leave_type_code}' does not exist or is inactive.")

    total_days = calculate_leave_days(start_date, end_date, half_day)

    # Check RH calendar applicability (BR-EL-003)
    if leave_type_code == "RH" and not HolidayCalendar.objects.filter(
        date=start_date, is_restricted=True
    ).exists():
        raise ValueError(
            f"{start_date} is not listed as a Restricted Holiday in the calendar (BR-EL-003)."
        )

    # Check applicant overlap
    _check_applicant_no_overlap(user_id, start_date, end_date)

    # Check substitute requirements (BR-EL-014)
    if leave_type.requires_substitute or substitute_user_id is not None:
        sub_leaves = (
            _get_substitute_active_leaves(substitute_user_id) if substitute_user_id else []
        )
        validate_substitute_nomination(
            applicant_id=user_id,
            substitute_id=substitute_user_id,
            requires_substitute=leave_type.requires_substitute,
            start_date=start_date,
            end_date=end_date,
            substitute_active_leaves=sub_leaves,
        )

    # Verify and lock leave balance
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
            f"Insufficient leave balance: requested {total_days} days, "
            f"but remaining balance is {balance.remaining} days."
        )

    # Determine initial workflow state (CW-EL-01 table rows 1-3)
    if leave_type.requires_substitute and substitute_user_id is not None:
        init_status = ApplicationStatus.AWAITING_SUBSTITUTE.value
        sub_status = "pending"
    elif is_director:
        init_status = ApplicationStatus.AWAITING_DIRECTOR.value
        sub_status = "none"
    else:
        init_status = ApplicationStatus.AWAITING_UNIT_HEAD.value
        sub_status = "none"

    # Reserve balance in pending
    balance.pending += total_days
    balance.save(update_fields=["pending", "updated_at"])

    return LeaveApplication.objects.create(
        user_id=user_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        station_leave=station_leave,
        station_address=station_address,
        reason=reason,
        substitute_user_id=substitute_user_id,
        substitute_status=sub_status,
        status=init_status,
    )


@transaction.atomic
def respond_substitute(
    application_id: int,
    substitute_user_id: int,
    decision: str,  # "accepted" or "declined"
    is_director: bool = False,
) -> LeaveApplication:
    """Handle substitute response per CW-EL-01 rows 4-6 / EL-UC-002."""
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    if app.substitute_user_id != substitute_user_id:
        raise ValueError("You are not the designated substitute for this application.")

    if app.status != ApplicationStatus.AWAITING_SUBSTITUTE.value:
        raise ValueError(
            f"Application is in status '{app.status}', not awaiting substitute response."
        )

    if decision == "accepted":
        app.substitute_status = "accepted"
        if is_director or app.user_id == substitute_user_id:
            # Director applicant
            app.status = ApplicationStatus.AWAITING_DIRECTOR.value
        else:
            app.status = ApplicationStatus.AWAITING_UNIT_HEAD.value
    elif decision == "declined":
        app.substitute_status = "declined"
        app.status = ApplicationStatus.APPLICANT_ACTION_REQUIRED.value
    else:
        raise ValueError(
            f"Invalid substitute decision: {decision}. Must be 'accepted' or 'declined'."
        )

    app.save(update_fields=["substitute_status", "status", "updated_at"])
    return app


@transaction.atomic
def nominate_replacement_substitute(
    application_id: int,
    applicant_user_id: int,
    new_substitute_user_id: int | None = None,
    substitute_user_id: int | None = None,
) -> LeaveApplication:
    """Nominate a replacement substitute after previous decline per EL-UC-019 / BR-EL-015."""
    target_sub_id = (
        new_substitute_user_id if new_substitute_user_id is not None else substitute_user_id
    )
    if target_sub_id is None:
        raise ValueError("A replacement substitute must be nominated.")
    new_substitute_user_id = target_sub_id
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    if app.user_id != applicant_user_id:
        raise ValueError("You can only nominate a substitute for your own application.")

    if app.status != ApplicationStatus.APPLICANT_ACTION_REQUIRED.value:
        raise ValueError(
            f"Replacement nomination requires application to be in "
            f"'{ApplicationStatus.APPLICANT_ACTION_REQUIRED.value}', got '{app.status}'."
        )

    # Re-validate eligibility and overlaps
    sub_leaves = _get_substitute_active_leaves(new_substitute_user_id)
    validate_substitute_nomination(
        applicant_id=applicant_user_id,
        substitute_id=new_substitute_user_id,
        requires_substitute=True,
        start_date=app.start_date,
        end_date=app.end_date,
        substitute_active_leaves=sub_leaves,
    )

    app.substitute_user_id = new_substitute_user_id
    app.substitute_status = "pending"
    app.status = ApplicationStatus.AWAITING_SUBSTITUTE.value
    app.save(update_fields=["substitute_user_id", "substitute_status", "status", "updated_at"])
    return app


@transaction.atomic
def withdraw_leave(application_id: int, applicant_user_id: int) -> LeaveApplication:
    """Immediately withdraw a pending leave application per BR-EL-022 / EL-UC-007."""
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    if app.user_id != applicant_user_id:
        raise ValueError("You can only withdraw your own leave application.")

    terminal_statuses = [
        ApplicationStatus.APPROVED.value,
        ApplicationStatus.REJECTED.value,
        ApplicationStatus.WITHDRAWN.value,
        ApplicationStatus.CANCELLED.value,
    ]
    if app.status in terminal_statuses:
        raise ValueError(f"Cannot withdraw application in status '{app.status}'.")

    # Release pending balance
    balance = (
        LeaveBalance.objects.select_for_update()
        .filter(user_id=app.user_id, leave_type=app.leave_type, year=app.start_date.year)
        .first()
    )
    if balance and balance.pending >= app.total_days:
        balance.pending -= Decimal(str(app.total_days))
        balance.save(update_fields=["pending", "updated_at"])

    app.status = ApplicationStatus.WITHDRAWN.value
    app.save(update_fields=["status", "updated_at"])
    return app


@transaction.atomic
def review_leave(
    application_id: int,
    reviewer_user_id: int,
    decision: str,  # "approved", "rejected", "recommended", "not_recommended"
    remarks: str = "",
    reviewer_role: str = "",
) -> LeaveApplication:
    """Execute review/sanction decision per CW-EL-01 / BR-EL-016-020."""
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    now = timezone.now()
    days = Decimal(str(app.total_days))
    balance = (
        LeaveBalance.objects.select_for_update()
        .filter(user_id=app.user_id, leave_type=app.leave_type, year=app.start_date.year)
        .first()
    )

    # Unit Head Review Stage
    if app.status in (
        ApplicationStatus.AWAITING_UNIT_HEAD.value,
        ApplicationStatus.PENDING.value,
    ):
        if is_unit_head_final_authority(app.leave_type.code):
            # CL or RH: Unit Head makes final decision (BR-EL-016)
            if decision == "approved":
                if balance:
                    if balance.pending >= days:
                        balance.pending -= days
                    balance.used += days
                    balance.save(update_fields=["pending", "used", "updated_at"])
                app.status = ApplicationStatus.APPROVED.value
            elif decision == "rejected":
                if balance and balance.pending >= days:
                    balance.pending -= days
                    balance.save(update_fields=["pending", "updated_at"])
                app.status = ApplicationStatus.REJECTED.value
            else:
                raise ValueError(
                    f"Unit Head final decision on {app.leave_type.code} must be "
                    f"'approved' or 'rejected', got '{decision}'."
                )
            app.reviewer_user_id = reviewer_user_id
            app.review_remarks = remarks
            app.decided_at = now
        else:
            # SCL, EL, COL, VL: Unit Head records recommendation (BR-EL-017)
            if decision in ("recommended", "not_recommended"):
                app.recommendation = decision
                app.recommended_by_user_id = reviewer_user_id
                app.recommended_at = now
                app.review_remarks = remarks
                # Both recommended and not_recommended continue to final sanction (BR-EL-017)
                app.status = ApplicationStatus.AWAITING_FINAL_SANCTION.value
            elif decision in ("approved", "rejected") and reviewer_role in (
                "admin", "director", "sanction_authority"
            ):
                # Authorized higher authority acting directly
                if decision == "approved":
                    if balance:
                        if balance.pending >= days:
                            balance.pending -= days
                        balance.used += days
                        balance.save(update_fields=["pending", "used", "updated_at"])
                    app.status = ApplicationStatus.APPROVED.value
                else:
                    if balance and balance.pending >= days:
                        balance.pending -= days
                        balance.save(update_fields=["pending", "updated_at"])
                    app.status = ApplicationStatus.REJECTED.value
                app.reviewer_user_id = reviewer_user_id
                app.review_remarks = remarks
                app.decided_at = now
            else:
                raise ValueError(
                    f"Unit Head on {app.leave_type.code} must record 'recommended' or "
                    f"'not_recommended' (BR-EL-017), got '{decision}'."
                )

    # Director Self-Sanction Stage (BR-EL-020)
    elif app.status == ApplicationStatus.AWAITING_DIRECTOR.value:
        if reviewer_user_id != app.user_id:
            raise ValueError(
                "Only the Director applicant can perform Director self-sanction (BR-EL-020)."
            )
        if decision == "approved":
            if balance:
                if balance.pending >= days:
                    balance.pending -= days
                balance.used += days
                balance.save(update_fields=["pending", "used", "updated_at"])
            app.status = ApplicationStatus.APPROVED.value
        elif decision == "rejected":
            if balance and balance.pending >= days:
                balance.pending -= days
                balance.save(update_fields=["pending", "updated_at"])
            app.status = ApplicationStatus.REJECTED.value
        else:
            raise ValueError(
                f"Director self-sanction must be 'approved' or 'rejected', got '{decision}'."
            )
        app.reviewer_user_id = reviewer_user_id
        app.review_remarks = remarks
        app.decided_at = now

    # Final Sanction Decision Stage (BR-EL-018)
    elif app.status in (
        ApplicationStatus.AWAITING_FINAL_SANCTION.value,
        ApplicationStatus.RECOMMENDED.value,
    ):
        if decision == "approved":
            if balance:
                if balance.pending >= days:
                    balance.pending -= days
                balance.used += days
                balance.save(update_fields=["pending", "used", "updated_at"])
            app.status = ApplicationStatus.APPROVED.value
        elif decision == "rejected":
            if balance and balance.pending >= days:
                balance.pending -= days
                balance.save(update_fields=["pending", "updated_at"])
            app.status = ApplicationStatus.REJECTED.value
        else:
            raise ValueError(
                f"Final sanction decision must be 'approved' or 'rejected', got '{decision}'."
            )
        app.reviewer_user_id = reviewer_user_id
        app.review_remarks = remarks
        app.decided_at = now

    else:
        raise ValueError(f"Cannot review application in status '{app.status}'.")

    app.save(
        update_fields=[
            "status",
            "recommendation",
            "recommended_by_user_id",
            "recommended_at",
            "reviewer_user_id",
            "review_remarks",
            "decided_at",
            "updated_at",
        ]
    )
    return app
