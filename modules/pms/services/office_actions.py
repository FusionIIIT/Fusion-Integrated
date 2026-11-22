from datetime import date
from django.db import transaction

from modules.pms.domain.business_rules import calculate_statutory_fer_deadline
from modules.pms.domain.state_machine import PatentStateMachine
from modules.pms.models.application import PatentApplication
from modules.pms.models.audit import PatentAuditEvent
from modules.pms.models.office_action import OfficeAction, ResponseStatus
from modules.pms.selectors.scoping import get_application_scoped


@transaction.atomic
def record_office_action(
    app_id: int,
    attorney_user_id: int,
    action_type: str,
    issue_date: date,
    objections: str,
    roles: list[str],
) -> OfficeAction:
    """Log an examination report or office action received from the Patent Office."""
    app = get_application_scoped(app_id, attorney_user_id, roles)

    deadline = calculate_statutory_fer_deadline(issue_date)

    action = OfficeAction.objects.create(
        application=app,
        action_type=action_type,
        issue_date=issue_date,
        statutory_deadline=deadline,
        objections_summary=objections,
        handled_by_attorney_id=attorney_user_id,
        response_status=ResponseStatus.PENDING,
    )

    next_state = PatentStateMachine.get_next_state(
        app.status,
        event="RECEIVE_FER",
        actor_roles=roles,
    )

    old_status = app.status
    app.status = next_state
    app.save(update_fields=["status", "updated_at"])

    PatentAuditEvent.objects.create(
        application=app,
        event_name="RECEIVE_OFFICE_ACTION",
        from_status=old_status,
        to_status=next_state,
        actor_user_id=attorney_user_id,
        payload={"action_type": action_type, "deadline": str(deadline)},
    )

    return action


@transaction.atomic
def submit_office_action_response(
    action_id: int,
    attorney_user_id: int,
    response_draft: str,
    roles: list[str],
) -> OfficeAction:
    """Submit formal response to an Office Action (BW-PMS-12, BW-PMS-13)."""
    action = OfficeAction.objects.select_related("application").get(pk=action_id)
    app = get_application_scoped(action.application_id, attorney_user_id, roles)

    action.response_draft = response_draft
    action.response_status = ResponseStatus.SUBMITTED_TO_IPO
    action.response_submitted_date = date.today()
    action.save()

    next_state = PatentStateMachine.get_next_state(
        app.status,
        event="SUBMIT_RESPONSE",
        actor_roles=roles,
    )

    old_status = app.status
    app.status = next_state
    app.save(update_fields=["status", "updated_at"])

    PatentAuditEvent.objects.create(
        application=app,
        event_name="SUBMIT_FER_RESPONSE",
        from_status=old_status,
        to_status=next_state,
        actor_user_id=attorney_user_id,
        payload={"office_action_id": action.id},
    )

    return action
