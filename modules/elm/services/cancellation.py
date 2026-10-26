"""Approved leave pre-start cancellation services (CW-EL-02 / EL-UC-008 / BR-EL-023)."""
from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.constants import (
    ApplicationStatus,
    TaskType,
)
from modules.elm.domain.state_machine import (
    transition_cancellation_establishment,
    transition_cancellation_final,
    transition_cancellation_request,
    transition_cancellation_unit_head,
)
from modules.elm.models import LeaveApplication, LeaveAuditLog, WorkflowTask
from modules.elm.selectors.leaves import get_application_by_id
from modules.elm.services.balances import credit_leave_balance


@transaction.atomic
def request_cancellation(
    application_id: int,
    user_id: int,
    reason: str,
    *,
    today: date | None = None,
) -> LeaveApplication:
    """Request pre-start cancellation of an approved leave (EL-UC-008, BR-EL-023)."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    if app.user_id != user_id:
        raise BadRequestError("Only the applicant can request cancellation of approved leave.")

    curr_date = today or timezone.now().date()
    current_status = ApplicationStatus(app.status)

    try:
        new_status = transition_cancellation_request(current_status, app.start_date, curr_date)
    except ValueError as e:
        raise ConflictError(str(e)) from e

    from_state = app.status
    app.status = new_status.value
    app.cancellation_reason = reason
    app.cancellation_requested_at = timezone.now()
    app.save(
        update_fields=[
            "status",
            "cancellation_reason",
            "cancellation_requested_at",
            "updated_at",
        ]
    )

    # Create Unit Head review task for cancellation
    if app.unit_head_user_id:
        WorkflowTask.objects.create(
            leave_application=app,
            task_type=TaskType.CANCELLATION_UNIT_HEAD.value,
            assigned_to_user_id=app.unit_head_user_id,
            status="pending",
        )

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=user_id,
        action="request_cancellation",
        from_state=from_state,
        to_state=new_status.value,
        remarks=reason,
    )

    return app


@transaction.atomic
def review_cancellation_unit_head(
    application_id: int,
    reviewer_user_id: int,
    outcome: str,
    remarks: str = "",
) -> LeaveApplication:
    """Review cancellation request at Unit Head."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    if app.unit_head_user_id and app.unit_head_user_id != reviewer_user_id:
        raise PermissionDeniedError("Only the assigned Unit Head may review this cancellation.")

    current_status = ApplicationStatus(app.status)
    requires_estt = bool(app.establishment_user_id)

    try:
        new_status = transition_cancellation_unit_head(
            current_status,
            app.category,
            outcome,
            requires_establishment=requires_estt,
        )
    except ValueError as e:
        raise ConflictError(str(e)) from e

    from_state = app.status
    app.status = new_status.value
    app.cancellation_decision = outcome
    app.cancellation_decision_at = timezone.now()
    app.cancellation_decision_by_user_id = reviewer_user_id

    # If CL/RH was approved for cancellation, restore deducted balance (AFR-EL-019.5)
    if new_status == ApplicationStatus.CANCELLED:
        credit_leave_balance(
            user_id=app.user_id,
            year=app.start_date.year,
            category=app.category,
            amount=app.chargeable_days,
            reference_id=str(app.id),
            remarks=f"Restored balance on cancellation of leave #{app.id}",
            performed_by_user_id=reviewer_user_id,
        )

    app.save()

    # Complete Unit Head task
    WorkflowTask.objects.filter(
        leave_application=app,
        task_type=TaskType.CANCELLATION_UNIT_HEAD.value,
        status="pending",
    ).update(status="completed", completed_at=timezone.now())

    # Create next task if still progressing
    if (
        new_status == ApplicationStatus.CANCELLATION_PENDING_ESTABLISHMENT
        and app.establishment_user_id
    ):
        WorkflowTask.objects.create(
            leave_application=app,
            task_type=TaskType.CANCELLATION_ESTABLISHMENT.value,
            assigned_to_user_id=app.establishment_user_id,
            status="pending",
        )
    elif (
        new_status == ApplicationStatus.CANCELLATION_PENDING_FINAL
        and app.sanctioning_authority_user_id
    ):
        WorkflowTask.objects.create(
            leave_application=app,
            task_type=TaskType.CANCELLATION_FINAL.value,
            assigned_to_user_id=app.sanctioning_authority_user_id,
            status="pending",
        )

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=reviewer_user_id,
        action="cancellation_unit_head_review",
        from_state=from_state,
        to_state=new_status.value,
        remarks=remarks or outcome,
        payload={"outcome": outcome},
    )

    return app


@transaction.atomic
def review_cancellation_establishment(
    application_id: int,
    establishment_user_id: int,
    remarks: str = "",
) -> LeaveApplication:
    """Forward cancellation request at Establishment level."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    if app.establishment_user_id and app.establishment_user_id != establishment_user_id:
        raise PermissionDeniedError(
            "Only the assigned Establishment reviewer may forward this cancellation."
        )

    current_status = ApplicationStatus(app.status)
    try:
        new_status = transition_cancellation_establishment(current_status)
    except ValueError as e:
        raise ConflictError(str(e)) from e

    from_state = app.status
    app.status = new_status.value
    app.save(update_fields=["status", "updated_at"])

    # Complete establishment task
    WorkflowTask.objects.filter(
        leave_application=app,
        task_type=TaskType.CANCELLATION_ESTABLISHMENT.value,
        status="pending",
    ).update(status="completed", completed_at=timezone.now())

    if app.sanctioning_authority_user_id:
        WorkflowTask.objects.create(
            leave_application=app,
            task_type=TaskType.CANCELLATION_FINAL.value,
            assigned_to_user_id=app.sanctioning_authority_user_id,
            status="pending",
        )

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=establishment_user_id,
        action="cancellation_establishment_forward",
        from_state=from_state,
        to_state=new_status.value,
        remarks=remarks or "Forwarded cancellation to final authority",
    )

    return app


@transaction.atomic
def review_cancellation_final(
    application_id: int,
    sanctioner_user_id: int,
    decision: str,
    remarks: str = "",
) -> LeaveApplication:
    """Final decision on cancellation of higher-sanction leave."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    if (
        app.sanctioning_authority_user_id
        and app.sanctioning_authority_user_id != sanctioner_user_id
    ):
        raise PermissionDeniedError(
            "Only the assigned Sanctioning Authority may review this cancellation."
        )

    current_status = ApplicationStatus(app.status)
    try:
        new_status = transition_cancellation_final(current_status, decision)
    except ValueError as e:
        raise ConflictError(str(e)) from e

    from_state = app.status
    app.status = new_status.value
    app.cancellation_decision = decision
    app.cancellation_decision_at = timezone.now()
    app.cancellation_decision_by_user_id = sanctioner_user_id

    # If approved, restore deducted balance
    if new_status == ApplicationStatus.CANCELLED:
        credit_leave_balance(
            user_id=app.user_id,
            year=app.start_date.year,
            category=app.category,
            amount=app.chargeable_days,
            reference_id=str(app.id),
            remarks=f"Restored balance on final approved cancellation of leave #{app.id}",
            performed_by_user_id=sanctioner_user_id,
        )

    app.save()

    WorkflowTask.objects.filter(
        leave_application=app,
        task_type=TaskType.CANCELLATION_FINAL.value,
        status="pending",
    ).update(status="completed", completed_at=timezone.now())

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=sanctioner_user_id,
        action="cancellation_final_decision",
        from_state=from_state,
        to_state=new_status.value,
        remarks=remarks or decision,
        payload={"decision": decision},
    )

    return app
