"""Resumption of duty submission and review services (CW-EL-04 / EL-UC-010 / EL-UC-011)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.elm.domain.constants import (
    ApplicationStatus,
    LeaveCategory,
    ResumptionStatus,
    TaskType,
    TransactionType,
)
from modules.elm.domain.counting import calculate_chargeable_days
from modules.elm.domain.state_machine import determine_resumption_outcome
from modules.elm.models import (
    LeaveAuditLog,
    LeaveResumption,
    WorkflowTask,
)
from modules.elm.selectors.calendars import get_closed_holidays_set
from modules.elm.selectors.leaves import get_application_by_id
from modules.elm.services.balances import (
    credit_leave_balance,
    debit_leave_balance,
)


@transaction.atomic
def submit_resumption(
    application_id: int,
    applicant_user_id: int,
    actual_resumption_date: date,
    resumption_details: str,
) -> LeaveResumption:
    """Submit actual resumption date and details after EL/COL/VL (EL-UC-010, BR-EL-027)."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    if app.user_id != applicant_user_id:
        raise BadRequestError("Only the applicant can submit resumption for their leave.")

    # BR-EL-027: Resumption review applies to EL, COL, and VL
    if app.category not in (
        LeaveCategory.EL.value,
        LeaveCategory.COL.value,
        LeaveCategory.VL.value,
    ):
        raise BadRequestError(
            f"Formal resumption review is only supported for EL, COL, and VL. "
            f"Not applicable to {app.category}."
        )

    if app.status != ApplicationStatus.APPROVED.value:
        raise ConflictError(f"Cannot submit resumption for leave in status '{app.status}'.")

    # Check if resumption already submitted
    existing = LeaveResumption.objects.filter(leave_application=app).first()
    if existing:
        raise ConflictError("Resumption has already been submitted for this leave.")

    return_type, _ = determine_resumption_outcome(app.end_date, actual_resumption_date)

    resumption = LeaveResumption.objects.create(
        leave_application=app,
        applicant_user_id=applicant_user_id,
        approved_end_date=app.end_date,
        actual_resumption_date=actual_resumption_date,
        return_type=return_type,
        resumption_details=resumption_details,
        status=ResumptionStatus.PENDING_REVIEW.value,
    )

    # Assign task to Sanctioning Authority
    if app.sanctioning_authority_user_id:
        WorkflowTask.objects.create(
            resumption=resumption,
            task_type=TaskType.RESUMPTION_REVIEW.value,
            assigned_to_user_id=app.sanctioning_authority_user_id,
            status="pending",
        )

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=applicant_user_id,
        action="submit_resumption",
        from_state=app.status,
        to_state=ResumptionStatus.PENDING_REVIEW.value,
        remarks=f"Submitted resumption: actual date {actual_resumption_date} ({return_type})",
        payload={"resumption_id": resumption.id, "actual_date": str(actual_resumption_date)},
    )

    return resumption


@transaction.atomic
def review_resumption(
    resumption_id: int,
    reviewer_user_id: int,
    remarks: str = "",
) -> LeaveResumption:
    """Review resumption and apply adjustments if early or late return (EL-UC-011, BR-EL-028)."""
    resumption = (
        LeaveResumption.objects.select_related("leave_application")
        .filter(id=resumption_id)
        .first()
    )
    if not resumption:
        raise NotFoundError(f"Resumption #{resumption_id} not found.")

    if resumption.status != ResumptionStatus.PENDING_REVIEW.value:
        raise ConflictError(
            f"Resumption #{resumption_id} is already reviewed (status: {resumption.status})."
        )

    app = resumption.leave_application
    return_type, new_status = determine_resumption_outcome(
        resumption.approved_end_date, resumption.actual_resumption_date
    )

    year = app.start_date.year
    closed_holidays = get_closed_holidays_set(year)
    adjustment_days = Decimal("0.00")

    if return_type == "normal":
        # BR-EL-028: Normal resumption -> NO leave period or balance adjustment
        adjustment_days = Decimal("0.00")

    elif return_type == "early":
        # Early return: employee returned before approved end date.
        # Restore unused days: from actual_resumption_date + 1 to approved_end_date
        unused_start = resumption.actual_resumption_date + timezone.timedelta(days=1)
        if unused_start <= resumption.approved_end_date:
            adjustment_days = calculate_chargeable_days(
                app.category,
                unused_start,
                resumption.approved_end_date,
                closed_holidays=closed_holidays,
            )
            # Credit back unused days
            credit_leave_balance(
                user_id=app.user_id,
                year=year,
                category=app.category,
                amount=adjustment_days,
                transaction_type=TransactionType.ADJUST_RESUMPTION_CREDIT.value,
                reference_id=f"resum-{resumption.id}",
                remarks=f"Early return credit for leave #{app.id}",
                performed_by_user_id=reviewer_user_id,
            )
            # Synchronize actual period
            app.end_date = resumption.actual_resumption_date
            app.chargeable_days = max(Decimal("0.00"), app.chargeable_days - adjustment_days)
            app.save(update_fields=["end_date", "chargeable_days", "updated_at"])

    elif return_type == "late":
        # Late return: employee returned after approved end date.
        # Debit extra days: from approved_end_date + 1 to actual_resumption_date
        extra_start = resumption.approved_end_date + timezone.timedelta(days=1)
        if extra_start <= resumption.actual_resumption_date:
            adjustment_days = calculate_chargeable_days(
                app.category,
                extra_start,
                resumption.actual_resumption_date,
                closed_holidays=closed_holidays,
            )
            # Debit extra days
            debit_leave_balance(
                user_id=app.user_id,
                year=year,
                category=app.category,
                amount=adjustment_days,
                transaction_type=TransactionType.ADJUST_RESUMPTION_DEBIT.value,
                reference_id=f"resum-{resumption.id}",
                remarks=f"Late return debit for leave #{app.id}",
                performed_by_user_id=reviewer_user_id,
            )
            # Synchronize actual period
            app.end_date = resumption.actual_resumption_date
            app.chargeable_days += adjustment_days
            app.save(update_fields=["end_date", "chargeable_days", "updated_at"])

    from_state = resumption.status
    resumption.status = new_status.value
    resumption.return_type = return_type
    resumption.adjustment_days = adjustment_days
    resumption.reviewed_by_user_id = reviewer_user_id
    resumption.reviewed_at = timezone.now()
    resumption.review_remarks = remarks
    resumption.save()

    WorkflowTask.objects.filter(
        resumption=resumption,
        task_type=TaskType.RESUMPTION_REVIEW.value,
        status="pending",
    ).update(status="completed", completed_at=timezone.now())

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=reviewer_user_id,
        action="review_resumption",
        from_state=from_state,
        to_state=new_status.value,
        remarks=remarks or f"Resumption reviewed ({return_type})",
        payload={
            "resumption_id": resumption.id,
            "adjustment_days": str(adjustment_days),
            "return_type": return_type,
        },
    )

    return resumption
