"""Duty resumption service for Employee Leave Management (CW-EL-04 / BR-EL-027, BR-EL-028)."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.elm.domain.policy import (
    ApplicationStatus,
    LeaveCategory,
    ResumptionOutcome,
    calculate_resumption_adjustment,
)
from modules.elm.models import LeaveApplication, LeaveBalance


@transaction.atomic
def submit_duty_resumption(
    application_id: int,
    user_id: int,
    actual_resumption_date: date,
    remarks: str = "",
) -> LeaveApplication:
    """Submit formal duty resumption for review per CW-EL-04 row 1 / BR-EL-027 / EL-UC-010.

    Applies to EL, COL, and VL leave categories.
    """
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    if app.user_id != user_id:
        raise ValueError("You can only submit duty resumption for your own leave application.")

    if app.status != ApplicationStatus.APPROVED.value:
        raise ValueError(
            f"Duty resumption can only be submitted for an approved leave (got '{app.status}')."
        )

    allowed_types = (
        LeaveCategory.EL.value,
        LeaveCategory.COL.value,
        LeaveCategory.VL.value,
    )
    if app.leave_type.code not in allowed_types:
        raise ValueError(
            f"Formal resumption review applies only to EL, COL, and VL (BR-EL-027). "
            f"Current leave type is {app.leave_type.code}."
        )

    if app.resumption_status in (
        "pending_review",
        "reviewed_normal",
        "reviewed_early",
        "reviewed_late",
    ):
        raise ValueError(
            f"Duty resumption has already been submitted or completed for this application "
            f"(status: '{app.resumption_status}')."
        )

    if actual_resumption_date < app.start_date:
        raise ValueError(
            f"Actual resumption date ({actual_resumption_date}) cannot be earlier than "
            f"the leave start date ({app.start_date})."
        )

    app.actual_resumption_date = actual_resumption_date
    app.resumption_remarks = remarks
    app.resumption_status = "pending_review"
    app.save(
        update_fields=[
            "actual_resumption_date",
            "resumption_remarks",
            "resumption_status",
            "updated_at",
        ]
    )
    return app


@transaction.atomic
def review_duty_resumption(
    application_id: int,
    reviewer_user_id: int,
    review_remarks: str = "",
    remarks: str = "",
) -> LeaveApplication:
    """Review submitted duty resumption per CW-EL-04 rows 2-4 / BR-EL-028 / EL-UC-011.

    - Computes outcome (normal, early, late).
    - Adjusts balance accordingly.
    - Transitions resumption status to reviewed_normal, reviewed_early, or reviewed_late.
    - Prevents repeated reviews.
    """
    review_remarks = review_remarks or remarks
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    if app.resumption_status != "pending_review":
        raise ValueError(
            f"Application resumption cannot be reviewed in status '{app.resumption_status}'. "
            "Must be 'pending_review'."
        )

    if not app.actual_resumption_date:
        raise ValueError("Actual resumption date is not recorded on this application.")

    outcome, days_adjusted = calculate_resumption_adjustment(
        approved_start=app.start_date,
        approved_end=app.end_date,
        actual_resumption_date=app.actual_resumption_date,
    )

    balance = (
        LeaveBalance.objects.select_for_update()
        .filter(user_id=app.user_id, leave_type=app.leave_type, year=app.start_date.year)
        .first()
    )

    now = timezone.now()

    if outcome == ResumptionOutcome.NORMAL:
        # No balance adjustment (CW-EL-04 row 2 / BR-EL-028)
        app.resumption_status = ResumptionOutcome.NORMAL.value
        app.resumption_days_adjusted = Decimal("0.0")

    elif outcome == ResumptionOutcome.EARLY:
        # Early return: refund unused days (CW-EL-04 row 3 / BR-EL-028)
        app.resumption_status = ResumptionOutcome.EARLY.value
        app.resumption_days_adjusted = -days_adjusted
        if balance:
            balance.used -= days_adjusted
            balance.save(update_fields=["used", "updated_at"])

    elif outcome == ResumptionOutcome.LATE:
        # Late return: deduct extra days (CW-EL-04 row 4 / BR-EL-028)
        app.resumption_status = ResumptionOutcome.LATE.value
        app.resumption_days_adjusted = days_adjusted
        if balance:
            balance.used += days_adjusted
            balance.save(update_fields=["used", "updated_at"])

    app.resumption_reviewer_user_id = reviewer_user_id
    app.resumption_review_remarks = review_remarks
    app.resumption_decided_at = now
    app.save(
        update_fields=[
            "resumption_status",
            "resumption_days_adjusted",
            "resumption_reviewer_user_id",
            "resumption_review_remarks",
            "resumption_decided_at",
            "updated_at",
        ]
    )
    return app
