"""Substitute response and replacement services (CW-EL-01 / EL-UC-002 / EL-UC-019)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.elm.domain.constants import (
    ApplicationStatus,
    SubstituteStatus,
    TaskType,
)
from modules.elm.domain.state_machine import (
    transition_substitute_replace,
    transition_substitute_response,
)
from modules.elm.domain.validation import validate_substitute_eligibility
from modules.elm.models import LeaveApplication, LeaveAuditLog, WorkflowTask
from modules.elm.selectors.leaves import (
    get_application_by_id,
    get_substitute_active_leaves,
)


@transaction.atomic
def respond_substitute(
    application_id: int,
    substitute_user_id: int,
    accepted: bool,
    remarks: str = "",
) -> LeaveApplication:
    """Record substitute's Accept or Decline response (EL-UC-002, BR-EL-015)."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    if app.substitute_user_id != substitute_user_id:
        raise BadRequestError("You are not the nominated substitute for this request.")

    current_status = ApplicationStatus(app.status)
    try:
        new_status = transition_substitute_response(
            current_status,
            accepted,
            applicant_is_director=(app.sanctioning_authority_role.lower() == "director"),
        )
    except ValueError as e:
        raise ConflictError(str(e)) from e

    from_state = app.status
    app.status = new_status.value
    app.substitute_status = (
        SubstituteStatus.ACCEPTED.value if accepted else SubstituteStatus.DECLINED.value
    )
    app.substitute_responded_at = timezone.now()
    app.substitute_remarks = remarks
    app.save(update_fields=[
        "status", "substitute_status", "substitute_responded_at", "substitute_remarks", "updated_at"
    ])

    # Complete the substitute task
    WorkflowTask.objects.filter(
        leave_application=app,
        task_type=TaskType.SUBSTITUTE_RESPONSE.value,
        assigned_to_user_id=substitute_user_id,
        status="pending",
    ).update(status="completed", completed_at=timezone.now())

    # If accepted, route to Unit Head or Director
    if accepted:
        if new_status == ApplicationStatus.AWAITING_DIRECTOR:
            WorkflowTask.objects.create(
                leave_application=app,
                task_type=TaskType.DIRECTOR_SELF_SANCTION.value,
                assigned_to_user_id=app.user_id,
                status="pending",
            )
        elif new_status == ApplicationStatus.AWAITING_UNIT_HEAD and app.unit_head_user_id:
            WorkflowTask.objects.create(
                leave_application=app,
                task_type=TaskType.UNIT_HEAD_REVIEW.value,
                assigned_to_user_id=app.unit_head_user_id,
                status="pending",
            )

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=substitute_user_id,
        action="substitute_accept" if accepted else "substitute_decline",
        from_state=from_state,
        to_state=new_status.value,
        remarks=remarks or ("Accepted" if accepted else "Declined"),
    )

    return app


@transaction.atomic
def replace_substitute(
    application_id: int,
    applicant_user_id: int,
    new_substitute_user_id: int,
) -> LeaveApplication:
    """Nominate replacement substitute after decline (EL-UC-019, BR-EL-014)."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    if app.user_id != applicant_user_id:
        raise BadRequestError("Only the applicant can nominate a replacement substitute.")

    current_status = ApplicationStatus(app.status)
    try:
        new_status = transition_substitute_replace(current_status)
    except ValueError as e:
        raise ConflictError(str(e)) from e

    # Validate replacement substitute eligibility
    user_map = directory.get_users([new_substitute_user_id])
    sub_dto = user_map.get(new_substitute_user_id)
    sub_kind = sub_dto.kind if sub_dto else None
    sub_leaves = get_substitute_active_leaves(new_substitute_user_id)

    try:
        validate_substitute_eligibility(
            applicant_user_id,
            new_substitute_user_id,
            sub_kind,
            sub_leaves,
            app.start_date,
            app.end_date,
        )
    except ValueError as e:
        raise BadRequestError(str(e)) from e

    from_state = app.status
    app.status = new_status.value
    app.substitute_user_id = new_substitute_user_id
    app.substitute_status = SubstituteStatus.PENDING.value
    app.substitute_responded_at = None
    app.substitute_remarks = ""
    app.save(update_fields=[
        "status", "substitute_user_id", "substitute_status",
        "substitute_responded_at", "substitute_remarks", "updated_at"
    ])

    # Assign fresh substitute task
    WorkflowTask.objects.create(
        leave_application=app,
        task_type=TaskType.SUBSTITUTE_RESPONSE.value,
        assigned_to_user_id=new_substitute_user_id,
        status="pending",
    )

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=applicant_user_id,
        action="replace_substitute",
        from_state=from_state,
        to_state=new_status.value,
        remarks=f"Nominated replacement substitute #{new_substitute_user_id}",
    )

    return app
