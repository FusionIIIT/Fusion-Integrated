"""Approval workflow routing and sanctioning services.

Implements CW-EL-01 / EL-UC-003 / EL-UC-004 / EL-UC-005.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm.domain.constants import (
    ApplicationStatus,
    SanctionDecision,
    TaskType,
)
from modules.elm.domain.state_machine import (
    transition_establishment_routing,
    transition_final_sanction,
    transition_unit_head_review,
)
from modules.elm.models import LeaveApplication, LeaveAuditLog, WorkflowTask
from modules.elm.selectors.leaves import get_application_by_id
from modules.elm.services.balances import debit_leave_balance


@transaction.atomic
def review_unit_head(
    application_id: int,
    reviewer_user_id: int,
    outcome: str,
    remarks: str = "",
) -> LeaveApplication:
    """Record Unit Head review outcome (EL-UC-003, BR-EL-016, BR-EL-017)."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    current_status = ApplicationStatus(app.status)
    requires_estt = bool(app.establishment_user_id)

    try:
        new_status = transition_unit_head_review(
            current_status,
            app.category,
            outcome,
            requires_establishment=requires_estt,
        )
    except ValueError as e:
        raise ConflictError(str(e)) from e

    from_state = app.status
    app.status = new_status.value
    app.unit_head_recommendation = outcome
    app.unit_head_action_at = timezone.now()
    app.unit_head_remarks = remarks

    # If CL/RH was approved, Unit Head decision is final (BR-EL-016)
    if new_status == ApplicationStatus.APPROVED:
        app.final_decision = SanctionDecision.APPROVE.value
        app.final_decision_at = timezone.now()
        app.final_decision_by_user_id = reviewer_user_id
        app.final_decision_remarks = remarks

        # Update leave account / debit balance on final approval (CFR-EL-016.3)
        debit_leave_balance(
            user_id=app.user_id,
            year=app.start_date.year,
            category=app.category,
            amount=app.chargeable_days,
            reference_id=str(app.id),
            remarks=f"Approved leave #{app.id} by Unit Head",
            performed_by_user_id=reviewer_user_id,
        )
    elif new_status == ApplicationStatus.REJECTED:
        app.final_decision = SanctionDecision.REJECT.value
        app.final_decision_at = timezone.now()
        app.final_decision_by_user_id = reviewer_user_id
        app.final_decision_remarks = remarks

    app.save()

    # Complete Unit Head task
    WorkflowTask.objects.filter(
        leave_application=app,
        task_type=TaskType.UNIT_HEAD_REVIEW.value,
        status="pending",
    ).update(status="completed", completed_at=timezone.now())

    # Create next task if still progressing
    if new_status == ApplicationStatus.AWAITING_ESTABLISHMENT and app.establishment_user_id:
        WorkflowTask.objects.create(
            leave_application=app,
            task_type=TaskType.ESTABLISHMENT_ROUTING.value,
            assigned_to_user_id=app.establishment_user_id,
            status="pending",
        )
    elif (
        new_status == ApplicationStatus.AWAITING_FINAL_DECISION
        and app.sanctioning_authority_user_id
    ):
        WorkflowTask.objects.create(
            leave_application=app,
            task_type=TaskType.FINAL_SANCTION.value,
            assigned_to_user_id=app.sanctioning_authority_user_id,
            status="pending",
        )

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=reviewer_user_id,
        action="unit_head_review",
        from_state=from_state,
        to_state=new_status.value,
        remarks=remarks or outcome,
        payload={"outcome": outcome},
    )

    return app


@transaction.atomic
def route_establishment(
    application_id: int,
    establishment_user_id: int,
    remarks: str = "",
) -> LeaveApplication:
    """Perform Establishment-level verification and forward request (EL-UC-004, CFR-EL-014.7)."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    current_status = ApplicationStatus(app.status)
    try:
        new_status = transition_establishment_routing(current_status)
    except ValueError as e:
        raise ConflictError(str(e)) from e

    from_state = app.status
    app.status = new_status.value
    app.establishment_action_at = timezone.now()
    app.establishment_remarks = remarks
    app.save(
        update_fields=[
            "status",
            "establishment_action_at",
            "establishment_remarks",
            "updated_at",
        ]
    )

    # Complete establishment task
    WorkflowTask.objects.filter(
        leave_application=app,
        task_type=TaskType.ESTABLISHMENT_ROUTING.value,
        status="pending",
    ).update(status="completed", completed_at=timezone.now())

    # Create final sanction task
    if app.sanctioning_authority_user_id:
        WorkflowTask.objects.create(
            leave_application=app,
            task_type=TaskType.FINAL_SANCTION.value,
            assigned_to_user_id=app.sanctioning_authority_user_id,
            status="pending",
        )

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=establishment_user_id,
        action="establishment_forward",
        from_state=from_state,
        to_state=new_status.value,
        remarks=remarks or "Forwarded to final sanctioning authority",
    )

    return app


@transaction.atomic
def sanction_decision(
    application_id: int,
    sanctioner_user_id: int,
    decision: str,
    remarks: str = "",
) -> LeaveApplication:
    """Record final sanctioning decision (EL-UC-005, CFR-EL-016)."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    current_status = ApplicationStatus(app.status)
    try:
        new_status = transition_final_sanction(current_status, decision)
    except ValueError as e:
        raise ConflictError(str(e)) from e

    from_state = app.status
    app.status = new_status.value
    app.final_decision = decision
    app.final_decision_at = timezone.now()
    app.final_decision_by_user_id = sanctioner_user_id
    app.final_decision_remarks = remarks

    # On final approval, deduct balance (CFR-EL-016.3)
    if new_status == ApplicationStatus.APPROVED:
        debit_leave_balance(
            user_id=app.user_id,
            year=app.start_date.year,
            category=app.category,
            amount=app.chargeable_days,
            reference_id=str(app.id),
            remarks=f"Final sanction approval #{app.id}",
            performed_by_user_id=sanctioner_user_id,
        )

    app.save()

    # Complete final sanction / director task
    WorkflowTask.objects.filter(
        leave_application=app,
        task_type__in=[TaskType.FINAL_SANCTION.value, TaskType.DIRECTOR_SELF_SANCTION.value],
        status="pending",
    ).update(status="completed", completed_at=timezone.now())

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=sanctioner_user_id,
        action="final_sanction_decision",
        from_state=from_state,
        to_state=new_status.value,
        remarks=remarks or decision,
        payload={"decision": decision},
    )

    return app
