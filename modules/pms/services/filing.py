from datetime import date
from django.db import transaction

from modules.pms.domain.state_machine import PatentStateMachine
from modules.pms.domain.validation import validate_pre_filing_agreements
from modules.pms.models.application import ApplicationStatus, PatentApplication
from modules.pms.models.audit import PatentAuditEvent
from modules.pms.selectors.scoping import get_application_scoped


@transaction.atomic
def record_external_filing(
    app_id: int,
    user_id: int,
    official_filing_number: str,
    filing_date: date,
    roles: list[str],
) -> PatentApplication:
    """Record external patent office filing submission (BW-PMS-11)."""
    app = get_application_scoped(app_id, user_id, roles)

    # Prerequisite: Co-inventor agreements must be executed (BR-PMS-020)
    validate_pre_filing_agreements(list(app.inventors.all()))

    next_state = PatentStateMachine.get_next_state(
        app.status,
        event="RECORD_FILING",
        actor_roles=roles,
    )

    old_status = app.status
    app.status = next_state
    app.official_filing_number = official_filing_number
    app.official_filing_date = filing_date
    app.save(update_fields=["status", "official_filing_number", "official_filing_date", "updated_at"])

    PatentAuditEvent.objects.create(
        application=app,
        event_name="RECORD_FILING",
        from_status=old_status,
        to_status=next_state,
        actor_user_id=user_id,
        payload={"filing_number": official_filing_number, "filing_date": str(filing_date)},
    )

    return app


@transaction.atomic
def record_grant(
    app_id: int,
    user_id: int,
    grant_number: str,
    grant_date: date,
    roles: list[str],
) -> PatentApplication:
    """Record official grant of patent certificate."""
    app = get_application_scoped(app_id, user_id, roles)

    next_state = PatentStateMachine.get_next_state(
        app.status,
        event="GRANT",
        actor_roles=roles,
    )

    old_status = app.status
    app.status = next_state
    app.grant_number = grant_number
    app.grant_date = grant_date
    app.save(update_fields=["status", "grant_number", "grant_date", "updated_at"])

    PatentAuditEvent.objects.create(
        application=app,
        event_name="GRANT",
        from_status=old_status,
        to_status=next_state,
        actor_user_id=user_id,
        payload={"grant_number": grant_number, "grant_date": str(grant_date)},
    )

    return app
