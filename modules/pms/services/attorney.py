from datetime import datetime
from django.db import transaction

from modules.pms.domain.state_machine import PatentStateMachine
from modules.pms.models.application import ApplicationStatus, PatentApplication
from modules.pms.models.audit import PatentAuditEvent
from modules.pms.selectors.scoping import get_application_scoped


@transaction.atomic
def assign_attorney(
    app_id: int,
    coordinator_user_id: int,
    attorney_user_id: int,
    roles: list[str],
) -> PatentApplication:
    """Assign an empanelled patent attorney to an approved application (UC-PMS-010)."""
    app = get_application_scoped(app_id, coordinator_user_id, roles)

    next_state = PatentStateMachine.get_next_state(
        app.status,
        event="ASSIGN_ATTORNEY",
        actor_roles=roles,
    )

    old_status = app.status
    app.status = next_state
    app.assigned_attorney_id = attorney_user_id
    app.save(update_fields=["status", "assigned_attorney_id", "updated_at"])

    PatentAuditEvent.objects.create(
        application=app,
        event_name="ASSIGN_ATTORNEY",
        from_status=old_status,
        to_status=next_state,
        actor_user_id=coordinator_user_id,
        payload={"assigned_attorney_id": attorney_user_id},
    )

    return app


@transaction.atomic
def respond_assignment(
    app_id: int,
    attorney_user_id: int,
    accepted: bool,
    roles: list[str],
    notes: str = "",
) -> PatentApplication:
    """Accept or decline patent representation assignment (BW-PMS-06, BW-PMS-07)."""
    app = get_application_scoped(app_id, attorney_user_id, roles)

    event = "ACCEPT_ASSIGNMENT" if accepted else "DECLINE_ASSIGNMENT"
    next_state = PatentStateMachine.get_next_state(
        app.status,
        event=event,
        actor_roles=roles,
    )

    old_status = app.status
    app.status = next_state
    if not accepted:
        # Clear attorney so coordinator can reassign (BW-PMS-07)
        app.assigned_attorney_id = None
        app.save(update_fields=["status", "assigned_attorney_id", "updated_at"])
    else:
        app.save(update_fields=["status", "updated_at"])

    PatentAuditEvent.objects.create(
        application=app,
        event_name=event,
        from_status=old_status,
        to_status=next_state,
        actor_user_id=attorney_user_id,
        payload={"accepted": accepted, "notes": notes},
    )

    return app
