"""Cancellation workflow service for Employee Leave Management (CW-EL-02 / BR-EL-023)."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.elm.domain.policy import (
    ApplicationStatus,
    is_unit_head_final_authority,
)
from modules.elm.models import LeaveApplication, LeaveBalance


@transaction.atomic
def request_cancellation(
    application_id: int,
    user_id: int | None = None,
    reason: str = "",
    current_date: date | None = None,
    applicant_user_id: int | None = None,
) -> LeaveApplication:
    """Request pre-start cancellation of an approved leave per BR-EL-023 / EL-UC-008.

    - Approved leave only.
    - Start date has not yet occurred (current_date < start_date).
    - Transitions to cancellation pending without editing the approved leave in place.
    - Balance is not refunded at this stage.
    """
    effective_user_id = user_id if user_id is not None else applicant_user_id
    if effective_user_id is None:
        raise ValueError("User ID is required for cancellation request.")
    user_id = effective_user_id
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    if app.user_id != user_id:
        raise ValueError("You can only request cancellation for your own leave application.")

    if app.status != ApplicationStatus.APPROVED.value:
        raise ValueError(
            f"Only approved leave can be cancelled (got '{app.status}'). "
            "Pending requests must use the withdrawal mechanism (BR-EL-022, BR-EL-023)."
        )

    today = current_date or timezone.localdate()
    if today >= app.start_date:
        raise ValueError(
            f"Approved leave can be cancelled only before its start date "
            f"(start date {app.start_date}, today {today}) (BR-EL-023)."
        )

    if app.cancellation_status in ("requested", "approved"):
        raise ValueError(
            "Cancellation has already been requested or approved for this application."
        )

    app.cancellation_status = "requested"
    app.cancellation_reason = reason
    app.status = ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD.value
    app.save(update_fields=["cancellation_status", "cancellation_reason", "status", "updated_at"])
    return app


@transaction.atomic
def review_cancellation(
    application_id: int,
    reviewer_user_id: int,
    decision: str,  # "approved", "rejected", "recommended", "not_recommended"
    remarks: str = "",
    reviewer_role: str = "",
) -> LeaveApplication:
    """Review cancellation through the applicable hierarchy per CW-EL-02 rows 2-8."""
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    now = timezone.now()
    days = Decimal(str(app.total_days))

    balance = (
        LeaveBalance.objects.select_for_update()
        .filter(user_id=app.user_id, leave_type=app.leave_type, year=app.start_date.year)
        .first()
    )

    if app.status == ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD.value:
        if is_unit_head_final_authority(app.leave_type.code):
            # CL or RH: Unit Head makes final decision on cancellation (CW-EL-02 rows 2-3)
            if decision == "approved":
                app.status = ApplicationStatus.CANCELLED.value
                app.cancellation_status = "approved"
                if not app.is_balance_refunded and balance:
                    balance.used -= days
                    balance.save(update_fields=["used", "updated_at"])
                    app.is_balance_refunded = True
            elif decision == "rejected":
                # Rejection leaves original approval unchanged (CW-EL-02 row 3 / BR-EL-023)
                app.status = ApplicationStatus.APPROVED.value
                app.cancellation_status = "rejected"
            else:
                raise ValueError(
                    f"Unit Head final cancellation decision on {app.leave_type.code} "
                    f"must be 'approved' or 'rejected', got '{decision}'."
                )
            app.cancellation_reviewer_user_id = reviewer_user_id
            app.cancellation_remarks = remarks
            app.cancellation_decided_at = now
        else:
            # SCL, EL, COL, VL: Unit Head records recommendation (CW-EL-02 row 5 / BR-EL-017)
            if decision in ("recommended", "not_recommended"):
                app.cancellation_remarks = remarks
                app.cancellation_reviewer_user_id = reviewer_user_id
                # Both outcomes continue to final sanction (BR-EL-017)
                app.status = ApplicationStatus.CANCELLATION_PENDING_FINAL.value
            elif decision in ("approved", "rejected") and reviewer_role in (
                "admin", "director", "sanction_authority"
            ):
                # Authorized higher authority acting directly
                if decision == "approved":
                    app.status = ApplicationStatus.CANCELLED.value
                    app.cancellation_status = "approved"
                    if not app.is_balance_refunded and balance:
                        balance.used -= days
                        balance.save(update_fields=["used", "updated_at"])
                        app.is_balance_refunded = True
                else:
                    app.status = ApplicationStatus.APPROVED.value
                    app.cancellation_status = "rejected"
                app.cancellation_reviewer_user_id = reviewer_user_id
                app.cancellation_remarks = remarks
                app.cancellation_decided_at = now
            else:
                raise ValueError(
                    f"Unit Head recommendation on higher-sanction cancellation must be "
                    f"'recommended' or 'not_recommended', got '{decision}'."
                )

    elif app.status == ApplicationStatus.CANCELLATION_PENDING_FINAL.value:
        # Final Sanction Authority decision (CW-EL-02 rows 7-8)
        if decision == "approved":
            app.status = ApplicationStatus.CANCELLED.value
            app.cancellation_status = "approved"
            if not app.is_balance_refunded and balance:
                balance.used -= days
                balance.save(update_fields=["used", "updated_at"])
                app.is_balance_refunded = True
        elif decision == "rejected":
            app.status = ApplicationStatus.APPROVED.value
            app.cancellation_status = "rejected"
        else:
            raise ValueError(
                f"Final sanction cancellation decision must be 'approved' or 'rejected', "
                f"got '{decision}'."
            )
        app.cancellation_reviewer_user_id = reviewer_user_id
        app.cancellation_remarks = remarks
        app.cancellation_decided_at = now

    else:
        raise ValueError(
            f"Application {app.pk} is not pending cancellation (status: '{app.status}')."
        )

    app.save(
        update_fields=[
            "status",
            "cancellation_status",
            "cancellation_remarks",
            "cancellation_reviewer_user_id",
            "cancellation_decided_at",
            "is_balance_refunded",
            "updated_at",
        ]
    )
    return app
